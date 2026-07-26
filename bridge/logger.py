import json
import os

class DecisionLogger:

    def __init__(self, log_path='logs/decisions.jsonl'):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def log(self, state, proposed_action, clamped_action, reason):
        record = {'state': state, 'proposed': proposed_action, 'applied': clamped_action, 'reason': reason}
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(record) + '\n')