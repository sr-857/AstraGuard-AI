
#!/usr/bin/env python3
def classify(state):
    # state: dict with keys voltage, current, temperature, gyro, wheel_speed
    try:
        v = state.get("voltage", None)
        t = state.get("temperature", 0)
        g = state.get("gyro", 0)
        w = state.get("wheel_speed", 0)
    except:
        return "unknown"

    if v is None or (isinstance(v, (int,float)) and v < 7.3):
        return "power_fault"
    if isinstance(t,(int,float)) and t > 32:
        return "thermal_fault"
    if isinstance(g,(int,float)) and abs(g) > 0.05:
        return "attitude_fault"
    if w is None:
        return "sensor_fault"
    return "normal"
