import asyncio
import json
import os
import requests
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

OLLAMA_URL = 'http://localhost:11434/api/chat'
MODEL_NAME = 'qwen2.5:7b-instruct'

ZONE_SPECS = {
    "CORE_ZN": "Interior zone. Stable temperature, minimal solar gain.",
    "PERIMETER_ZN_1": "South-facing zone. High solar gain during the day.",
    "PERIMETER_ZN_2": "East-facing zone. Morning solar peak.",
    "PERIMETER_ZN_3": "North-facing zone. Low solar gain, prone to overcooling.",
    "PERIMETER_ZN_4": "West-facing zone. Afternoon solar peak."
}

class CognitiveAgents:
    def __init__(self, mcp_session, prompts_dir):
        self.mcp = mcp_session
        self.prompts_dir = prompts_dir
        
        with open(os.path.join(prompts_dir, 'planner.md'), 'r') as f:
            self.planner_prompt = f.read()
        with open(os.path.join(prompts_dir, 'coordinator.md'), 'r') as f:
            self.coord_prompt = f.read()
        with open(os.path.join(prompts_dir, 'comfort_auditor.md'), 'r') as f:
            self.auditor_prompt = f.read()
        with open(os.path.join(prompts_dir, 'zone_agent.md'), 'r') as f:
            self.zone_prompt_template = f.read()

    async def _query_llm(self, system_prompt, user_message):
        messages = [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_message}]
        payload = {'model': MODEL_NAME, 'messages': messages, 'stream': False, 'format': 'json'}
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: requests.post(OLLAMA_URL, json=payload, timeout=30))
        response.raise_for_status()
        return json.loads(response.json()['message']['content'])

    async def run_planner(self):
        print("\n[PLANNING LAYER] Running Forecast Planner...")
        try:
            weather_res = await self.mcp.call_tool('get_weather_forecast', {'hours_ahead': 24})
            carbon_res = await self.mcp.call_tool('get_grid_carbon', {'hours_ahead': 24})
            perf_res = await self.mcp.call_tool('get_performance_summary', {'hours': 24})
            
            user_msg = f"Weather: {weather_res.content[0].text}\nCarbon: {carbon_res.content[0].text}\nRecent Performance: {perf_res.content[0].text}"
            strategy = await self._query_llm(self.planner_prompt, user_msg)
            
            await self.mcp.call_tool('set_strategy', {'strategy': strategy})
            print(f"Strategy set: {strategy.get('strategy')}")
        except Exception as e:
            print(f"Planner failed: {e}")

    async def run_zone_agent(self, zone_name):
        try:
            state_res = await self.mcp.call_tool('get_zone_state', {'zone_name': zone_name})
            if 'error' in state_res.content[0].text: return
            
            strat_res = await self.mcp.call_tool('get_current_strategy', {})
            mem_res = await self.mcp.call_tool('get_my_last_decisions', {'agent_id': zone_name, 'k': 3})
            
            sys_prompt = self.zone_prompt_template.replace('{ZONE_NAME}', zone_name).replace('{ZONE_SPECIFIC_INSTRUCTION}', ZONE_SPECS[zone_name])
            user_msg = f"State: {state_res.content[0].text}\nStrategy: {strat_res.content[0].text}\nRecent Decisions: {mem_res.content[0].text}"
            
            proposal = await self._query_llm(sys_prompt, user_msg)
            
            await self.mcp.call_tool('propose_zone_setpoint', {
                'zone': zone_name,
                'heating_c': float(proposal.get('proposed_heating', 21)),
                'cooling_c': float(proposal.get('proposed_cooling', 24)),
                'reasoning': proposal.get('reasoning', '')
            })
            print(f"[ZONE LAYER] {zone_name} proposed H:{proposal.get('proposed_heating')} C:{proposal.get('proposed_cooling')}")
        except Exception as e:
            print(f"Zone agent {zone_name} failed: {e}")

    async def run_coordinator(self):
        print("\n[REASONING LAYER] Running Coordinator...")
        try:
            props_res = await self.mcp.call_tool('get_all_zone_proposals', {})
            state_res = await self.mcp.call_tool('get_building_state', {})
            strat_res = await self.mcp.call_tool('get_current_strategy', {})
            
            user_msg = f"Proposals: {props_res.content[0].text}\nBuilding State: {state_res.content[0].text}\nStrategy: {strat_res.content[0].text}"
            decision = await self._query_llm(self.coord_prompt, user_msg)
            
            await self.mcp.call_tool('approve_setpoints', {
                'zone_setpoints': decision.get('zone_actions', {}),
                'reasoning': decision.get('reasoning', '')
            })
            print(f"Coordinator approved setpoints.")
        except Exception as e:
            print(f"Coordinator failed: {e}")

    async def run_auditor(self):
        print("[SAFETY LAYER] Running Comfort Auditor...")
        try:
            pmv_res = await self.mcp.call_tool('get_all_zone_pmv', {})
            user_msg = f"Current PMVs: {pmv_res.content[0].text}"
            
            overrides = await self._query_llm(self.auditor_prompt, user_msg)
            ovr_dict = overrides.get('overrides', {})
            
            for zone, data in ovr_dict.items():
                await self.mcp.call_tool('issue_comfort_override', {
                    'zone': zone,
                    'heating_c': float(data.get('heating_c', 21)),
                    'cooling_c': float(data.get('cooling_c', 24)),
                    'reason': data.get('reason', '')
                })
                print(f"!!! EMERGENCY OVERRIDE ISSUED FOR {zone} !!!")
        except Exception as e:
            print(f"Auditor failed: {e}")

async def run_loop():
    server_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mcp_server', 'server.py')
    prompts_dir = os.path.join(os.path.dirname(__file__), 'prompts')
    params = StdioServerParameters(command='python', args=[server_path])
    
    print(f'Starting Cognitive Orchestrator (Model: {MODEL_NAME})...')
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print('Connected to MCP Server.')
            
            agents = CognitiveAgents(session, prompts_dir)
            last_sim_time = None
            cycles = 0
            
            while True:
                try:
                    state_res = await session.call_tool('get_building_state', {})
                    if 'error' in state_res.content[0].text:
                        await asyncio.sleep(2)
                        continue
                        
                    state_data = json.loads(state_res.content[0].text)
                    current_sim_time = state_data.get('sim_time')
                    
                    if current_sim_time != last_sim_time:
                        print(f'\n[{current_sim_time}] New cycle. Orchestrating agents...')
                        
                        # 1. Planner runs every 12 cycles (6 hours)
                        if cycles % 12 == 0:
                            await agents.run_planner()
                            
                        # 2. Zone Agents run concurrently
                        zones = ['CORE_ZN', 'PERIMETER_ZN_1', 'PERIMETER_ZN_2', 'PERIMETER_ZN_3', 'PERIMETER_ZN_4']
                        tasks = [agents.run_zone_agent(z) for z in zones]
                        await asyncio.gather(*tasks)
                        
                        # 3. Coordinator resolves and approves
                        await agents.run_coordinator()
                        
                        # 4. Auditor monitors safety
                        await agents.run_auditor()
                        
                        last_sim_time = current_sim_time
                        cycles += 1
                        
                except Exception as e:
                    print(f"Orchestrator error: {e}")
                
                await asyncio.sleep(2)

if __name__ == '__main__':
    asyncio.run(run_loop())
