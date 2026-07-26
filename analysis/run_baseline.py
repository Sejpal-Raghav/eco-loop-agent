import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from bridge.ep_runner import EPlusRunner
if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(__file__))
    idf = os.path.join(base_dir, 'models', 'baseline.idf')
    epw = os.path.join(base_dir, 'models', 'weather.epw')
    print('Running Baseline Simulation (no agent control)...')
    runner = EPlusRunner(idf, epw)
    runner.run()