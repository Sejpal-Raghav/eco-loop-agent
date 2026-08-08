import json
import os

class DecisionStore:
    def __init__(self, logs_dir=None):
        if logs_dir is None:
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        self.decisions_file = os.path.join(logs_dir, 'decisions.jsonl')
        
    def get_last_k_decisions(self, zone_name: str = None, k: int = 3):
        if not os.path.exists(self.decisions_file):
            return []
            
        decisions = []
        with open(self.decisions_file, 'r') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    if zone_name is None:
                        decisions.append(record)
                    else:
                        if zone_name in record.get('proposed_action', {}):
                            zone_record = {
                                "timestamp": record.get("state", {}).get("sim_time"),
                                "proposed": record["proposed_action"][zone_name],
                                "applied": record.get("clamped_action", {}).get(zone_name),
                                "clamp_reason": record.get("reason", {}).get(zone_name)
                            }
                            decisions.append(zone_record)
                            
        return decisions[-k:]
