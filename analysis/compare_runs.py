import os
import sys
import csv
import pandas as pd

try:
    import matplotlib.pyplot as plt
except ImportError:
    print("Please install matplotlib to generate charts: pip install matplotlib")
    sys.exit(1)

def extract_metrics_from_csv(csv_path):
    print(f"Parsing {csv_path} ...")
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return 0.0, [], []
        
    df = pd.read_csv(csv_path)
    
    # Dynamically find PMV and Energy columns from EPlus output
    pmv_cols = [c for c in df.columns if 'PMV' in c]
    energy_cols = [c for c in df.columns if 'Electricity' in c and ('HVAC' in c or 'Facility' in c)]
    
    pmv = df[pmv_cols[0]].values if pmv_cols else [0.0] * len(df)
    
    if energy_cols:
        energy_series = df[energy_cols[0]]
        if '(J)' in energy_cols[0]:
            kwh = energy_series.sum() / 3.6e6
        elif '(W)' in energy_cols[0]:
            kwh = (energy_series.sum() * 1.0) / 1000.0 
        else:
            kwh = energy_series.sum()
    else:
        kwh = 0.0
        
    time_steps = list(range(len(df)))
    return kwh, pmv, time_steps

def compare_runs():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    outputs_dir = os.path.join(base_dir, "analysis", "outputs")
    
    baseline_csv = os.path.join(outputs_dir, "baseline", "eplusout.csv")
    agent_csv = os.path.join(outputs_dir, "agent", "eplusout.csv")
    
    baseline_kwh, baseline_pmv, time_steps = extract_metrics_from_csv(baseline_csv)
    agent_kwh, agent_pmv, _ = extract_metrics_from_csv(agent_csv)
    
    if baseline_kwh == 0 and agent_kwh == 0:
        print("Warning: Could not extract energy data. Ensure EPlus outputs eplusout.csv with HVAC Electricity meters.")
        
    savings_pct = ((baseline_kwh - agent_kwh) / baseline_kwh) * 100 if baseline_kwh > 0 else 0
    
    print(f"\n--- Results ---")
    print(f"Baseline kWh: {baseline_kwh:.2f}")
    print(f"Agent kWh: {agent_kwh:.2f}")
    print(f"Energy Savings: {savings_pct:.1f}%\n")
    
    # 1. Generate Bar Chart (Energy)
    plt.figure(figsize=(8, 6))
    bars = plt.bar(['Baseline', 'Eco-Loop Agent'], [baseline_kwh, agent_kwh], color=['#555555', '#2ca02c'])
    plt.title('Total HVAC Energy Consumption')
    plt.ylabel('kWh')
    plt.ylim(0, max(baseline_kwh, agent_kwh) * 1.2 if max(baseline_kwh, agent_kwh) > 0 else 1)
    plt.text(1, agent_kwh + (baseline_kwh * 0.05), f"-{savings_pct:.1f}%", ha='center', color='#2ca02c', fontweight='bold', fontsize=14)
    energy_chart_path = os.path.join(outputs_dir, "energy_comparison.png")
    plt.savefig(energy_chart_path)
    print(f"Energy Chart saved to {energy_chart_path}")
    plt.close()
    
    # 2. Generate Line Chart (PMV)
    plt.figure(figsize=(10, 5))
    if len(time_steps) > 0:
        plt.plot(time_steps, baseline_pmv, label='Baseline PMV', color='gray', linestyle='--')
        plt.plot(time_steps, agent_pmv, label='Agent PMV', color='green', linewidth=2)
    
    plt.axhspan(-0.5, 0.5, color='lightgreen', alpha=0.3, label='Comfort Band (-0.5 to 0.5)')
    plt.title('Thermal Comfort (PMV) Over Time')
    plt.ylabel('Predicted Mean Vote (PMV)')
    plt.xlabel('Simulation Timestep')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    pmv_chart_path = os.path.join(outputs_dir, "pmv_comparison.png")
    plt.savefig(pmv_chart_path)
    print(f"PMV Chart saved to {pmv_chart_path}")
    plt.close()
    
    # 3. Export CSV
    csv_path = os.path.join(outputs_dir, "comparison_data.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Run", "Total_kWh", "Savings_Percent"])
        writer.writerow(["Baseline", baseline_kwh, 0.0])
        writer.writerow(["Agent", agent_kwh, round(savings_pct, 1)])
    print(f"Data exported to {csv_path}")

if __name__ == "__main__":
    compare_runs()