# Eco-Loop: Autonomous Closed-Loop Building Energy Agent

![Eco-Loop](https://img.shields.io/badge/Agent-Autonomous-green.svg) ![EnergyPlus](https://img.shields.io/badge/Simulation-EnergyPlus-blue.svg) ![LLM](https://img.shields.io/badge/LLM-Local-orange.svg)

Eco-Loop is an advanced proof-of-concept for an autonomous, artificial intelligence-driven Building Management System (BMS). It is designed to replace traditional static scheduling with a localized Large Language Model (LLM) capable of reasoning about building physics, thermal comfort constraints, and energy consumption tradeoffs in real-time.

## The Problem Statement

Commercial and residential buildings currently consume approximately 40% of global energy. A massive portion of this energy footprint is wasted due to a single, pervasive root cause: legacy Building Management Systems operate on static, rule-based schedules.

A traditional BMS is typically programmed with fixed heuristics—for example, setting the thermostat to 22°C from 9 AM to 6 PM, Monday through Friday. This approach is blind to dynamic, real-world context. The system does not know if the current day is unseasonably cool, if building occupancy is drastically lower than expected due to a holiday, or if the regional power grid is currently experiencing high carbon intensity. The system simply executes the static rule, leading to over-conditioning and substantial energy waste.

## The Eco-Loop Solution

Eco-Loop aims to replace this passive rule layer with a proactive, intelligent reasoning agent. By pairing a physics-accurate building simulation engine (EnergyPlus) with a local open-source Large Language Model (such as Llama 3.1 or Qwen 2.5), Eco-Loop enables the building to act as a self-correcting system.

The agent continuously ingests live simulation state data, reasons about the necessary tradeoffs between occupant thermal comfort and energy expenditure, and writes control decisions directly back into the running simulation. This closed-loop process requires zero human intervention, allowing the building to adapt to shifting environmental conditions dynamically while strictly minimizing HVAC electricity consumption.

## Technical Architecture

The Eco-Loop system is built upon a non-blocking, highly decoupled architecture designed to ensure extreme reliability over extended, multi-week simulation horizons. 

1. **Simulation Engine (EnergyPlus & pyenergyplus):** 
   Eco-Loop utilizes the industry-standard EnergyPlus engine to run high-fidelity physics simulations. We interface with the simulation via the `pyenergyplus` API, intercepting the Energy Management System (EMS) callbacks at every simulation timestep to read sensor data and apply actuator overrides.

2. **Python Bridge (`bridge/ep_runner.py`):** 
   The bridge serves as the core orchestration layer. It manages the lifecycle of the EnergyPlus process, aggregates raw sensor data, and executes safety guardrails. If the LLM agent times out or disconnects, the bridge acts as a fallback, gracefully maintaining the previous setpoints to prevent simulation hangs.

3. **State Compressor (`bridge/state_compressor.py`):** 
   Because EnergyPlus generates data at a high frequency, feeding raw timestep logs into an LLM would quickly exhaust its context window. The State Compressor condenses this data into a compact 30-minute rolling JSON state summary, providing the agent with the necessary context without the noise.

4. **MCP Server (`mcp_server/server.py`):** 
   Built using the Model Context Protocol (MCP) via `FastMCP`, this server exposes the building's internal state and allowable control levers (such as `propose_setpoint`) to the LLM agent using standardized tool-calling schemas.

5. **LLM Agent (`agent/client.py`):** 
   An asynchronous client that connects to the MCP Server and queries a locally hosted Ollama model. The agent evaluates the compressed state summary against its system prompt, generates a reasoning trace, and determines the optimal heating and cooling setpoints.

6. **Safety Guardrails (`bridge/guardrails.py`):**
   To prevent LLM hallucinations from destabilizing the building environment, all proposed actions must pass through a strict guardrail layer. This includes PMV (Predicted Mean Vote) boundary repulsion, which aggressively clamps setpoint proposals that would push occupant thermal comfort outside the acceptable [-0.5, +0.5] band.

For an in-depth breakdown of the system integration, safety guardrails, and fault isolation mechanisms, please see the [ARCHITECTURE.md](ARCHITECTURE.md) document.

## Quickstart Guide

### Prerequisites
1. **EnergyPlus:** Ensure EnergyPlus (version 24.1.0 or similar) is installed on your local machine. You may need to update the `EPLUS_DIR` variable in `bridge/ep_runner.py` if your installation path differs from the default Windows path.
2. **Ollama:** Install Ollama and pull your preferred instruct-tuned model. For example:
   ```bash
   ollama run qwen2.5:7b-instruct
   ```
3. **Python Dependencies:** Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

### Setup Instructions
To run the simulation, you must provide actual EnergyPlus model files:
1. Place your chosen baseline IDF file into `models/baseline.idf`.
2. Place a copy of that IDF, ensuring EMS Actuators are enabled for temperature control, into `models/agent_model.idf`.
3. Place a standard TMY3 EPW weather file into `models/weather.epw`.

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
