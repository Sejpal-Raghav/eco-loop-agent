class ActionGuardrail:

    def __init__(self, min_heating_c=18.0, max_cooling_c=28.0, min_deadband=2.0, pmv_limit=0.5):
        self.min_heating = min_heating_c
        self.max_cooling = max_cooling_c
        self.min_deadband = min_deadband
        self.pmv_limit = pmv_limit

    def validate_and_clamp(self, proposed_action: dict, current_state: dict):
        if proposed_action.get('type') != 'setpoint':
            return (proposed_action, False, 'Not a setpoint action')
        heat = proposed_action.get('heating_c', 21.0)
        cool = proposed_action.get('cooling_c', 24.0)
        was_clamped = False
        reasons = []
        current_pmv = current_state['zones'][0]['pmv'] if current_state.get('zones') else 0.0
        if current_pmv >= self.pmv_limit - 0.1 and cool > 24.0:
            cool = 24.0
            was_clamped = True
            reasons.append(f'PMV Tension: Current PMV {current_pmv} is near upper limit. Cooling setpoint clamped to protect comfort.')
        if current_pmv <= -(self.pmv_limit - 0.1) and heat < 21.0:
            heat = 21.0
            was_clamped = True
            reasons.append(f'PMV Tension: Current PMV {current_pmv} is near lower limit. Heating setpoint clamped to protect comfort.')
        if heat < self.min_heating:
            heat = self.min_heating
            was_clamped = True
            reasons.append(f'Heating setpoint absolute clamp to {self.min_heating}')
        if cool > self.max_cooling:
            cool = self.max_cooling
            was_clamped = True
            reasons.append(f'Cooling setpoint absolute clamp to {self.max_cooling}')
        if cool - heat < self.min_deadband:
            mid = (heat + cool) / 2.0
            heat = mid - self.min_deadband / 2.0
            cool = mid + self.min_deadband / 2.0
            was_clamped = True
            reasons.append(f'Deadband enforced to {self.min_deadband}')
        clamped_action = {'type': 'setpoint', 'zone': proposed_action.get('zone'), 'heating_c': round(heat, 2), 'cooling_c': round(cool, 2)}
        reason_str = ' | '.join(reasons) if was_clamped else 'Valid bounds'
        return (clamped_action, was_clamped, reason_str)