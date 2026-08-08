import sys
import os
import json
import time

EPLUS_DIR = 'C:\\EnergyPlusV26-1-0'
if EPLUS_DIR not in sys.path:
    sys.path.append(EPLUS_DIR)

try:
    from pyenergyplus.api import EnergyPlusAPI
except ImportError:
    print(f'Failed to import pyenergyplus. Ensure EnergyPlus is installed at {EPLUS_DIR}')
    sys.exit(1)

from bridge.perception.state_compressor import StateCompressor
from bridge.perception.anomaly_detector import AnomalyDetector
from bridge.logger import DecisionLogger
from bridge.safety.guardrails import ActionGuardrail

class EPState:
    IDLE = 'idle'
    RUNNING = 'running'
    ERROR = 'error'
    STOPPED = 'stopped'

class EPlusRunner:
    def __init__(self, idf_path, epw_path):
        self.api = EnergyPlusAPI()
        self.state = self.api.state_manager.new_state()
        self.idf_path = idf_path
        self.epw_path = epw_path
        
        self.sensor_handles = {}
        self.actuator_handles = {}
        
        self.compressor = StateCompressor(interval_minutes=30)
        self.anomaly_detector = AnomalyDetector()
        
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        self.logger = DecisionLogger(os.path.join(logs_dir, 'decisions.jsonl'))
        self.error_log_path = os.path.join(logs_dir, 'errors.jsonl')
        
        self.guardrail = ActionGuardrail()
        self.lifecycle_state = EPState.IDLE
        self.last_action_time = None
        
        self.zones = ['CORE_ZN', 'PERIMETER_ZN_1', 'PERIMETER_ZN_2', 'PERIMETER_ZN_3', 'PERIMETER_ZN_4']
        
        self.api.runtime.callback_begin_zone_timestep_after_init_heat_balance(self.state, self._begin_zone_timestep_callback)

    def _log_error(self, error_type, message):
        record = {'timestamp': time.time(), 'type': error_type, 'message': message}
        with open(self.error_log_path, 'a') as f:
            f.write(json.dumps(record) + '\n')

    def _get_sensor(self, state, var_name, var_key):
        key = f"{var_name}_{var_key}"
        if key not in self.sensor_handles:
            handle = self.api.exchange.get_variable_handle(state, var_name, var_key)
            if handle > 0:
                self.sensor_handles[key] = handle
        if key in self.sensor_handles:
            return self.api.exchange.get_variable_value(state, self.sensor_handles[key])
        return 0.0

    def _set_actuator(self, state, act_type, act_control, act_key, value):
        key = f"{act_type}_{act_control}_{act_key}"
        if key not in self.actuator_handles:
            handle = self.api.exchange.get_actuator_handle(state, act_type, act_control, act_key)
            if handle > 0:
                self.actuator_handles[key] = handle
        if key in self.actuator_handles:
            self.api.exchange.set_actuator_value(state, self.actuator_handles[key], value)

    def _begin_zone_timestep_callback(self, state):
        if not self.api.exchange.api_data_fully_ready(state):
            return
            
        current_sim_minutes = self.api.exchange.current_sim_time(state) * 60.0
        
        # 1. Read Sensors
        outdoor_temp = self._get_sensor(state, 'Site Outdoor Air Drybulb Temperature', 'Environment')
        facility_kw = self._get_sensor(state, 'Facility Total HVAC Electricity Demand Rate', 'Whole Building') / 1000.0
        
        zone_states = []
        for z in self.zones:
            temp = self._get_sensor(state, 'Zone Mean Air Temperature', z)
            pmv = self._get_sensor(state, 'Zone Thermal Comfort Fanger Model PMV', f"People {z}")
            heat_kw = self._get_sensor(state, 'Zone Air System Sensible Heating Rate', z)
            cool_kw = self._get_sensor(state, 'Zone Air System Sensible Cooling Rate', z)
            
            zone_states.append({
                'name': z,
                'mean_air_temp_c': round(temp, 2),
                'pmv': round(pmv, 2),
                'hvac_electricity_kw': round((heat_kw + cool_kw) / 1000.0, 2)
            })
            
        # 2. Compress State
        year = self.api.exchange.year(state)
        month = self.api.exchange.month(state)
        day = self.api.exchange.day_of_month(state)
        hour = self.api.exchange.hour(state)
        minute = int(self.api.exchange.minutes(state))
        sim_time_str = f'{year}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00'
        
        self.compressor.add_reading(sim_time_str, outdoor_temp, zone_states, facility_kw)
        
        if self.compressor.should_compress(current_sim_minutes):
            raw_state = {
                "outdoor_temp": outdoor_temp,
                "facility_kw": facility_kw,
                "zones": zone_states
            }
            flags = self.anomaly_detector.detect(raw_state)
            state_summary = self.compressor.compress(current_sim_minutes, anomalies=flags)
            
            if state_summary:
                logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
                with open(os.path.join(logs_dir, 'latest_state.json'), 'w') as f:
                    json.dump(state_summary, f)
                    
                # 3. Read Actions (Overrides first, then Coordinator decision)
                action_dict = {}
                
                # Check coordinator decision
                coord_file = os.path.join(logs_dir, 'coordinator_decision.json')
                if os.path.exists(coord_file):
                    try:
                        with open(coord_file, 'r') as f:
                            action_dict = json.load(f)
                        os.remove(coord_file)
                    except Exception as e:
                        self._log_error('coordinator_parse_error', str(e))
                        
                # Check comfort overrides
                overrides_dir = os.path.join(logs_dir, 'comfort_overrides')
                os.makedirs(overrides_dir, exist_ok=True)
                for f_name in os.listdir(overrides_dir):
                    if f_name.endswith('.json'):
                        try:
                            z_name = f_name.replace('.json', '')
                            with open(os.path.join(overrides_dir, f_name), 'r') as f:
                                override = json.load(f)
                            action_dict[z_name] = override
                            os.remove(os.path.join(overrides_dir, f_name))
                        except Exception:
                            pass

                if action_dict:
                    clamped_actions, was_clamped, reasons = self.guardrail.validate_and_clamp(action_dict, state_summary)
                    
                    for z, act in clamped_actions.items():
                        self._set_actuator(state, 'Zone Temperature Control', 'Heating Setpoint', z, act['heating_c'])
                        self._set_actuator(state, 'Zone Temperature Control', 'Cooling Setpoint', z, act['cooling_c'])
                        
                    self.logger.log(state=state_summary, proposed_action=action_dict, clamped_action=clamped_actions, reason=reasons)
                    self.last_action_time = current_sim_minutes
                elif self.last_action_time is not None:
                    elapsed = current_sim_minutes - self.last_action_time
                    if elapsed > self.compressor.interval_minutes * 2:
                        self._log_error('agent_timeout', 'No decision received. Holding setpoints.')

    def run(self):
        self.lifecycle_state = EPState.RUNNING
        print(f'Starting EnergyPlus simulation in {self.lifecycle_state} state...')
        out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'analysis', 'outputs')
        os.makedirs(out_dir, exist_ok=True)
        try:
            result = self.api.runtime.run_energyplus(self.state, ['-w', self.epw_path, '-d', out_dir, self.idf_path])
            if result == 0:
                self.lifecycle_state = EPState.STOPPED
                print('Simulation completed successfully.')
            else:
                self.lifecycle_state = EPState.ERROR
                print(f'Simulation failed with code {result}.')
        except Exception as e:
            self.lifecycle_state = EPState.ERROR
            self._log_error('fatal_exception', str(e))
        finally:
            self.api.state_manager.delete_state(self.state)

if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    base_dir = os.path.dirname(os.path.dirname(__file__))
    idf = os.path.join(base_dir, 'models', 'agent_model.idf')
    epw = os.path.join(base_dir, 'models', 'weather.epw')
    
    if not os.path.exists(idf):
        print(f"ERROR: {idf} not found.")
        sys.exit(1)
        
    runner = EPlusRunner(idf, epw)
    runner.run()