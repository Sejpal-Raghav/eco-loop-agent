import streamlit as st
import pandas as pd
import json
import os
import plotly.graph_objects as go
from datetime import datetime

st.set_page_config(page_title="Eco-Loop Multi‑Agent Mission Control", layout="wide")
st.title("Eco-Loop: Multi‑Agent Workflow Demonstration")
st.markdown("Visualizing the 5‑layer cognitive architecture in real‑time (or from a pre‑generated log).")

# ---------- Helper functions ----------

def load_jsonl(path):
    """Load a JSONL file and return a list of dicts."""
    if not os.path.exists(path):
        return []
    records = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except Exception:
                    continue
    return records

def load_state_history():
    hist_path = os.path.join("logs", "state_history.jsonl")
    return load_jsonl(hist_path)

def load_decisions():
    dec_path = os.path.join("logs", "decisions.jsonl")
    return load_jsonl(dec_path)

def load_zone_proposals():
    dir_path = os.path.join("logs", "zone_proposals")
    proposals = {}
    if not os.path.isdir(dir_path):
        return proposals
    for fname in os.listdir(dir_path):
        if fname.endswith('.json'):
            zone = fname.replace('.json', '')
            with open(os.path.join(dir_path, fname), 'r') as f:
                proposals[zone] = json.load(f)
    return proposals

def load_coordinator_decision():
    path = os.path.join("logs", "coordinator_decision.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        return json.load(f)

def load_comfort_overrides():
    dir_path = os.path.join("logs", "comfort_overrides")
    overrides = {}
    if not os.path.isdir(dir_path):
        return overrides
    for fname in os.listdir(dir_path):
        if fname.endswith('.json'):
            zone = fname.replace('.json', '')
            with open(os.path.join(dir_path, fname), 'r') as f:
                overrides[zone] = json.load(f)
    return overrides

def load_anomalies():
    # anomalies are stored under each state entry under key 'anomalies'
    history = load_state_history()
    if not history:
        return []
    # pull the latest entry's anomalies for display
    latest = history[-1]
    return latest.get('anomalies', [])

# ---------- Load data ----------
state_history = load_state_history()
if not state_history:
    st.warning("No state history found – run `generate_demo_data.py` first to produce demo logs.")
    st.stop()

decisions = load_decisions()
zone_proposals = load_zone_proposals()
coord_decision = load_coordinator_decision()
comfort_overrides = load_comfort_overrides()
anomalies = load_anomalies()

# ---------- Layout ----------
# 1️⃣ Planning Layer – show the active strategy (stored in logs/current_strategy.json)
strategy_path = os.path.join("logs", "current_strategy.json")
if os.path.exists(strategy_path):
    with open(strategy_path, "r") as f:
        strategy = json.load(f)
    st.subheader("🧭 Planning Layer – Forecast Planner Strategy")
    st.json(strategy)
else:
    st.subheader("🧭 Planning Layer – No strategy file found")

# 2️⃣ Perception Layer – show latest anomalies (if any)
if anomalies:
    st.subheader("🔍 Perception Layer – Anomaly Flags")
    for a in anomalies:
        st.info(a)
else:
    st.subheader("🔍 Perception Layer – No anomalies detected")

# 3️⃣ Reasoning Layer – Zone agents proposals vs Coordinator decision
st.subheader("🤖 Reasoning Layer – Zone Proposals & Coordinator Consolidation")
col1, col2 = st.columns([2, 1])
with col1:
    # Table of proposals
    if zone_proposals:
        data = []
        for zone, prop in zone_proposals.items():
            data.append({
                "Zone": zone,
                "Heating (°C)": prop.get('heating_c'),
                "Cooling (°C)": prop.get('cooling_c'),
                "Reasoning": prop.get('reasoning')
            })
        df_props = pd.DataFrame(data)
        st.table(df_props)
    else:
        st.info("No zone proposals present – they will appear after each orchestrator tick.")
    
    # Show coordinator's approved setpoints
    if coord_decision:
        st.markdown("**Coordinator Approved Setpoints**")
        df_coords = pd.DataFrame([{
            "Zone": z,
            "Heating (°C)": vals.get('heating_c'),
            "Cooling (°C)": vals.get('cooling_c')
        } for z, vals in coord_decision.items()])
        st.table(df_coords)
    else:
        st.info("Coordinator decision not yet written.")
with col2:
    # Highlight any conflicts – e.g., total demand cap violated (we simulate a flag in the strategy)
    if strategy.get('peak_demand_cap_kw'):
        # compute a pseudo total demand from state history (simple sum of facility_total_kw for last entry)
        total_kw = state_history[-1].get('facility_total_kw', 0)
        cap = strategy.get('peak_demand_cap_kw')
        if total_kw > cap:
            st.error(f"⚡ Demand Cap Exceeded: {total_kw:.1f} kW > {cap} kW – Coordinator forced trade‑offs.")
        else:
            st.success(f"⚡ Current Demand: {total_kw:.1f} kW (within cap {cap} kW)")

# 4️⃣ Safety Layer – Comfort Auditor overrides
st.subheader("🛡️ Safety Layer – Comfort Auditor Overrides")
if comfort_overrides:
    for zone, ov in comfort_overrides.items():
        st.warning(f"🚨 Override in {zone}: Heating {ov.get('heating_c')} °C, Cooling {ov.get('cooling_c')} °C – {ov.get('reason')}")
else:
    st.info("No comfort overrides – all zones stayed within the ±0.5 PMV band.")

# 5️⃣ Performance Summary – Energy & Comfort over time
st.subheader("📈 Performance Summary")
# Build a time series from state history
times = [datetime.fromisoformat(entry['sim_time']) for entry in state_history]
facility_kw = [entry['facility_total_kw'] for entry in state_history]
pmv_series = []
for entry in state_history:
    # average absolute PMV across zones (for demo simplicity)
    zones = entry.get('zones', [])
    if zones:
        avg_pmv = sum(abs(z.get('pmv',0)) for z in zones) / len(zones)
    else:
        avg_pmv = 0
    pmv_series.append(avg_pmv)

colA, colB = st.columns(2)
with colA:
    fig_energy = go.Figure()
    fig_energy.add_trace(go.Scatter(x=times, y=facility_kw, mode='lines', name='Facility kW'))
    fig_energy.update_layout(title='Facility Power Demand', xaxis_title='Simulation Time', yaxis_title='kW')
    st.plotly_chart(fig_energy, use_container_width=True)
with colB:
    fig_pmv = go.Figure()
    fig_pmv.add_trace(go.Scatter(x=times, y=pmv_series, mode='lines', name='Avg |PMV|'))
    fig_pmv.add_hline(y=0.5, line_dash='dot', line_color='green', annotation_text='PMV limit')
    fig_pmv.update_layout(title='Average Absolute PMV', xaxis_title='Simulation Time', yaxis_title='|PMV|')
    st.plotly_chart(fig_pmv, use_container_width=True)

# Footer – brief explanation for CTO audience
st.caption("\nThe dashboard shows each cognitive layer in action: Planning (forecast & strategy), Perception (sensor sanity), Reasoning (zone agents + coordinator), Safety (auditor overrides), and the resulting performance. All data comes from the logged JSONL files, so the system can be replayed offline for interview demos.")
