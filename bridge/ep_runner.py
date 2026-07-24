import sys
import os

# Adjust EPLUS_DIR to match your EnergyPlus installation path on Windows.
EPLUS_DIR = r"C:\EnergyPlusV24-1-0" 
if EPLUS_DIR not in sys.path:
    sys.path.append(EPLUS_DIR)

try:
    from pyenergyplus.api import EnergyPlusAPI
except ImportError:
    print(f"Failed to import pyenergyplus. Ensure EnergyPlus is installed at {EPLUS_DIR}")
    sys.exit(1)

from bridge.state_compressor import StateCompressor
from bridge.logger import DecisionLogger

class EPlusRunner:
    def __init__(self, idf_path, epw_path):
        self.api = EnergyPlusAPI()
        self.state = self.api.state_manager.new_state()
        self.idf_path = idf_path
        self.epw_path = epw_path
        
        self.sensor_handles = {}
        self.actuator_handles = {}
        
        self.compressor = StateCompressor(interval_minutes=30)
        self.logger = DecisionLogger(os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "decisions.jsonl"))
        
        # Request more sensors for the state summary
        self.sensor_names = {
            "zone_mean_temp": ("Zone Mean Air Temperature", "Core_Zone"),
            "pmv": ("Zone Thermal Comfort Fanger Model PMV", "People Core_Zone"),
            "heating_kw": ("Zone Air System Sensible Heating Rate", "Core_Zone"),
            "cooling_kw": ("Zone Air System Sensible Cooling Rate", "Core_Zone"),
            "facility_kw": ("Facility Total HVAC Electricity Demand Rate", "Whole Building"),
            "outdoor_temp": ("Site Outdoor Air Drybulb Temperature", "Environment")
        }
        
        # Register the callback to read sensors and apply actuators
        self.api.runtime.callback_begin_zone_timestep_after_init_heat_balance(
            self.state, self._begin_zone_timestep_callback
        )
        
    def _begin_zone_timestep_callback(self, state):
        if not self.api.exchange.api_data_fully_ready(state):
            return
            
        # 1. Get sensor handles dynamically
        for key, (var_name, var_key) in self.sensor_names.items():
            if key not in self.sensor_handles:
                handle = self.api.exchange.get_variable_handle(state, var_name, var_key)
                if handle > 0:
                    self.sensor_handles[key] = handle
                    
        # 2. Get actuator handles
        if 'cooling_setpoint' not in self.actuator_handles:
            handle = self.api.exchange.get_actuator_handle(state, "Zone Temperature Control", "Cooling Setpoint", "Core_Zone")
            if handle > 0:
                self.actuator_handles['cooling_setpoint'] = handle
                
        if 'heating_setpoint' not in self.actuator_handles:
            handle = self.api.exchange.get_actuator_handle(state, "Zone Temperature Control", "Heating Setpoint", "Core_Zone")
            if handle > 0:
                self.actuator_handles['heating_setpoint'] = handle

        # 3. Read basic time
        year = self.api.exchange.year(state)
        month = self.api.exchange.month(state)
        day = self.api.exchange.day_of_month(state)
        hour = self.api.exchange.hour(state)
        minute = int(self.api.exchange.minutes(state))
        sim_time_str = f"{year}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00"
        
        current_sim_minutes = self.api.exchange.current_sim_time(state) * 60.0
        
        def get_val(k):
            return self.api.exchange.get_variable_value(state, self.sensor_handles[k]) if k in self.sensor_handles else 0.0

        outdoor_temp = get_val('outdoor_temp')
        facility_kw = get_val('facility_kw') / 1000.0 # Convert W to kW
        
        zone_states = [{
            "name": "Core_Zone",
            "mean_air_temp_c": round(get_val('zone_mean_temp'), 2),
            "pmv": round(get_val('pmv'), 2),
            "heating_setpoint_c": 21.0, # Placeholder until we read/write real setpoints properly
            "cooling_setpoint_c": 24.0, # Placeholder
            "hvac_electricity_kw": round((get_val('heating_kw') + get_val('cooling_kw')) / 1000.0, 2)
        }]
        
        # Add reading to compressor
        self.compressor.add_reading(sim_time_str, outdoor_temp, zone_states, facility_kw)
        
        # Check if we should compress and act (once every N minutes)
        if self.compressor.should_compress(current_sim_minutes):
            state_summary = self.compressor.compress(current_sim_minutes)
            if state_summary:
                # Apply dumb rule on a 30-minute cadence instead of every timestep
                temp = zone_states[0]['mean_air_temp_c']
                if temp > 25.0 and 'cooling_setpoint' in self.actuator_handles:
                    new_setpoint = 24.0
                    self.api.exchange.set_actuator_value(state, self.actuator_handles['cooling_setpoint'], new_setpoint)
                    
                    self.logger.log(
                        state=state_summary,
                        proposed_action={"cooling_setpoint": new_setpoint},
                        clamped_action={"cooling_setpoint": new_setpoint},
                        reason="Dumb rule triggered: temp > 25.0"
                    )
                
    def run(self):
        print(f"Starting EnergyPlus simulation...")
        print(f"IDF: {self.idf_path}")
        print(f"EPW: {self.epw_path}")
        
        out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "analysis", "outputs")
        os.makedirs(out_dir, exist_ok=True)
        
        result = self.api.runtime.run_energyplus(
            self.state, 
            [
                '-w', self.epw_path,
                '-d', out_dir,
                self.idf_path
            ]
        )
        
        if result == 0:
            print("Simulation completed successfully.")
        else:
            print(f"Simulation failed with code {result}.")
            
        self.api.state_manager.delete_state(self.state)

if __name__ == "__main__":
    # Ensure bridge is in PYTHONPATH
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    
    base_dir = os.path.dirname(os.path.dirname(__file__))
    idf = os.path.join(base_dir, "models", "agent_model.idf")
    epw = os.path.join(base_dir, "models", "weather.epw")
    
    with open(idf, 'r') as f:
        content = f.read()
        if content.startswith('! Please copy'):
            print("ERROR: Please replace models/agent_model.idf with a real EnergyPlus IDF file containing EMS actuators.")
            sys.exit(1)
            
    runner = EPlusRunner(idf, epw)
    runner.run()
