class ActionGuardrail:
    def __init__(self, min_heating_c=18.0, max_cooling_c=28.0, min_deadband=2.0, pmv_limit=0.5, max_rate_c=3.0):
        self.min_heating = min_heating_c
        self.max_cooling = max_cooling_c
        self.min_deadband = min_deadband
        self.pmv_limit = pmv_limit
        self.max_rate_c = max_rate_c
        self.last_applied = {} 
        
    def validate_and_clamp(self, zone_actions: dict, current_state: dict):
        clamped_actions = {}
        total_was_clamped = False
        reasons = {}

        pmv_map = {z['name']: z['pmv'] for z in current_state.get('zones', [])}
        
        for zone, action in zone_actions.items():
            heat = action.get('heating_c', 21.0)
            cool = action.get('cooling_c', 24.0)
            current_pmv = pmv_map.get(zone, 0.0)
            
            zone_clamped = False
            zone_reasons = []

            if current_pmv >= self.pmv_limit - 0.1 and cool > 24.0:
                cool = 24.0
                zone_clamped = True
                zone_reasons.append(f"PMV Tension: Current PMV {current_pmv} near upper limit")
            if current_pmv <= -(self.pmv_limit - 0.1) and heat < 21.0:
                heat = 21.0
                zone_clamped = True
                zone_reasons.append(f"PMV Tension: Current PMV {current_pmv} near lower limit")

            if heat < self.min_heating:
                heat = self.min_heating
                zone_clamped = True
                zone_reasons.append(f"Heating < min {self.min_heating}")
            if cool > self.max_cooling:
                cool = self.max_cooling
                zone_clamped = True
                zone_reasons.append(f"Cooling > max {self.max_cooling}")

            if zone in self.last_applied:
                last_heat, last_cool = self.last_applied[zone]
                if abs(heat - last_heat) > self.max_rate_c:
                    heat = last_heat + self.max_rate_c * (1 if heat > last_heat else -1)
                    zone_clamped = True
                    zone_reasons.append(f"Heating rate limit {self.max_rate_c}C")
                if abs(cool - last_cool) > self.max_rate_c:
                    cool = last_cool + self.max_rate_c * (1 if cool > last_cool else -1)
                    zone_clamped = True
                    zone_reasons.append(f"Cooling rate limit {self.max_rate_c}C")

            if cool - heat < self.min_deadband:
                mid = (heat + cool) / 2.0
                heat = mid - self.min_deadband / 2.0
                cool = mid + self.min_deadband / 2.0
                zone_clamped = True
                zone_reasons.append(f"Deadband enforced to {self.min_deadband}")

            heat = round(heat, 2)
            cool = round(cool, 2)
            clamped_actions[zone] = {"heating_c": heat, "cooling_c": cool}
            self.last_applied[zone] = (heat, cool)

            if zone_clamped:
                total_was_clamped = True
                reasons[zone] = " | ".join(zone_reasons)

        return clamped_actions, total_was_clamped, reasons
