# Eco-Loop: Cognitive Multi-Agent Building Intelligence Platform

**Eco-Loop** is a 5-layer cognitive architecture for autonomous building energy management. It coordinates **7 concurrent LLM agents** (Planner, 5 Zone Agents, Coordinator, Comfort Auditor) through a Model Context Protocol (MCP) server to control a physics-accurate EnergyPlus simulation in real time.

**[Watch the Demo Video](https://drive.google.com/file/d/12aPcBYq61TVJfzHJzMN_OQ-evPPmDOMM/view?usp=sharing)**

---

## Quick Demo (No EnergyPlus Required)

See the full multi-agent workflow in action with pre-generated simulation data:

```bash
python scripts/generate_demo_data.py
```
Then open `dashboard/index.html` in your browser. Use the timeline scrubber to step through 24 hours of agent coordination, including 3 crisis events that demonstrate each cognitive layer.

---

## The Problem Statement

Commercial and residential buildings currently consume approximately 40% of global energy. A massive portion of this energy footprint is wasted due to a single, pervasive root cause: legacy Building Management Systems operate on static, rule-based schedules.

A traditional BMS is typically programmed with fixed heuristics. This approach is blind to dynamic, real-world context. The system does not know if the current day is unseasonably cool, if building occupancy is drastically lower than expected due to a holiday, or if the regional power grid is currently experiencing high carbon intensity. The system simply executes the static rule, leading to over-conditioning and substantial energy waste.

## The Eco-Loop Solution

Eco-Loop replaces this passive rule layer with a **predictive, self-correcting multi-agent system**. The 5 cognitive layers work together:

| Layer | Agent(s) | Role |
|---|---|---|
| **Planning** | Forecast Planner | Reads 24-hour weather forecast and grid carbon intensity to set a building-wide strategy (e.g., "pre-cool overnight") |
| **Reasoning** | 5 Zone Agents + Coordinator | Each zone proposes setpoints independently; the Coordinator resolves conflicts and enforces a peak demand cap |
| **Perception** | State Compressor + Anomaly Detector | Cleans and compresses sensor data; flags impossible readings before agents see them |
| **Memory** | Decision Store + Performance Tracker | Agents receive their last 3 decisions (and whether they were clamped) enabling true self-correction |
| **Safety** | Comfort Auditor + Guardrail Engine | Independent watchdog that can bypass all other layers if PMV exits the [-0.5, +0.5] comfort band |


## Technical Architecture

The Eco-Loop system is built upon a non-blocking, highly decoupled architecture designed to ensure extreme reliability over extended, multi-week simulation horizons. 

1. **Simulation Engine (EnergyPlus v26.1.0 & pyenergyplus):** 
   Eco-Loop utilizes the industry-standard EnergyPlus engine to run high-fidelity physics simulations on the DOE Reference Small Office building (`RefBldgSmallOfficeNew2004_Chicago.idf`). We interface with the simulation via the `pyenergyplus` API, intercepting the Energy Management System (EMS) callbacks at every simulation timestep to read sensor data and apply actuator overrides specifically for `CORE_ZN`.

2. **Python Bridge (`bridge/ep_runner.py`):** 
   The bridge serves as the core orchestration layer. It manages the lifecycle of the EnergyPlus process, aggregates raw sensor data, and executes safety guardrails. If the LLM agent times out or disconnects, the bridge acts as a fallback, gracefully maintaining the previous setpoints to prevent simulation hangs.

3. **State Compressor (`bridge/state_compressor.py`):** 
   Because EnergyPlus generates data at a high frequency, feeding raw timestep logs into an LLM would quickly exhaust its context window. The State Compressor condenses this data into a compact 30-minute rolling JSON state summary, providing the agent with the necessary context without the noise.

4. **MCP Server (`mcp_server/server.py`):** 
   Built using the Model Context Protocol (MCP) via `FastMCP`, this server exposes the building's internal state and allowable control levers (such as `propose_setpoint`) to the LLM agent using standardized tool-calling schemas.

5. **LLM Agent (`agent/client.py`):** 
   An asynchronous client that connects to the MCP Server and queries a locally hosted Ollama model (`qwen2.5:7b-instruct`). The agent evaluates the compressed state summary against its system prompt, generates a reasoning trace, and determines the optimal heating and cooling setpoints.

6. **Safety Guardrails (`bridge/guardrails.py`):**
   To prevent LLM hallucinations from destabilizing the building environment, all proposed actions must pass through a strict guardrail layer. This includes PMV (Predicted Mean Vote) boundary repulsion, which aggressively clamps setpoint proposals that would push occupant thermal comfort outside the acceptable [-0.5, +0.5] band, as well as an absolute heating floor of 18.0°C.

For an in-depth breakdown of the system integration, safety guardrails, and fault isolation mechanisms, please see the [ARCHITECTURE.md](ARCHITECTURE.md) document.

## Quickstart Guide

### Prerequisites
1. **EnergyPlus:** Ensure EnergyPlus v26.1.0 is installed on your local machine at `C:\EnergyPlusV26-1-0` (update the `EPLUS_DIR` variable in `bridge/ep_runner.py` if your path differs).
2. **Ollama:** Install Ollama and pull the required instruct-tuned model:
   ```bash
   ollama run qwen2.5:7b-instruct
   ```
3. **Python Dependencies:** Install the required Python packages (including the `mcp` SDK):
   ```bash
   pip install -r requirements.txt
   ```

### Setup Instructions
To run the simulation, you must provide the specific EnergyPlus model files:
1. Place the `RefBldgSmallOfficeNew2004_Chicago.idf` file into `models/baseline.idf`.
2. Place a copy of that IDF into `models/agent_model.idf` and add the EMS Actuators `Cooling_Setpoint_Actuator` and `Heating_Setpoint_Actuator` bound to `CORE_ZN`'s Zone Temperature Control.
3. Add `Output:EnergyManagementSystem, Verbose, Verbose, Verbose;` to `agent_model.idf` for diagnostics.
4. Place the `USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw` weather file into `models/weather.epw`.

## Running the Simulation

You will need to run the pipeline across three concurrent terminal windows to observe the closed-loop agent in action.

**1. Generate Baseline Data:**
First, run the baseline simulation to establish a control group.
```bash
python analysis/run_baseline.py
```

**2. Start the LLM Agent & MCP Server:**
In a separate terminal, start the LLM client. This will automatically spin up the MCP server and begin polling for state updates.
```bash
python agent/client.py
```

**3. Run the Agent-Controlled Simulation:**
In a third terminal, initiate the agent-controlled EnergyPlus run. The Python bridge will communicate with the MCP server, passing state and receiving setpoints.
```bash
python analysis/run_agent.py
```

**4. Analyze the Results:**
Once both simulations have successfully completed, run the analysis script to generate the performance comparison charts:
```bash
python analysis/compare_runs.py
```
This script parses the output data and generates `energy_comparison.png` and `pmv_comparison.png` in the `analysis/outputs/` directory. These charts visually demonstrate the net kWh savings achieved by the agent, as well as its adherence to strict thermal comfort constraints.
