import json
import os
import datetime
from mcp.server.fastmcp import FastMCP

mcp = FastMCP('EcoLoopCognitiveServer')

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)
STATE_FILE = os.path.join(LOGS_DIR, 'latest_state.json')
HISTORY_FILE = os.path.join(LOGS_DIR, 'state_history.jsonl')
PROPOSALS_DIR = os.path.join(LOGS_DIR, 'zone_proposals')
os.makedirs(PROPOSALS_DIR, exist_ok=True)
COORD_FILE = os.path.join(LOGS_DIR, 'coordinator_decision.json')
OVERRIDES_DIR = os.path.join(LOGS_DIR, 'comfort_overrides')
os.makedirs(OVERRIDES_DIR, exist_ok=True)
STRATEGY_FILE = os.path.join(LOGS_DIR, 'current_strategy.json')

# 1. MEMORY LAYER TOOLS
from memory.decision_store import DecisionStore
from memory.performance_tracker import PerformanceTracker

decision_store = DecisionStore(LOGS_DIR)
performance_tracker = PerformanceTracker(LOGS_DIR)

@mcp.tool()
def get_my_last_decisions(agent_id: str, k: int) -> str:
    zone_name = None if agent_id == 'coordinator' else agent_id
    decisions = decision_store.get_last_k_decisions(zone_name, k)
    return json.dumps(decisions)

@mcp.tool()
def get_performance_summary(hours: int) -> str:
    return json.dumps(performance_tracker.get_performance_summary(hours))


# 2. PERCEPTION LAYER TOOLS
@mcp.tool()
def get_building_state() -> str:
    if not os.path.exists(STATE_FILE):
        return json.dumps({'error': 'No state available.'})
    with open(STATE_FILE, 'r') as f:
        return f.read()

@mcp.tool()
def get_zone_state(zone_name: str) -> str:
    if not os.path.exists(STATE_FILE):
        return json.dumps({'error': 'No state available.'})
    with open(STATE_FILE, 'r') as f:
        state = json.load(f)
    for z in state.get('zones', []):
        if z['name'] == zone_name:
            # Include outdoor temp and anomalies context
            return json.dumps({
                'sim_time': state['sim_time'],
                'outdoor_temp_c': state['outdoor_temp_c'],
                'zone_state': z,
                'anomalies': state.get('anomalies', [])
            })
    return json.dumps({'error': f'Zone {zone_name} not found.'})

@mcp.tool()
def get_anomaly_report() -> str:
    if not os.path.exists(STATE_FILE):
        return json.dumps([])
    with open(STATE_FILE, 'r') as f:
        return json.dumps(json.load(f).get('anomalies', []))


# 3. REASONING LAYER TOOLS
@mcp.tool()
def propose_zone_setpoint(zone: str, heating_c: float, cooling_c: float, reasoning: str) -> str:
    proposal = {
        'zone': zone,
        'heating_c': heating_c,
        'cooling_c': cooling_c,
        'reasoning': reasoning,
        'timestamp': datetime.datetime.now().isoformat()
    }
    with open(os.path.join(PROPOSALS_DIR, f"{zone}.json"), 'w') as f:
        json.dump(proposal, f)
    return json.dumps({'status': 'ack', 'message': f'Proposal logged for {zone}.'})

@mcp.tool()
def get_all_zone_proposals() -> str:
    proposals = {}
    for fname in os.listdir(PROPOSALS_DIR):
        if fname.endswith('.json'):
            with open(os.path.join(PROPOSALS_DIR, fname), 'r') as f:
                proposals[fname.replace('.json', '')] = json.load(f)
    return json.dumps(proposals)

@mcp.tool()
def approve_setpoints(zone_setpoints: dict, reasoning: str) -> str:
    # zone_setpoints format: {"CORE_ZN": {"heating_c": 21, "cooling_c": 24}, ...}
    decision = {
        'zone_actions': zone_setpoints,
        'reasoning': reasoning,
        'timestamp': datetime.datetime.now().isoformat()
    }
    with open(COORD_FILE, 'w') as f:
        json.dump(zone_setpoints, f) # The bridge just reads the zone_actions dict
    # Clear out proposals after approval
    for fname in os.listdir(PROPOSALS_DIR):
        if fname.endswith('.json'):
            os.remove(os.path.join(PROPOSALS_DIR, fname))
    return json.dumps({'status': 'ack', 'message': 'Coordinator decision sent to bridge.'})


# 4. PLANNING LAYER TOOLS
@mcp.tool()
def set_strategy(strategy: dict) -> str:
    with open(STRATEGY_FILE, 'w') as f:
        json.dump(strategy, f)
    return json.dumps({'status': 'ack', 'message': 'New strategy set.'})

@mcp.tool()
def get_current_strategy() -> str:
    if not os.path.exists(STRATEGY_FILE):
        return json.dumps({"strategy": "default", "reasoning": "No advanced strategy set."})
    with open(STRATEGY_FILE, 'r') as f:
        return f.read()

@mcp.tool()
def get_grid_carbon(hours_ahead: int) -> str:
    # Simple simulated diurnal curve read from CSV
    import pandas as pd
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'grid_carbon_chicago.csv')
    df = pd.read_csv(csv_path)
    # For simulation, just return the whole curve for the day
    return df.to_json(orient='records')

@mcp.tool()
def get_weather_forecast(hours_ahead: int) -> str:
    # A mock returning upcoming peaks since EPW parsing is complex for a quick tool
    return json.dumps({
        "forecast": f"Next {hours_ahead} hours: Outdoor temp will rise to a peak of 33C at 15:00, then drop to 22C by 22:00. High solar load expected on south and west faces."
    })


# 5. SAFETY LAYER TOOLS
@mcp.tool()
def get_all_zone_pmv() -> str:
    if not os.path.exists(STATE_FILE):
        return json.dumps({})
    with open(STATE_FILE, 'r') as f:
        state = json.load(f)
    pmvs = {z['name']: z['pmv'] for z in state.get('zones', [])}
    return json.dumps(pmvs)

@mcp.tool()
def issue_comfort_override(zone: str, heating_c: float, cooling_c: float, reason: str) -> str:
    override = {
        'heating_c': heating_c,
        'cooling_c': cooling_c,
        'reason': reason
    }
    with open(os.path.join(OVERRIDES_DIR, f"{zone}.json"), 'w') as f:
        json.dump(override, f)
    return json.dumps({'status': 'ack', 'message': f'EMERGENCY OVERRIDE issued for {zone}.'})


if __name__ == '__main__':
    mcp.run(transport='stdio')