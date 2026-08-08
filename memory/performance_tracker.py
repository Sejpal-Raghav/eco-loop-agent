import json
import os

class PerformanceTracker:
    def __init__(self, logs_dir=None):
        if logs_dir is None:
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        self.history_file = os.path.join(logs_dir, 'state_history.jsonl')
        
    def get_performance_summary(self, hours=6):
        if not os.path.exists(self.history_file):
            return {"error": "No history available yet."}
            
        steps = hours * 2 # 30 min steps
        records = []
        with open(self.history_file, 'r') as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
                    
        records = records[-steps:]
        if not records:
            return {"error": "No history available yet."}
            
        total_kw = sum(r['facility_total_kw'] for r in records)
        avg_kw = total_kw / len(records)
        
        violations = 0
        for r in records:
            for z in r.get('zones', []):
                if abs(z['pmv']) > 0.5:
                    violations += 1
                    
        return {
            "period_hours": hours,
            "avg_facility_kw": round(avg_kw, 2),
            "pmv_violation_count": violations
        }
