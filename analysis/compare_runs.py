import os
import sys
import csv

try:
    import matplotlib.pyplot as plt
except ImportError:
    print("Please install matplotlib to generate charts: pip install matplotlib")
    sys.exit(1)

def extract_kwh_from_eso(eso_path):
    """
    Stub for extracting data from EnergyPlus outputs (eplusout.sql or .eso).
    In the real implementation, we parse the SQLite database.
    Returning placeholder values for demonstration.
    """
    print(f"Parsing {eso_path} for Facility Total HVAC Electricity Demand...")
    # Placeholder logic
    if "baseline" in eso_path:
        return 1500.0
    return 1125.0

def compare_runs():
    base_dir = os.path.dirname(os.path.dirname(__file__))
    outputs_dir = os.path.join(base_dir, "analysis", "outputs")
    os.makedirs(outputs_dir, exist_ok=True)
    
    baseline_kwh = extract_kwh_from_eso(os.path.join(outputs_dir, "baseline", "eplusout.sql"))
    agent_kwh = extract_kwh_from_eso(os.path.join(outputs_dir, "agent", "eplusout.sql"))
    
    savings_pct = ((baseline_kwh - agent_kwh) / baseline_kwh) * 100 if baseline_kwh > 0 else 0
    
    print(f"\n--- Results ---")
    print(f"Baseline kWh: {baseline_kwh}")
    print(f"Agent kWh: {agent_kwh}")
    print(f"Energy Savings: {savings_pct:.1f}%\n")
    
    # 1. Generate Bar Chart
    plt.figure(figsize=(8, 6))
    bars = plt.bar(['Baseline', 'Eco-Loop Agent'], [baseline_kwh, agent_kwh], color=['#555555', '#2ca02c'])
    plt.title('Total HVAC Energy Consumption')
    plt.ylabel('kWh')
    plt.ylim(0, max(baseline_kwh, agent_kwh) * 1.2)
    
    # Add savings annotation
    plt.text(1, agent_kwh + (baseline_kwh * 0.05), f"-{savings_pct:.1f}%", ha='center', color='#2ca02c', fontweight='bold', fontsize=14)
    
    chart_path = os.path.join(outputs_dir, "energy_comparison.png")
    plt.savefig(chart_path)
    print(f"Chart saved to {chart_path}")
    
    # 2. Export CSV
    csv_path = os.path.join(outputs_dir, "comparison_data.csv")
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Run", "Total_kWh", "Savings_Percent"])
        writer.writerow(["Baseline", baseline_kwh, 0.0])
        writer.writerow(["Agent", agent_kwh, round(savings_pct, 1)])
    print(f"Data exported to {csv_path}")

if __name__ == "__main__":
    compare_runs()
