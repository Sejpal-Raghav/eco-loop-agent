import datetime

class StateCompressor:
    def __init__(self, interval_minutes=30):
        self.interval_minutes = interval_minutes
        self.buffer = []
        self.last_compression_time = None
        
    def add_reading(self, sim_time_str: str, outdoor_temp: float, zone_states: list, facility_kw: float):
        self.buffer.append({
            'time_str': sim_time_str,
            'outdoor_temp': outdoor_temp,
            'zones': zone_states,
            'facility_kw': facility_kw
        })
        
    def should_compress(self, current_sim_minutes: float):
        if not self.buffer:
            return False
        if self.last_compression_time is None:
            # Wait for the first interval to complete
            if current_sim_minutes >= self.interval_minutes:
                return True
            return False
            
        elapsed = current_sim_minutes - self.last_compression_time
        return elapsed >= self.interval_minutes
        
    def compress(self, current_sim_minutes: float, error_summary=None):
        if not self.buffer:
            return None
            
        # Calculate averages over the buffer
        avg_facility_kw = sum(r['facility_kw'] for r in self.buffer) / len(self.buffer)
        
        # Take the most recent zone states as current
        latest_reading = self.buffer[-1]
        
        compressed_state = {
            "sim_time": latest_reading['time_str'],
            "outdoor_temp_c": round(latest_reading['outdoor_temp'], 2),
            "zones": latest_reading['zones'],
            "facility_total_kw": round(latest_reading['facility_kw'], 2),
            "rolling_30min_avg_kw": round(avg_facility_kw, 2),
            "error_summary": error_summary or {"severe_count": 0, "warning_count": 0, "last_warnings": []}
        }
        
        self.last_compression_time = current_sim_minutes
        self.buffer.clear()
        
        return compressed_state
