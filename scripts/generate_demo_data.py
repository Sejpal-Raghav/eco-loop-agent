"""
Eco-Loop Demo Data Generator
Produces a realistic 24-hour simulation log for the Mission Control dashboard.
No EnergyPlus or Ollama required.

Usage:
    python scripts/generate_demo_data.py

Output:
    logs/state_history.jsonl
    logs/decisions.jsonl
    logs/current_strategy.json
    logs/latest_state.json
    logs/zone_proposals/*.json
    logs/coordinator_decision.json
    logs/comfort_overrides/*.json
    dashboard/demo_data.js
"""

import json
import os
import math
import random

random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
PROPOSALS_DIR = os.path.join(LOGS_DIR, 'zone_proposals')
OVERRIDES_DIR = os.path.join(LOGS_DIR, 'comfort_overrides')
DASHBOARD_DIR = os.path.join(BASE_DIR, 'dashboard')

ZONES = ['CORE_ZN', 'PERIMETER_ZN_1', 'PERIMETER_ZN_2', 'PERIMETER_ZN_3', 'PERIMETER_ZN_4']

ZONE_CHARACTERISTICS = {
    'CORE_ZN':         {'solar_gain': 0.0, 'thermal_mass': 1.2, 'base_temp_offset': 0.0,  'desc': 'Interior zone, stable'},
    'PERIMETER_ZN_1':  {'solar_gain': 0.8, 'thermal_mass': 0.9, 'base_temp_offset': 0.5,  'desc': 'South-facing, high solar'},
    'PERIMETER_ZN_2':  {'solar_gain': 0.5, 'thermal_mass': 0.9, 'base_temp_offset': 0.3,  'desc': 'East-facing, morning peak'},
    'PERIMETER_ZN_3':  {'solar_gain': 0.2, 'thermal_mass': 0.8, 'base_temp_offset': -0.3, 'desc': 'North-facing, low solar'},
    'PERIMETER_ZN_4':  {'solar_gain': 0.6, 'thermal_mass': 0.9, 'base_temp_offset': 0.4,  'desc': 'West-facing, afternoon peak'},
}


def outdoor_temp(hour):
    """Realistic Chicago summer diurnal curve. Peak ~33C at 15:00, low ~20C at 05:00."""
    return 26.5 + 6.5 * math.sin(math.pi * (hour - 9) / 12)


def solar_intensity(hour):
    """Normalized solar intensity 0-1, peaks at noon."""
    if hour < 6 or hour > 20:
        return 0.0
    return max(0, math.sin(math.pi * (hour - 6) / 14))


def grid_carbon(hour):
    """gCO2/kWh, peaks mid-afternoon when gas peakers fire."""
    return 420 + 180 * math.sin(math.pi * (hour - 8) / 10) + random.uniform(-15, 15)


def compute_zone_temp(hour, zone_name, outdoor, solar):
    """Simulated zone temperature based on outdoor temp, solar, and zone characteristics."""
    char = ZONE_CHARACTERISTICS[zone_name]
    base = 22.5 + char['base_temp_offset']
    outdoor_influence = (outdoor - 22.5) * 0.15 / char['thermal_mass']
    solar_influence = solar * char['solar_gain'] * 2.5
    # HVAC keeps things roughly in range but with realistic drift
    hvac_correction = -0.4 * (base + outdoor_influence + solar_influence - 23.0)
    noise = random.uniform(-0.3, 0.3)
    return round(base + outdoor_influence + solar_influence + hvac_correction + noise, 2)


def compute_pmv(zone_temp, outdoor):
    """Simplified PMV approximation. Comfort band is 22-25C."""
    neutral = 23.5
    pmv = (zone_temp - neutral) * 0.35
    return round(max(-2.0, min(2.0, pmv + random.uniform(-0.05, 0.05))), 2)


def compute_hvac_kw(zone_temp, outdoor, zone_name):
    """HVAC energy consumption estimate."""
    delta = abs(zone_temp - outdoor)
    base_kw = delta * 0.6 + random.uniform(0.5, 1.5)
    return round(base_kw, 2)


def generate_zone_proposal(zone_name, zone_temp, pmv, strategy_mode):
    """Simulate what a zone agent would propose."""
    if strategy_mode == 'pre-cool':
        heating = round(20.0 + random.uniform(-0.5, 0.5), 1)
        cooling = round(23.0 + random.uniform(-0.5, 0.5), 1)
        reasoning = f"Strategy is pre-cool. Lowering cooling setpoint to take advantage of low carbon intensity."
    elif strategy_mode == 'demand-shed':
        heating = round(20.0 + random.uniform(-0.5, 0.5), 1)
        cooling = round(25.5 + random.uniform(-0.5, 0.5), 1)
        reasoning = f"Peak demand period. Widening deadband to reduce load."
    else:
        heating = round(21.0 + random.uniform(-0.3, 0.3), 1)
        cooling = round(24.0 + random.uniform(-0.3, 0.3), 1)
        reasoning = f"Normal operation. Maintaining comfort within PMV bounds."

    # If PMV is drifting, adjust
    if pmv > 0.3:
        cooling = round(cooling - 0.5, 1)
        reasoning += f" PMV trending warm ({pmv}), tightening cooling."
    elif pmv < -0.3:
        heating = round(heating + 0.5, 1)
        reasoning += f" PMV trending cool ({pmv}), raising heating."

    return {
        'zone': zone_name,
        'heating_c': heating,
        'cooling_c': cooling,
        'reasoning': reasoning
    }


