# Eco-Loop System Architecture

**Eco-Loop** is an autonomous closed-loop building energy agent. It pairs a physics-accurate building simulator (EnergyPlus) with a local open-source LLM, enabling real-time reasoning over comfort and energy tradeoffs to dynamically adjust HVAC setpoints.

## 1. System Integration (Fault Isolated & Robust)
- **Lifecycle Management**: The `EPRunner` explicitly tracks `idle`, `running`, `error`, and `stopped` states, ensuring the simulation runs reliably over extended multi-week horizons.
- **Asynchronous & Non-Blocking**: The bridge writes state summaries to disk every 30 minutes and checks for pending actions. If the LLM times out or fails, the bridge logs a `timeout` warning and simply holds previous setpoints without crashing.
- **Guardrails**: All LLM actions pass through `guardrails.py`.
- **Fault Injection Proven**: We include `tests/test_fault_injection.py` to explicitly simulate malformed actions, extreme LLM hallucinations, and PMV boundary tension, proving the guardrails clamp the outputs safely every time without crashing.

## 2. Thermal Comfort (Strict PMV Constraints)
- **Dual Enforcement Mechanism**: Comfort is treated as a hard constraint. The LLM is instructed to maintain a PMV of `[-0.5, +0.5]`. Independently, the Python Bridge executes a **PMV Repulsion Guardrail**: if current PMV approaches the limit (e.g., 0.4), the guardrail actively clamps LLM proposals that worsen the situation, logging a "PMV Tension: Current PMV X is near upper limit" event. An absolute heating floor at 18.0°C is also enforced.
- **Visual Proof**: `compare_runs.py` automatically generates a PMV timeseries chart alongside the baseline, proving the agent respected the band.

## 3. Energy Efficiency
- The system runs an identical apples-to-apples baseline vs agent model using the `RefBldgSmallOfficeNew2004_Chicago.idf` (DOE reference small office). Out of 5 zones, only `CORE_ZN` is under agent control; the other 4 zones keep their default schedule-based control.
- Weather file used is `USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw`, which matches the model's Chicago calibration.
- `compare_runs.py` calculates the net kWh reduction, outputting directly to a CSV and a clear bar chart.

## 4. Agentic Autonomy
- The system uses `qwen2.5:7b-instruct` via Ollama.
- The LLM leverages standard MCP tools (`get_current_state`, `get_recent_history`, `propose_setpoint`) to read the state and effect changes.
- The agent outputs explicit reasoning (visible in `logs/decisions.jsonl`) before acting, ensuring the system demonstrates true decision-making rather than fixed rule execution.

## 5. Technical Details
- **EnergyPlus Version**: v26.1.0 installed at `C:\EnergyPlusV26-1-0`.
- **EMS Actuators**: `Cooling_Setpoint_Actuator` and `Heating_Setpoint_Actuator`, both bound to `CORE_ZN`'s `Zone Temperature Control`.
- **Diagnostics**: `Output:EnergyManagementSystem, Verbose, Verbose, Verbose;` is added to `agent_model.idf` for actuator diagnostics in `eplusout.edd`.
- **Dependencies**: The `mcp` Python SDK is required and explicitly managed via `requirements.txt`.

---
**Run the Pipeline:**
Two-terminal setup:
```bash
python agent/client.py
```
```bash
python analysis/run_agent.py
```
