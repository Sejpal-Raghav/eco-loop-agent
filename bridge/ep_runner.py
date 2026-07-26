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
from bridge.state_compressor import StateCompressor
from bridge.logger import DecisionLogger
from bridge.guardrails import ActionGuardrail

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
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        self.logger = DecisionLogger(os.path.join(logs_dir, 'decisions.jsonl'))
        self.error_log_path = os.path.join(logs_dir, 'errors.jsonl')
        self.guardrail = ActionGuardrail()
        self.lifecycle_state = EPState.IDLE
        self.last_action_time = None
        self.sensor_names = {'zone_mean_temp': ('Zone Mean Air Temperature', 'CORE_ZN'), 'pmv': ('Zone Thermal Comfort Fanger Model PMV', 'People CORE_ZN'), 'heating_kw': ('Zone Air System Sensible Heating Rate', 'CORE_ZN'), 'cooling_kw': ('Zone Air System Sensible Cooling Rate', 'CORE_ZN'), 'facility_kw': ('Facility Total HVAC Electricity Demand Rate', 'Whole Building'), 'outdoor_temp': ('Site Outdoor Air Drybulb Temperature', 'Environment')}
        self.api.runtime.callback_begin_zone_timestep_after_init_heat_balance(self.state, self._begin_zone_timestep_callback)

    def _log_error(self, error_type, message):
        record = {'timestamp': time.time(), 'type': error_type, 'message': message}
        with open(self.error_log_path, 'a') as f:
            f.write(json.dumps(record) + '\n')

    def _begin_zone_timestep_callback(self, state):
        if not self.api.exchange.api_data_fully_ready(state):
            return
        for key, (var_name, var_key) in self.sensor_names.items():
            if key not in self.sensor_handles:
                handle = self.api.exchange.get_variable_handle(state, var_name, var_key)
                if handle > 0:
                    self.sensor_handles[key] = handle
        if 'cooling_setpoint' not in self.actuator_handles:
            handle = self.api.exchange.get_actuator_handle(state, 'Zone Temperature Control', 'Cooling Setpoint', 'CORE_ZN')
            if handle > 0:
                self.actuator_handles['cooling_setpoint'] = handle
        if 'heating_setpoint' not in self.actuator_handles:
            handle = self.api.exchange.get_actuator_handle(state, 'Zone Temperature Control', 'Heating Setpoint', 'CORE_ZN')
            if handle > 0:
                self.actuator_handles['heating_setpoint'] = handle
        year = self.api.exchange.year(state)
        month = self.api.exchange.month(state)
        day = self.api.exchange.day_of_month(state)
        hour = self.api.exchange.hour(state)
        minute = int(self.api.exchange.minutes(state))
        sim_time_str = f'{year}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00'
        current_sim_minutes = self.api.exchange.current_sim_time(state) * 60.0

        def get_val(k):
            return self.api.exchange.get_variable_value(state, self.sensor_handles[k]) if k in self.sensor_handles else 0.0
        outdoor_temp = get_val('outdoor_temp')
        facility_kw = get_val('facility_kw') / 1000.0
        pmv_val = get_val('pmv')
        zone_states = [{'name': 'CORE_ZN', 'mean_air_temp_c': round(get_val('zone_mean_temp'), 2), 'pmv': round(pmv_val, 2), 'heating_setpoint_c': 21.0, 'cooling_setpoint_c': 24.0, 'hvac_electricity_kw': round((get_val('heating_kw') + get_val('cooling_kw')) / 1000.0, 2)}]
        self.compressor.add_reading(sim_time_str, outdoor_temp, zone_states, facility_kw)
        if self.compressor.should_compress(current_sim_minutes):
            state_summary = self.compressor.compress(current_sim_minutes)
            if state_summary:
                state_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'latest_state.json')
                with open(state_file_path, 'w') as f:
                    json.dump(state_summary, f)
                action_file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs', 'pending_action.json')
                if os.path.exists(action_file_path):
                    try:
                        with open(action_file_path, 'r') as f:
                            proposed_action = json.load(f)
                        os.remove(action_file_path)
                        clamped_action, was_clamped, reason = self.guardrail.validate_and_clamp(proposed_action, state_summary)
                        if clamped_action.get('type') == 'setpoint':
                            heat = clamped_action['heating_c']
                            cool = clamped_action['cooling_c']
                            if 'heating_setpoint' in self.actuator_handles:
                                self.api.exchange.set_actuator_value(state, self.actuator_handles['heating_setpoint'], heat)
                            if 'cooling_setpoint' in self.actuator_handles:
                                self.api.exchange.set_actuator_value(state, self.actuator_handles['cooling_setpoint'], cool)
                        self.logger.log(state=state_summary, proposed_action=proposed_action, clamped_action=clamped_action, reason=reason)
                        self.last_action_time = current_sim_minutes
                    except Exception as e:
                        self._log_error('action_parse_error', str(e))
                elif self.last_action_time is not None:
                    elapsed = current_sim_minutes - self.last_action_time
                    if elapsed > self.compressor.interval_minutes * 2:
                        self._log_error('agent_timeout', 'No action received from LLM for multiple cycles. Holding previous setpoints.')

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
                self._log_error('sim_failure', f'EnergyPlus exited with code {result}')
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
    with open(idf, 'r') as f:
        if f.read().startswith('! Please copy'):
            print('ERROR: Please replace models/agent_model.idf with a real EnergyPlus IDF file.')
            sys.exit(1)
    runner = EPlusRunner(idf, epw)
    runner.run()