def generate_coordinator_decision(proposals, facility_kw, peak_cap):
    """Simulate coordinator consolidation. If over peak cap, force relaxation."""
    decision = {}
    reasoning_parts = []
    was_constrained = False

    for zone, prop in proposals.items():
        decision[zone] = {
            'heating_c': prop['heating_c'],
            'cooling_c': prop['cooling_c']
        }

    if facility_kw > peak_cap:
        was_constrained = True
        # Force the two highest-demand perimeter zones to relax
        for z in ['PERIMETER_ZN_3', 'PERIMETER_ZN_4']:
            if z in decision:
                decision[z]['cooling_c'] = round(decision[z]['cooling_c'] + 1.5, 1)
                reasoning_parts.append(f"Raised {z} cooling by 1.5C to shed load.")

    if was_constrained:
        reasoning = f"Facility at {facility_kw:.1f} kW exceeds {peak_cap} kW cap. " + " ".join(reasoning_parts)
    else:
        reasoning = f"All proposals within operational limits. Facility at {facility_kw:.1f} kW."

    return decision, reasoning, was_constrained


def generate_guardrail_clamps(decision, zone_states_dict):
    """Simulate guardrail clamping for out-of-bound setpoints."""
    clamped = {}
    reasons = {}
    ABS_HEAT_MIN, ABS_HEAT_MAX = 18.0, 24.0
    ABS_COOL_MIN, ABS_COOL_MAX = 22.0, 28.0

    for zone, sp in decision.items():
        h = max(ABS_HEAT_MIN, min(ABS_HEAT_MAX, sp['heating_c']))
        c = max(ABS_COOL_MIN, min(ABS_COOL_MAX, sp['cooling_c']))
        if c <= h:
            c = h + 2.0  # enforce deadband

        was_clamped = (h != sp['heating_c'] or c != sp['cooling_c'])
        clamped[zone] = {'heating_c': round(h, 1), 'cooling_c': round(c, 1)}
        if was_clamped:
            reasons[zone] = f"Clamped from H:{sp['heating_c']} C:{sp['cooling_c']} to H:{h} C:{c}"

    return clamped, reasons


def get_strategy_for_hour(hour):
    """Determine the planner's active strategy based on time of day."""
    if hour < 7:
        return {
            'strategy': 'pre-cool',
            'mode': 'pre-cool',
            'reasoning': 'Grid carbon is low overnight. Pre-cooling building thermal mass to reduce afternoon peak demand.',
            'peak_demand_cap_kw': 50,
            'target_pmv_band': [-0.3, 0.3]
        }
    elif 12 <= hour <= 17:
        return {
            'strategy': 'demand-shed',
            'mode': 'demand-shed',
            'reasoning': 'Peak electricity pricing and high grid carbon (>550 gCO2/kWh). Widening comfort band to coast on stored cooling.',
            'peak_demand_cap_kw': 45,
            'target_pmv_band': [-0.5, 0.5]
        }
    else:
        return {
            'strategy': 'balanced',
            'mode': 'balanced',
            'reasoning': 'Normal operation. Balancing comfort and efficiency with moderate grid carbon.',
            'peak_demand_cap_kw': 50,
            'target_pmv_band': [-0.3, 0.3]
        }


