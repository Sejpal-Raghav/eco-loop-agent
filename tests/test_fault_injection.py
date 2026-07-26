import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from bridge.guardrails import ActionGuardrail

def test_guardrail_faults():
    print("Running Fault Injection Tests...\n")
    guardrail = ActionGuardrail()
    
    dummy_state = {
        "zones": [{"pmv": 0.45}] # High PMV near boundary
    }
    
    print("Test 1: Malformed Action Type")
    action = {"type": "not_a_setpoint", "heating_c": 21}
    clamped, was_clamped, reason = guardrail.validate_and_clamp(action, dummy_state)
    print(f"Result: Clamped={was_clamped}, Reason={reason}")
    assert not was_clamped # Shouldn't touch non-setpoints
    print("PASS\n")
    
    print("Test 2: PMV Boundary Repulsion (Comfort Enforcement)")
    # PMV is high (0.45), agent tries to raise cooling to 27
    action = {"type": "setpoint", "zone": "Core_Zone", "heating_c": 20.0, "cooling_c": 27.0}
    clamped, was_clamped, reason = guardrail.validate_and_clamp(action, dummy_state)
    print(f"Result: Clamped={was_clamped}, Reason={reason}")
    print(f"Clamped Output: {clamped}")
    assert was_clamped
    assert clamped["cooling_c"] <= 24.0 # Should be clamped back to safe limit
    print("PASS\n")
    
    print("Test 3: Extreme LLM Hallucination")
    action = {"type": "setpoint", "zone": "Core_Zone", "heating_c": -100, "cooling_c": 500}
    clamped, was_clamped, reason = guardrail.validate_and_clamp(action, dummy_state)
    print(f"Result: Clamped={was_clamped}, Reason={reason}")
    assert was_clamped
    assert clamped["heating_c"] >= 18.0
    assert clamped["cooling_c"] <= 28.0
    print("PASS\n")
    
    print("All fault injection tests passed successfully.")

if __name__ == "__main__":
    test_guardrail_faults()
