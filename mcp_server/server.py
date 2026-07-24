import json
import os
import datetime
from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("EcoLoopServer")

# File-based communication channels between MCP server and EnergyPlus Bridge
LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
STATE_FILE = os.path.join(LOGS_DIR, "latest_state.json")
HISTORY_FILE = os.path.join(LOGS_DIR, "state_history.jsonl")
ACTION_FILE = os.path.join(LOGS_DIR, "pending_action.json")
ERROR_FILE = os.path.join(LOGS_DIR, "error_summary.json")

os.makedirs(LOGS_DIR, exist_ok=True)

@mcp.tool()
def get_current_state() -> str:
    """Returns the latest compressed state summary of the building (temperature, energy, PMV)."""
    if not os.path.exists(STATE_FILE):
        return json.dumps({"error": "No state available yet. Simulation might be initializing."})
    with open(STATE_FILE, 'r') as f:
        return f.read()

@mcp.tool()
def get_recent_history(k: int) -> str:
    """Returns the last K state summaries for trend awareness."""
    if not os.path.exists(HISTORY_FILE):
        return json.dumps([])
    history = []
    with open(HISTORY_FILE, 'r') as f:
        for line in f:
            if line.strip():
                history.append(json.loads(line))
    return json.dumps(history[-k:])

@mcp.tool()
def get_error_summary() -> str:
    """Returns counts of severe/fatal errors and warnings from the EnergyPlus simulation."""
    if not os.path.exists(ERROR_FILE):
        return json.dumps({"severe_count": 0, "warning_count": 0, "last_warnings": []})
    with open(ERROR_FILE, 'r') as f:
        return f.read()

@mcp.tool()
def propose_setpoint(zone: str, heating_c: float, cooling_c: float) -> str:
    """
    Propose new heating and cooling setpoints for a specific zone.
    The bridge will read this and apply the setpoints at the next available timestep.
    """
    action = {
        "timestamp": datetime.datetime.now().isoformat(),
        "type": "setpoint",
        "zone": zone,
        "heating_c": heating_c,
        "cooling_c": cooling_c
    }
    with open(ACTION_FILE, 'w') as f:
        json.dump(action, f)
    return json.dumps({"status": "ack", "message": "Setpoint proposed to the bridge."})

@mcp.tool()
def propose_override(parameter: str, value: float) -> str:
    """Propose a supervisory override for a specific parameter (e.g., supply_air_temp)."""
    action = {
        "timestamp": datetime.datetime.now().isoformat(),
        "type": "override",
        "parameter": parameter,
        "value": value
    }
    with open(ACTION_FILE, 'w') as f:
        json.dump(action, f)
    return json.dumps({"status": "ack", "message": f"Override proposed for {parameter}."})

if __name__ == "__main__":
    # Run the MCP server over stdio for the LLM agent to connect to
    mcp.run(transport='stdio')
