# Eco-Loop

Autonomous Closed-Loop Building Energy Agent using EnergyPlus, MCP, and a local LLM.

## Structure
- `models/`: EnergyPlus IDF models and EPW weather files.
- `bridge/`: Python bridge communicating with EnergyPlus via pyenergyplus.
- `mcp_server/`: MCP server exposing EnergyPlus control tools.
- `agent/`: LLM agent client.
- `analysis/`: Scripts to run simulations and compare results.
- `logs/`: Simulation decision logs.
