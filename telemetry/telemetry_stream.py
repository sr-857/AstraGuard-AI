
#!/usr/bin/env python3
import numpy as np
import time
import json
import random
import sys

def generate_state():
    return {
        "voltage": round(7.9 + np.random.normal(0,0.03), 3),
        "current": round(0.55 + np.random.normal(0,0.01), 3),
        "temperature": round(24 + np.random.normal(0,0.4), 3),
        "gyro": round(np.random.normal(0,0.015), 4),
        "wheel_speed": int(480 + np.random.normal(0,4))
    }

def inject_fault(state):
    # 10% chance to inject a fault
    if random.random() < 0.10:
        choice = random.choice(["power","thermal","attitude","sensor"])
        s = dict(state)
        if choice == "power":
            s["voltage"] = round(s["voltage"] - random.uniform(0.8,1.6), 3)
            return s, "power_fault"
        if choice == "thermal":
            s["temperature"] = round(s["temperature"] + random.uniform(10,18), 3)
            return s, "thermal_fault"
        if choice == "attitude":
            s["gyro"] = round(random.uniform(0.08,0.25), 4)
            return s, "attitude_fault"
        if choice == "sensor":
            s["wheel_speed"] = None
            return s, "sensor_fault"
    return state, None

if __name__ == "__main__":
    # emit telemetry endlessly to stdout as JSON lines
    try:
        while True:
            base = generate_state()
            state, fault = inject_fault(base)
            print(json.dumps({"data": state, "fault": fault}), flush=True)
            time.sleep(0.2)
    except KeyboardInterrupt:
        sys.exit(0)
