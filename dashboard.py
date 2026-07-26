import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go

st.set_page_config(page_title="Eco-Loop Dashboard", layout="wide")
st.title("🌱 Eco-Loop: Quantitative Savings Dashboard")
st.markdown("Comparing Baseline Fixed-Schedule vs AI-Driven Closed-Loop Control")

def load_data(run_type):
    base_dir = os.path.dirname(__file__)
    csv_path = os.path.join(base_dir, "analysis", "outputs", run_type, "eplusout.csv")
    
    if not os.path.exists(csv_path):
        return None
        
    df = pd.read_csv(csv_path)
    
    pmv_cols = [c for c in df.columns if 'PMV' in c]
    energy_cols = [c for c in df.columns if 'Electricity' in c and ('HVAC' in c or 'Facility' in c)]
    
    pmv_data = df[pmv_cols[0]] if pmv_cols else pd.Series([0]*len(df))
    energy_data = df[energy_cols[0]] if energy_cols else pd.Series([0]*len(df))
    
    if energy_cols and '(J)' in energy_cols[0]:
        kwh = energy_data.sum() / 3.6e6
    elif energy_cols and '(W)' in energy_cols[0]:
        kwh = (energy_data.sum() * 1.0) / 1000.0
    else:
        kwh = energy_data.sum()
        
    return {
        "df": df,
        "kwh": kwh,
        "pmv": pmv_data,
        "time": df.index
    }

baseline = load_data("baseline")
agent = load_data("agent")

if not baseline or not agent:
    st.warning("Simulation data not found. Please run both baseline and agent simulations first to generate the EPlus CSVs.")
else:
    st.header("Performance Metrics")
    savings = baseline['kwh'] - agent['kwh']
    savings_pct = (savings / baseline['kwh'] * 100) if baseline['kwh'] > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Baseline HVAC Energy", f"{baseline['kwh']:,.1f} kWh")
    col2.metric("Agent HVAC Energy", f"{agent['kwh']:,.1f} kWh", delta=f"-{savings_pct:.1f}%", delta_color="inverse")
    
    pmv_violations = ((agent['pmv'] > 0.5) | (agent['pmv'] < -0.5)).sum()
    col3.metric("Agent Comfort Violations", f"{pmv_violations} timesteps", delta=f"Limit: ±0.5 PMV", delta_color="off")
    
    colA, colB = st.columns(2)
    
    with colA:
        st.header("Energy Savings")
        fig_energy = go.Figure(data=[
            go.Bar(name='Baseline', x=['HVAC Energy'], y=[baseline['kwh']], marker_color='#555555'),
            go.Bar(name='Eco-Loop Agent', x=['HVAC Energy'], y=[agent['kwh']], marker_color='#2ca02c')
        ])
        fig_energy.update_layout(barmode='group', yaxis_title="Total kWh")
        st.plotly_chart(fig_energy, use_container_width=True)
        
    with colB:
        st.header("Thermal Comfort (PMV)")
        fig_pmv = go.Figure()
        fig_pmv.add_trace(go.Scatter(x=baseline['time'], y=baseline['pmv'], mode='lines', name='Baseline PMV', line=dict(color='gray', dash='dash')))
        fig_pmv.add_trace(go.Scatter(x=agent['time'], y=agent['pmv'], mode='lines', name='Agent PMV', line=dict(color='green', width=2)))
        fig_pmv.add_hrect(y0=-0.5, y1=0.5, line_width=0, fillcolor="green", opacity=0.1, annotation_text="Safe Comfort Band")
        fig_pmv.update_layout(yaxis_title="PMV", xaxis_title="Timestep")
        st.plotly_chart(fig_pmv, use_container_width=True)
