# Eco-Loop: Autonomous Closed-Loop Building Energy Agent

![Eco-Loop](https://img.shields.io/badge/Agent-Autonomous-green.svg) ![EnergyPlus](https://img.shields.io/badge/Simulation-EnergyPlus-blue.svg) ![LLM](https://img.shields.io/badge/LLM-Local-orange.svg)

Eco-Loop is a proof-of-concept for an autonomous, AI-driven Building Management System (BMS). It replaces traditional static scheduling with a localized Large Language Model (LLM) that reasons about building physics, thermal comfort, and energy consumption in real-time.

## 🌍 The Problem
Buildings consume roughly 40% of global energy. A massive portion of this energy is wasted due to a single root cause: Building Management Systems run on **static, rule-based schedules**. 

A traditional BMS programmed to set the thermostat to 22°C from 9 AM to 6 PM does not know if today is unseasonably cool, if occupancy is unexpectedly low, or if the grid is currently carbon-intensive. It just blindly follows the rule.

## 🚀 The Eco-Loop Solution
Eco-Loop replaces the passive rule layer with an active **reasoning agent**. We pair a physics-accurate building simulator ([EnergyPlus](https://energyplus.net/)) with a local open-source LLM. The agent reads the live simulation state, reasons about comfort/energy tradeoffs, and writes control decisions directly back into the running simulation—with zero human intervention.

The building becomes a **self-correcting, adaptive system** that proactively minimizes HVAC electricity consumption while strictly maintaining occupant thermal comfort.

## 🏗️ Technical Architecture

Eco-Loop is built on a non-blocking, decoupled architecture designed for extreme reliability over extended simulation horizons.

* **Simulation Engine (`EnergyPlus` & `pyenergyplus`)**: Runs the physics simulation and exposes Energy Management System (EMS) callbacks.
* **Python Bridge (`bridge/ep_runner.py`)**: Intercepts the EMS callbacks every simulation timestep. It aggregates sensor data, enforces **PMV (Predicted Mean Vote)** comfort guardrails, and applies the LLM's chosen setpoints.
* **State Compressor (`bridge/state_compressor.py`)**: Condenses raw, high-frequency timestep data into a compact 30-minute JSON state summary to prevent LLM context-window exhaustion.
* **MCP Server (`mcp_server/server.py`)**: Built on `FastMCP`, it exposes the simulation state and control levers (`propose_setpoint`) to the LLM agent via standard MCP protocols.
* **LLM Agent (`agent/client.py`)**: An asynchronous client that connects to the MCP Server and queries a local Ollama model (e.g., Qwen 2.5 or Llama 3.1) to decide on optimal heating/cooling setpoints.

For an in-depth breakdown of the system integration, safety guardrails, and fault isolation mechanisms, see [ARCHITECTURE.md](ARCHITECTURE.md).

## 🛠️ Quickstart

### Prerequisites
1. **EnergyPlus**: Ensure EnergyPlus (V24.1.0 or similar) is installed on your machine. Update the `EPLUS_DIR` in `bridge/ep_runner.py` if your installation path differs.
2. **Ollama**: Install [Ollama](https://ollama.com/) and pull your preferred model (e.g., `ollama run qwen2.5:7b-instruct`).
3. **Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Setup
You must provide actual EnergyPlus models to run the simulation:
1. Place your baseline IDF file in `models/baseline.idf`.
2. Place a copy of that IDF with EMS Actuators enabled in `models/agent_model.idf`.
3. Place a standard TMY3 EPW weather file in `models/weather.epw`.

## 📊 Running the Simulation

Run the pipeline in three terminal windows to see the closed-loop agent in action:

**1. Generate Baseline Data:**
```bash
python analysis/run_baseline.py
```

**2. Start the LLM Agent & MCP Server:**
```bash
python agent/client.py
```

**3. Run the Agent-Controlled Simulation:**
```bash
# In a new terminal, alongside the agent
python analysis/run_agent.py
```

**4. Analyze the Results:**
Once the simulation finishes, generate the performance comparison charts:
```bash
python analysis/compare_runs.py
```
This will output `energy_comparison.png` and `pmv_comparison.png` in the `analysis/outputs/` directory, visually proving the net kWh savings and thermal comfort compliance!
