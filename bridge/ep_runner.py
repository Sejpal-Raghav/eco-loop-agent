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
        
        # Register the callback to read sensors
        self.api.runtime.callback_begin_zone_timestep_after_init_heat_balance(
            self.state, self._begin_zone_timestep_callback
        )
        
    def _begin_zone_timestep_callback(self, state):
        if not self.api.exchange.api_data_fully_ready(state):
            return
            
        # Dynamically get variable handles. 
        # Note: 'Core_Zone' is just an example key; it depends on the specific IDF.
        if 'zone_mean_temp' not in self.sensor_handles:
            handle = self.api.exchange.get_variable_handle(
                state, "Zone Mean Air Temperature", "Core_Zone"
            )
            if handle > 0:
                self.sensor_handles['zone_mean_temp'] = handle
        
        # Read and optionally print sensor value
        if 'zone_mean_temp' in self.sensor_handles:
            val = self.api.exchange.get_variable_value(state, self.sensor_handles['zone_mean_temp'])
            # Uncomment to verify it's reading at each timestep:
            # print(f"Core Zone Mean Temp: {val:.2f} C")
            
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
    idf = os.path.join(base_dir, "models", "baseline.idf")
    epw = os.path.join(base_dir, "models", "weather.epw")
    
    # Check if the dummy files are still there instead of real ones
    with open(idf, 'r') as f:
        content = f.read()
        if content.startswith('! Please copy'):
            print("ERROR: Please replace models/baseline.idf with a real EnergyPlus IDF file.")
            sys.exit(1)
            
    runner = EPlusRunner(idf, epw)
    runner.run()
