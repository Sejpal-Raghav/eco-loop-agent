import sys
import os

# Note: Adjust EPLUS_DIR to match your EnergyPlus installation path on Windows.
EPLUS_DIR = r"C:\EnergyPlusV24-1-0" 
if EPLUS_DIR not in sys.path:
    sys.path.append(EPLUS_DIR)

try:
    from pyenergyplus.api import EnergyPlusAPI
except ImportError:
    print(f"Failed to import pyenergyplus. Ensure EnergyPlus is installed at {EPLUS_DIR}")
    sys.exit(1)

class EPlusRunner:
    def __init__(self, idf_path, epw_path):
        self.api = EnergyPlusAPI()
        self.state = self.api.state_manager.new_state()
        self.idf_path = idf_path
        self.epw_path = epw_path
        
        self.sensor_handles = {}
        self.actuator_handles = {}
        
        # Register the callback to read sensors and apply actuators
        self.api.runtime.callback_begin_zone_timestep_after_init_heat_balance(
            self.state, self._begin_zone_timestep_callback
        )
        
    def _begin_zone_timestep_callback(self, state):
        if not self.api.exchange.api_data_fully_ready(state):
            return
            
        # 1. Get sensor handles
        if 'zone_mean_temp' not in self.sensor_handles:
            handle = self.api.exchange.get_variable_handle(
                state, "Zone Mean Air Temperature", "Core_Zone"
            )
            if handle > 0:
                self.sensor_handles['zone_mean_temp'] = handle
                
        # 2. Get actuator handles
        if 'cooling_setpoint' not in self.actuator_handles:
            # Note: EMS actuators must be explicitly enabled in the IDF.
            handle = self.api.exchange.get_actuator_handle(
                state, "Zone Temperature Control", "Cooling Setpoint", "Core_Zone"
            )
            if handle > 0:
                self.actuator_handles['cooling_setpoint'] = handle
        
        # 3. Read sensor and apply a "dumb rule" for testing (Step 2 requirement)
        if 'zone_mean_temp' in self.sensor_handles and 'cooling_setpoint' in self.actuator_handles:
            temp = self.api.exchange.get_variable_value(state, self.sensor_handles['zone_mean_temp'])
            
            # Dumb rule: if temp > 25, drop cooling setpoint by 1 to 24
            if temp > 25.0:
                new_setpoint = 24.0
                self.api.exchange.set_actuator_value(
                    state, self.actuator_handles['cooling_setpoint'], new_setpoint
                )
            else:
                self.api.exchange.set_actuator_value(
                    state, self.actuator_handles['cooling_setpoint'], 26.0
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
    base_dir = os.path.dirname(os.path.dirname(__file__))
    # Switch to the agent_model for step 2
    idf = os.path.join(base_dir, "models", "agent_model.idf")
    epw = os.path.join(base_dir, "models", "weather.epw")
    
    # Check if the dummy files are still there instead of real ones
    with open(idf, 'r') as f:
        content = f.read()
        if content.startswith('! Please copy'):
            print("ERROR: Please replace models/agent_model.idf with a real EnergyPlus IDF file containing EMS actuators.")
            sys.exit(1)
            
    runner = EPlusRunner(idf, epw)
    runner.run()
