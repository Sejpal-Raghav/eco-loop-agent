# Eco-Loop: Cognitive Building Intelligence

Buildings consume approximately 40% of global energy and remain a primary driver of carbon emissions. Traditional Building Management Systems (BMS) rely on rigid, rule-based schedules that fail to adapt dynamically to real-time changes in weather, occupancy, and grid demands. 

**Eco-Loop** transforms the building from a passive energy consumer into an active, self-correcting agent capable of continuous, real-time optimization. It is an autonomous, closed-loop control pipeline driven entirely by open-source Large Language Models (LLMs) communicating via the Model Context Protocol (MCP).

---

## The 5-Layer Distributed Cognitive Stack

Attempting to run a building on a single monolithic LLM prompt leads to context bloat, extreme latency, and dangerous hallucinations. Instead, Eco-Loop distributes the workload across **7 concurrent LLM agents** organized into a strict, 5-layer hierarchical execution pipeline:

| Layer | Agent(s) | Role |
|---|---|---|
| **Perception** | State Compressor + Anomaly Detector | Cleans and compresses raw EnergyPlus sensor data into a concise semantic state summary to reduce token latency. |
| **Memory** | Outcome Memory | Tracks previous decisions and their outcomes, enabling true self-correction. |
| **Planning** | Forecast Planner | Wakes every 6 hours to read weather and carbon intensity, establishing a macro-strategy and peak demand cap for the facility. |
| **Reasoning** | 5 Zone Agents + Coordinator | Independent zone agents propose localized setpoints every 30 mins. The Coordinator actively negotiates conflicts to balance comfort against the facility demand cap. |
| **Safety** | Comfort Auditor + Guardrail Engine | A strictly deterministic layer that clamps any LLM hallucination exceeding 3°C delta or violating the Predicted Mean Vote (PMV) comfort band. |

*For a comprehensive breakdown of the architecture, data flow, and the negotiation protocol, read the [Technical Blog](dashboard/blog.html).*

---

## Interactive Dashboard & Workflow Visualization

Eco-Loop includes a premium, interactive web dashboard to visualize the multi-agent reasoning process and view the quantifiable energy savings.

### Quick Demo (No EnergyPlus Required)

You can see the full multi-agent workflow in action using pre-generated simulation data:

1. Generate the simulated data:
   ```bash
   python scripts/generate_demo_data.py
   ```
2. Open `dashboard/index.html` in your web browser. 
3. Click "Launch dashboard" to use the timeline scrubber and step through 24 hours of agent coordination, including crisis events that demonstrate each cognitive layer reacting in real-time.

---

## Full Simulation Quickstart

To run the live, closed-loop pipeline yourself, Eco-Loop uses **EnergyPlus** as a high-fidelity digital building sandbox.

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
1. Place the `RefBldgSmallOfficeNew2004_Chicago.idf` file into `models/baseline.idf`.
2. Place a copy of that IDF into `models/agent_model.idf` and add the EMS Actuators `Cooling_Setpoint_Actuator` and `Heating_Setpoint_Actuator` bound to `CORE_ZN`'s Zone Temperature Control.
3. Add `Output:EnergyManagementSystem, Verbose, Verbose, Verbose;` to `agent_model.idf` for diagnostics.
4. Place the `USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw` weather file into `models/weather.epw`.

### Running the Live Pipeline

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
