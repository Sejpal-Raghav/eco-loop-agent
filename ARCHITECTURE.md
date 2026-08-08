# Eco-Loop v2: Cognitive Building Intelligence Platform

**Eco-Loop v2** elevates autonomous building control from a reactive PID-like system to a predictive, cognitive platform. By organizing multiple specialized LLM agents into a layered cognitive architecture, Eco-Loop can read weather forecasts, optimize for grid carbon, self-correct from past mistakes, and coordinate complex multi-zone tradeoffs in real-time.

---

## The 5-Layer Cognitive Architecture

```text
┌─────────────────────────────────────────────────────┐
│                   SAFETY LAYER                      │
│         Comfort Auditor + Guardrail Engine          │
│    (can override any layer below — hard veto)       │
├─────────────────────────────────────────────────────┤
│                  PLANNING LAYER                     │
│              Forecast Planner Agent                 │
│  (reads weather forecast + grid carbon signal,      │
│   generates a 24-hour lookahead strategy)           │
├─────────────────────────────────────────────────────┤
│                REASONING LAYER                      │
│     Coordinator Agent + 5 Zone Agents               │
│  (real-time setpoint decisions within the           │
│   strategy set by the planning layer)               │
├─────────────────────────────────────────────────────┤
│                PERCEPTION LAYER                     │
│    State Compressor + Anomaly Detector              │
│  (cleans, compresses, and flags sensor data         │
│   before any agent sees it)                         │
├─────────────────────────────────────────────────────┤
│                  MEMORY LAYER                       │
│         Decision History + Performance Tracker      │
│  (agents can query their own past decisions,        │
│   learn from what worked and what got clamped)      │
└─────────────────────────────────────────────────────┘
          ↕ EMS Actuators ↕
┌─────────────────────────────────────────────────────┐
│            EnergyPlus Simulation Engine              │
└─────────────────────────────────────────────────────┘
```

### 1. Planning Layer (Predictive Strategy)
Unlike rule-based systems, Eco-Loop can read the future. Every 6 simulated hours, the **Forecast Planner Agent** reads the upcoming 24-hour weather forecast and grid carbon intensity curve. It outputs a natural-language strategy (e.g., *"Carbon peaks at 3pm, pre-cool the building overnight then coast with a wider deadband"*).

### 2. Reasoning Layer (Multi-Agent Negotiation)
Real-time control is handled every 30 minutes by **5 Zone Agents** running concurrently. Each zone agent (e.g., `CORE_ZN`, `PERIMETER_ZN_1`) receives specific prompts detailing its thermal profile (e.g., South-facing, high solar gain) and the Planner's strategy. They propose setpoints which are then sent to the **Coordinator Agent**. The Coordinator resolves conflicts, ensuring the total building kW doesn't exceed a peak demand cap, and issues final setpoints.

### 3. Perception & Memory Layers (Context & Self-Correction)
The **Anomaly Detector** flags impossible sensor readings (e.g., a broken sensor reporting -50°C) before the LLM sees them.
The **Memory Layer** appends the agent's last 3 decisions (and whether they were clamped) to the prompt. If a zone agent proposes 28°C cooling and gets clamped, the next cycle it reads *"Your last proposal was clamped for PMV tension"* and adjusts dynamically. This proves true autonomous self-correction.

### 4. Safety Layer (The Ultimate Veto)
Comfort is a hard constraint. The **Comfort Auditor Agent** runs independently after every coordinator decision. If it detects any zone drifting outside the `[-0.5, +0.5]` PMV band, it issues an immediate emergency override, bypassing the coordinator. The **Guardrail Engine** provides deterministic rate-limiting (max 3°C change per cycle) and absolute floor/ceiling enforcement.

---

## Technical Stack
- **Simulation**: EnergyPlus v26.1.0 (`RefBldgSmallOfficeNew2004_Chicago.idf`)
- **Intelligence**: `qwen2.5:7b-instruct` running locally via Ollama
- **Integration**: Model Context Protocol (MCP) using `fastmcp`
- **Concurrency**: `asyncio.gather` for parallel Zone Agent execution

## Running the Platform
Launch the MCP server and EnergyPlus bridge in Terminal 1:
```bash
python mcp_server/server.py
```
*(In a separate terminal, run the orchestrator)*
```bash
python agent/orchestrator.py
```
*(In a third terminal, run the bridge)*
```bash
python bridge/ep_runner.py
```
*(Wait, the architecture has Orchestrator calling MCP, and EP Runner calling MCP? Actually, the MCP server runs standalone. Orchestrator and EP_Runner both read/write to the `logs/` directory through tools or directly.)*
