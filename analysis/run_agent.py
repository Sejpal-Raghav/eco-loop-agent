import os
import sys
import time
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from bridge.ep_runner import EPlusRunner
if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(__file__))
    print('NOTE: For the closed-loop agent run, please ensure you have started the agent client in another terminal:')
    print('      python agent/client.py')
    print('Waiting 3 seconds before starting simulation...')
    time.sleep(3)
    idf = os.path.join(base_dir, 'models', 'agent_model.idf')
    epw = os.path.join(base_dir, 'models', 'weather.epw')
    print('Running Agent-Controlled Simulation...')
    runner = EPlusRunner(idf, epw)
    runner.run()