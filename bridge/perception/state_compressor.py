import os
import json

class StateCompressor:
    def __init__(self, interval_minutes=30):
        self.interval_minutes = interval_minutes
        self.buffer = []
        self.last_compression_time = None
        self.history_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs', 'state_history.jsonl')
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)

    def add_reading(self, sim_time_str: str, outdoor_temp: float, zone_states: list, facility_kw: float):
        self.buffer.append({
            'time_str': sim_time_str,
            'outdoor_temp': outdoor_temp,
            'zones': zone_states,
            'facility_kw': facility_kw
        })

    def should_compress(self, current_sim_minutes: float):
        if not self.buffer: return False
        if self.last_compression_time is None:
            return current_sim_minutes >= self.interval_minutes
        return (current_sim_minutes - self.last_compression_time) >= self.interval_minutes

    def compress(self, current_sim_minutes: float, anomalies=None):
        if not self.buffer: return None
        avg_facility_kw = sum(r['facility_kw'] for r in self.buffer) / len(self.buffer)
        latest = self.buffer[-1]
        
        compressed = {
            'sim_time': latest['time_str'],
            'outdoor_temp_c': round(latest['outdoor_temp'], 2),
            'facility_total_kw': round(latest['facility_kw'], 2),
            'rolling_30min_avg_kw': round(avg_facility_kw, 2),
            'zones': latest['zones'],
            'anomalies': anomalies or []
        }
        
        self.last_compression_time = current_sim_minutes
        self.buffer.clear()
        
        # Write history
        with open(self.history_path, 'a') as f:
            f.write(json.dumps(compressed) + '\n')
            
        return compressed
