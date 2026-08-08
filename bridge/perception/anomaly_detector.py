class AnomalyDetector:
    """Flags physically implausible or suspect sensor readings."""

    def __init__(self):
        self.anomaly_count = 0

    def detect(self, raw_state: dict) -> dict:
        flags = []
        
        # 1. Facility Load Checks
        if raw_state.get("facility_kw", 0) < 0:
            flags.append("METER_ERROR: Negative facility HVAC power")
        
        # 2. Outdoor Temp Checks
        out_temp = raw_state.get("outdoor_temp", 20.0)
        if out_temp < -40 or out_temp > 55:
            flags.append(f"SENSOR_FAULT: Extreme outdoor temp {out_temp}°C")

        # 3. Zone Checks
        for zone in raw_state.get("zones", []):
            name = zone["name"]
            temp = zone["mean_air_temp_c"]
            pmv = zone["pmv"]

            if temp < 5 or temp > 45:
                flags.append(f"SENSOR_FAULT: {name} mean air temp {temp}°C is physically suspect")
            
            if pmv < -3.5 or pmv > 3.5:
                flags.append(f"SUSPECT_READING: {name} PMV {pmv} is extreme")
                
        if flags:
            self.anomaly_count += len(flags)
            
        return flags