def main():
    # Create output directories
    for d in [LOGS_DIR, PROPOSALS_DIR, OVERRIDES_DIR, DASHBOARD_DIR]:
        os.makedirs(d, exist_ok=True)

    # Clear old log files
    for fname in ['state_history.jsonl', 'decisions.jsonl']:
        path = os.path.join(LOGS_DIR, fname)
        if os.path.exists(path):
            os.remove(path)
    for d in [PROPOSALS_DIR, OVERRIDES_DIR]:
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))

    all_ticks = []
    state_history = []
    decisions_log = []

    print("Generating 24-hour demo data (48 ticks at 30-min intervals)...")
    print()

    for tick in range(48):
        hour = tick * 0.5
        hour_int = int(hour)
        minute = int((hour % 1) * 60)
        sim_time = f"2024-07-15T{hour_int:02d}:{minute:02d}:00"

        outdoor = round(outdoor_temp(hour), 2)
        solar = round(solar_intensity(hour), 3)
        carbon = round(grid_carbon(hour), 1)
        strategy = get_strategy_for_hour(hour)

        # --- Generate zone states ---
        zone_states = []
        zone_states_dict = {}
        for z in ZONES:
            temp = compute_zone_temp(hour, z, outdoor, solar)
            pmv = compute_pmv(temp, outdoor)
            hvac_kw = compute_hvac_kw(temp, outdoor, z)
            zs = {'name': z, 'temp_c': temp, 'pmv': pmv, 'hvac_kw': hvac_kw}
            zone_states.append(zs)
            zone_states_dict[z] = zs

        facility_kw = round(sum(z['hvac_kw'] for z in zone_states), 2)

        # --- Anomaly detection ---
        anomalies = []
        events = []

        # EVENT 1: Hour 6 — Sensor anomaly on PERIMETER_ZN_2
        if tick == 12:  # 06:00
            zone_states[2]['temp_c'] = -40.0
            anomalies.append({
                'zone': 'PERIMETER_ZN_2',
                'type': 'impossible_temperature',
                'value': -40.0,
                'message': 'PERIMETER_ZN_2 reported -40.0 C. Physically impossible. Flagged as sensor fault.'
            })
            events.append({
                'type': 'anomaly',
                'layer': 'Perception',
                'severity': 'warning',
                'message': 'Sensor fault detected on PERIMETER_ZN_2: -40.0 C reading flagged and excluded from agent context.'
            })
            print(f"  [{sim_time}] EVENT: Sensor anomaly injected on PERIMETER_ZN_2 (-40 C)")

        # --- Zone agent proposals ---
        proposals = {}
        for z in ZONES:
            prop = generate_zone_proposal(z, zone_states_dict[z]['temp_c'], zone_states_dict[z]['pmv'], strategy['mode'])
            proposals[z] = prop

        # EVENT 2: Hour 14 — Peak demand conflict
        if tick == 28:  # 14:00
            # Make all zones request aggressive cooling
            for z in ZONES:
                proposals[z]['cooling_c'] = round(21.5 + random.uniform(0, 0.5), 1)
                proposals[z]['reasoning'] = f"Outdoor at {outdoor}C. Requesting aggressive cooling to prevent PMV breach."
            facility_kw = 58.3  # Force over the cap
            events.append({
                'type': 'demand_conflict',
                'layer': 'Reasoning',
                'severity': 'critical',
                'message': f'All 5 zones requested aggressive cooling. Facility demand hit {facility_kw} kW, exceeding 45 kW cap. Coordinator forced PERIMETER_ZN_3 and ZN_4 to relax setpoints.'
            })
            print(f"  [{sim_time}] EVENT: Peak demand conflict ({facility_kw} kW > 45 kW cap)")

        # --- Coordinator decision ---
        coord_decision, coord_reasoning, was_constrained = generate_coordinator_decision(
            proposals, facility_kw, strategy.get('peak_demand_cap_kw', 50)
        )

        # --- Guardrail clamping ---
        clamped, clamp_reasons = generate_guardrail_clamps(coord_decision, zone_states_dict)

        # --- Comfort overrides ---
        comfort_overrides = {}

        # EVENT 3: Hour 18 — Comfort override on PERIMETER_ZN_3
        if tick == 36:  # 18:00
            zone_states[3]['pmv'] = -0.62
            zone_states[3]['temp_c'] = 21.1
            comfort_overrides['PERIMETER_ZN_3'] = {
                'heating_c': 22.0,
                'cooling_c': 25.0,
                'reason': 'PMV at -0.62 breached the -0.5 safety limit. Emergency override: raising heating setpoint to 22.0 C.'
            }
            events.append({
                'type': 'comfort_override',
                'layer': 'Safety',
                'severity': 'critical',
                'message': 'PERIMETER_ZN_3 PMV dropped to -0.62. Comfort Auditor bypassed Coordinator and issued emergency heating override.'
            })
            print(f"  [{sim_time}] EVENT: Comfort override on PERIMETER_ZN_3 (PMV -0.62)")

        # --- Assemble tick record ---
        state_record = {
            'sim_time': sim_time,
            'outdoor_temp_c': outdoor,
            'solar_intensity': solar,
            'grid_carbon_gco2_kwh': carbon,
            'facility_total_kw': facility_kw,
            'rolling_30min_avg_kw': round(facility_kw + random.uniform(-2, 2), 2),
            'zones': zone_states,
            'anomalies': anomalies
        }

        tick_record = {
            'tick': tick,
            'sim_time': sim_time,
            'hour': hour,
            'outdoor_temp_c': outdoor,
            'solar_intensity': solar,
            'grid_carbon_gco2_kwh': carbon,
            'facility_total_kw': facility_kw,
            'zones': zone_states,
            'anomalies': anomalies,
            'strategy': strategy,
            'zone_proposals': proposals,
            'coordinator_decision': coord_decision,
            'coordinator_reasoning': coord_reasoning,
            'coordinator_constrained': was_constrained,
            'guardrail_clamps': clamp_reasons,
            'clamped_setpoints': clamped,
            'comfort_overrides': comfort_overrides,
            'events': events
        }

        all_ticks.append(tick_record)
        state_history.append(state_record)

        decision_record = {
            'state': {'sim_time': sim_time, 'facility_total_kw': facility_kw},
            'proposed_action': {z: {'heating_c': p['heating_c'], 'cooling_c': p['cooling_c']} for z, p in proposals.items()},
            'clamped_action': clamped,
            'reason': clamp_reasons
        }
        decisions_log.append(decision_record)

    # --- Write log files (same format the real system uses) ---
    print()
    print("Writing log files...")

    # state_history.jsonl
    with open(os.path.join(LOGS_DIR, 'state_history.jsonl'), 'w') as f:
        for record in state_history:
            f.write(json.dumps(record) + '\n')
    print(f"  logs/state_history.jsonl ({len(state_history)} records)")

    # decisions.jsonl
    with open(os.path.join(LOGS_DIR, 'decisions.jsonl'), 'w') as f:
        for record in decisions_log:
            f.write(json.dumps(record) + '\n')
    print(f"  logs/decisions.jsonl ({len(decisions_log)} records)")

    # current_strategy.json (last strategy)
    with open(os.path.join(LOGS_DIR, 'current_strategy.json'), 'w') as f:
        json.dump(all_ticks[-1]['strategy'], f, indent=2)
    print("  logs/current_strategy.json")

    # latest_state.json (last state)
    with open(os.path.join(LOGS_DIR, 'latest_state.json'), 'w') as f:
        json.dump(state_history[-1], f, indent=2)
    print("  logs/latest_state.json")

    # zone_proposals (last tick's proposals)
    for z, prop in all_ticks[-1]['zone_proposals'].items():
        with open(os.path.join(PROPOSALS_DIR, f'{z}.json'), 'w') as f:
            json.dump(prop, f, indent=2)
    print(f"  logs/zone_proposals/ ({len(ZONES)} files)")

    # coordinator_decision.json (last tick)
    with open(os.path.join(LOGS_DIR, 'coordinator_decision.json'), 'w') as f:
        json.dump(all_ticks[-1]['coordinator_decision'], f, indent=2)
    print("  logs/coordinator_decision.json")

    # comfort_overrides (only the override event at tick 36)
    for tick_data in all_ticks:
        for zone, ov in tick_data['comfort_overrides'].items():
            with open(os.path.join(OVERRIDES_DIR, f'{zone}.json'), 'w') as f:
                json.dump(ov, f, indent=2)
    override_count = sum(1 for t in all_ticks for _ in t['comfort_overrides'])
    print(f"  logs/comfort_overrides/ ({override_count} files)")

    # --- Write consolidated dashboard JS ---
    demo_data_content = {
        'metadata': {
            'building': 'DOE RefBldg Small Office (Chicago)',
            'weather': 'USA_IL_Chicago-OHare TMY3',
            'model': 'qwen2.5:7b-instruct',
            'zones': ZONES,
            'ticks': 48,
            'interval_minutes': 30,
            'date': '2024-07-15'
        },
        'ticks': all_ticks
    }
    with open(os.path.join(DASHBOARD_DIR, 'demo_data.js'), 'w') as f:
        f.write("const DEMO_DATA = ")
        json.dump(demo_data_content, f, indent=2)
        f.write(";\n")
    print(f"  dashboard/demo_data.js ({len(all_ticks)} ticks)")

    # --- Summary ---
    total_energy = sum(t['facility_total_kw'] for t in all_ticks) * 0.5  # kWh (30 min intervals)
    pmv_violations = sum(1 for t in all_ticks for z in t['zones'] if abs(z['pmv']) > 0.5)
    clamp_count = sum(len(t['guardrail_clamps']) for t in all_ticks)
    override_events = sum(len(t['comfort_overrides']) for t in all_ticks)
    anomaly_events = sum(len(t['anomalies']) for t in all_ticks)

    print()
    print("=== Demo Data Summary ===")
    print(f"  Total Energy:       {total_energy:.1f} kWh")
    print(f"  PMV Violations:     {pmv_violations} zone-ticks")
    print(f"  Guardrail Clamps:   {clamp_count} zone-ticks")
    print(f"  Comfort Overrides:  {override_events}")
    print(f"  Sensor Anomalies:   {anomaly_events}")
    print()
    print("Done. Open dashboard/index.html to view the demo.")


if __name__ == '__main__':
    main()
