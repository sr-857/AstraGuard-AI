
#!/usr/bin/env python3
def decide_action(fault):
    # returns action and description
    if fault == "power_fault":
        return "SAFE_MODE", "Reduce load, disable payload, conserve power"
    if fault == "thermal_fault":
        return "COOLING", "Adjust heaters/thermal valves or reduce load"
    if fault == "attitude_fault":
        return "STABILIZING", "Fire reaction wheels / command attitude correction"
    if fault == "sensor_fault":
        return "DIAGNOSTICS", "Run sensor reset and redundancy switch"
    if fault == "normal":
        return "NORMAL", "No action"
    return "UNKNOWN", "Investigate"
