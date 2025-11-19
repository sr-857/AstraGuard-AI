
#!/usr/bin/env python3
"""
Telemetry Stream Generator for AstraGuard AI

This module simulates real-time CubeSat telemetry data with realistic
parameters and occasional fault injection for testing the anomaly detection system.

Author: Subhajit Roy
"""

import json
import random
import sys
import time
from typing import Dict, Tuple, Optional

import numpy as np


def generate_state() -> Dict[str, float]:
    """
    Generate normal telemetry state for a CubeSat.
    
    Returns:
        Dictionary containing telemetry parameters:
        - voltage: Bus voltage in volts (nominal 7.9V)
        - current: Current draw in amps (nominal 0.55A)
        - temperature: Temperature in Celsius (nominal 24°C)
        - gyro: Gyroscope reading in rad/s (nominal 0 rad/s)
        - wheel_speed: Reaction wheel speed in RPM (nominal 480 RPM)
    """
    return {
        "voltage": round(7.9 + np.random.normal(0, 0.03), 3),
        "current": round(0.55 + np.random.normal(0, 0.01), 3),
        "temperature": round(24 + np.random.normal(0, 0.4), 3),
        "gyro": round(np.random.normal(0, 0.015), 4),
        "wheel_speed": int(480 + np.random.normal(0, 4))
    }


def inject_fault(state: Dict[str, float]) -> Tuple[Dict[str, Optional[float]], Optional[str]]:
    """
    Inject random faults into telemetry state for testing purposes.
    
    Args:
        state: Normal telemetry state dictionary
        
    Returns:
        Tuple of (faulty_state, fault_type) where fault_type is None if no fault injected
    """
    # 10% chance to inject a fault
    if random.random() < 0.10:
        fault_type = random.choice(["power", "thermal", "attitude", "sensor"])
        faulty_state = dict(state)
        
        if fault_type == "power":
            # Voltage drop simulating power system failure
            faulty_state["voltage"] = round(faulty_state["voltage"] - random.uniform(0.8, 1.6), 3)
            return faulty_state, "power_fault"
            
        elif fault_type == "thermal":
            # Temperature spike simulating thermal runaway
            faulty_state["temperature"] = round(faulty_state["temperature"] + random.uniform(10, 18), 3)
            return faulty_state, "thermal_fault"
            
        elif fault_type == "attitude":
            # High gyro reading simulating attitude disturbance
            faulty_state["gyro"] = round(random.uniform(0.08, 0.25), 4)
            return faulty_state, "attitude_fault"
            
        elif fault_type == "sensor":
            # Null sensor reading simulating sensor failure
            faulty_state["wheel_speed"] = None
            return faulty_state, "sensor_fault"
    
    return state, None


def main() -> None:
    """
    Main function to continuously emit telemetry data as JSON lines.
    
    This function runs indefinitely, generating telemetry data at 5Hz intervals
    and printing to stdout in JSON format for consumption by other components.
    """
    try:
        while True:
            base_state = generate_state()
            telemetry_state, fault = inject_fault(base_state)
            
            output = {
                "data": telemetry_state,
                "fault": fault,
                "timestamp": time.time()
            }
            
            print(json.dumps(output), flush=True)
            time.sleep(0.2)  # 5Hz telemetry rate
            
    except KeyboardInterrupt:
        print("\nTelemetry stream stopped by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"Error in telemetry stream: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
