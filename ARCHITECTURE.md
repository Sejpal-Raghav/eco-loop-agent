# Eco-Loop System Architecture

**Eco-Loop** is an autonomous closed-loop building energy agent. It pairs a physics-accurate building simulator (EnergyPlus) with a local open-source LLM, enabling real-time reasoning over comfort and energy tradeoffs to dynamically adjust HVAC setpoints.

## 1. System Integration (Fault Isolated & Robust)
- **Lifecycle Management**: The `EPRunner` explicitly tracks `idle`, `running`, `error`, and `stopped` states, ensuring the simulation runs reliably over extended multi-week horizons.
- **Asynchronous & Non-Blocking**: The bridge writes state summaries to disk every 30 minutes and checks for pending actions. If the LLM times out or fails (enforced by a strict `asyncio.wait_for` 15-second timeout in `client.py`), the bridge logs a `timeout` warning and simply holds previous setpoints without crashing.
- **Guardrails**: All LLM actions pass through `guardrails.py`.
- **Fault Injection Proven**: We include `tests/test_fault_injection.py` to explicitly simulate malformed actions, extreme LLM hallucinations, and PMV boundary tension, proving the guardrails clamp the outputs safely every time.

## 2. Thermal Comfort (Strict PMV Constraints)
- **Dual Enforcement Mechanism**: Comfort is treated as a hard constraint. The LLM is instructed to maintain a PMV of `[-0.5, +0.5]`. Independently, the Python Bridge executes a **PMV Repulsion Guardrail**: if current PMV approaches the limit (e.g., 0.4), the guardrail actively clamps LLM proposals that worsen the situation, logging a "PMV Tension" event.
- **Visual Proof**: `compare_runs.py` automatically generates a PMV timeseries chart alongside the baseline, proving the agent respected the band.

## 3. Energy Efficiency
- The system runs an identical apples-to-apples baseline (standard fixed schedule) vs agent model.
- `compare_runs.py` calculates the net kWh reduction, outputting directly to a CSV and a clear bar chart.

## 4. Agentic Autonomy
- The LLM leverages standard MCP tools (`get_current_state`, `get_recent_history`, `propose_setpoint`) to read the state and effect changes.
- The agent outputs explicit reasoning (visible in `logs/decisions.jsonl`) before acting, ensuring the system demonstrates true decision-making rather than fixed rule execution.

---
**Run the Pipeline:**
```bash
python analysis/run_baseline.py
# In terminal 1:
python agent/client.py
# In terminal 2:
python analysis/run_agent.py
# After completion:
python analysis/compare_runs.py
```
