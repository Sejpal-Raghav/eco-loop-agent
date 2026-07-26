import asyncio
import json
import os
import sys
import requests
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
OLLAMA_URL = 'http://localhost:11434/api/chat'
MODEL_NAME = 'llama3.2:latest'

class EcoLoopAgent:

    def __init__(self, mcp_server_path):
        self.server_params = StdioServerParameters(command='python', args=[mcp_server_path])
        with open(os.path.join(os.path.dirname(__file__), 'system_prompt.md'), 'r') as f:
            self.system_prompt = f.read()

    async def run_loop(self):
        print(f'Starting Eco-Loop Agent client (Model: {MODEL_NAME})...')
        async with stdio_client(self.server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print('Connected to MCP Server.')
                last_sim_time = None
                while True:
                    try:
                        state_result = await session.call_tool('get_current_state', {})
                        state_str = state_result.content[0].text
                        state_data = json.loads(state_str)
                        if 'error' in state_data:
                            await asyncio.sleep(2)
                            continue
                        current_sim_time = state_data.get('sim_time')
                        if current_sim_time != last_sim_time:
                            print(f'\n[{current_sim_time}] New state received. Analyzing...')
                            messages = [{'role': 'system', 'content': self.system_prompt}, {'role': 'user', 'content': f'Current State:\n{json.dumps(state_data, indent=2)}'}]
                            payload = {'model': MODEL_NAME, 'messages': messages, 'stream': False, 'format': 'json'}
                            try:
                                loop = asyncio.get_running_loop()
                                response = await asyncio.wait_for(loop.run_in_executor(None, lambda: requests.post(OLLAMA_URL, json=payload)), timeout=15.0)
                                response.raise_for_status()
                                result = response.json()
                                llm_output = json.loads(result['message']['content'])
                                print(f"Reasoning: {llm_output.get('reasoning', 'None')}")
                                heat = float(llm_output.get('proposed_heating', 21.0))
                                cool = float(llm_output.get('proposed_cooling', 24.0))
                                zone_name = state_data['zones'][0]['name']
                                tool_result = await session.call_tool('propose_setpoint', {'zone': zone_name, 'heating_c': heat, 'cooling_c': cool})
                                print(f'Action sent: Heat {heat}°C, Cool {cool}°C. Server: {tool_result.content[0].text}')
                                last_sim_time = current_sim_time
                            except Exception as e:
                                print(f'LLM interaction failed: {e}')
                    except Exception as e:
                        print(f'Agent loop error: {e}')
                    await asyncio.sleep(2)
if __name__ == '__main__':
    server_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mcp_server', 'server.py')
    agent = EcoLoopAgent(server_path)
    asyncio.run(agent.run_loop())