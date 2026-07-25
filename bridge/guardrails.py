class ActionGuardrail:
    def __init__(self, min_heating_c=18.0, max_cooling_c=28.0, min_deadband=2.0):
        self.min_heating = min_heating_c
        self.max_cooling = max_cooling_c
        self.min_deadband = min_deadband
        
    def validate_and_clamp(self, proposed_action: dict, current_state: dict):
        """
        Takes a proposed action and clamps it within acceptable safety and comfort bounds.
        Returns (clamped_action, was_clamped, reason)
        """
        if proposed_action.get("type") != "setpoint":
            # For now, only guarding setpoints
            return proposed_action, False, "Not a setpoint action"
            
        heat = proposed_action.get("heating_c", 21.0)
        cool = proposed_action.get("cooling_c", 24.0)
        
        was_clamped = False
        reasons = []
        
        # 1. Absolute bounds check
        if heat < self.min_heating:
            heat = self.min_heating
            was_clamped = True
            reasons.append(f"Heating setpoint clamped to {self.min_heating}")
            
        if cool > self.max_cooling:
            cool = self.max_cooling
            was_clamped = True
            reasons.append(f"Cooling setpoint clamped to {self.max_cooling}")
            
        # 2. Deadband check
        if cool - heat < self.min_deadband:
            # If deadband is violated, we widen it equally around the midpoint
            mid = (heat + cool) / 2.0
            heat = mid - (self.min_deadband / 2.0)
            cool = mid + (self.min_deadband / 2.0)
            was_clamped = True
            reasons.append(f"Deadband enforced to {self.min_deadband}")
            
        clamped_action = {
            "type": "setpoint",
            "zone": proposed_action.get("zone"),
            "heating_c": round(heat, 2),
            "cooling_c": round(cool, 2)
        }
        
        reason_str = " | ".join(reasons) if was_clamped else "Valid bounds"
        return clamped_action, was_clamped, reason_str
