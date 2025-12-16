#!/usr/bin/env python3
# Fault Classification Module for AstraGuard AI
"""
This module implements rule-based fault classification to identify the type
of fault based on telemetry parameters.

Author: Subhajit Roy
"""

from typing import Dict, Optional, List, TypedDict, Any

# Fault classification thresholds
THRESHOLDS = {
    "voltage_low": 7.3,  # Below this indicates power fault
    "voltage_critical": 6.8,  # Critical power failure
    "temperature_high": 32,  # Above this indicates thermal fault
    "temperature_critical": 40,  # Critical thermal condition
    "gyro_high": 0.05,  # Above this indicates attitude fault
    "gyro_critical": 0.1,  # Critical attitude disturbance
    "wheel_speed_nominal": (470, 490),  # Normal wheel speed range
}


class ValidationResult(TypedDict):
    valid: bool
    missing_fields: List[str]
    invalid_values: List[str]
    warnings: List[str]
    can_classify: bool


def classify(telemetry_state: Dict[str, Optional[float]]) -> str:
    """Classify the type of fault based on telemetry data.

    Args:
        telemetry_state: Dictionary containing telemetry parameters

    Returns:
        Fault classification string:
        - "power_fault": Voltage below threshold
        - "thermal_fault": Temperature above threshold
        - "attitude_fault": Gyro reading above threshold
        - "sensor_fault": Missing or invalid sensor data
        - "normal": No fault detected
        - "unknown": Unable to classify
    """
    try:
        # Extract telemetry values with safe defaults
        voltage = telemetry_state.get("voltage")
        temperature = telemetry_state.get("temperature")
        gyro = telemetry_state.get("gyro")
        wheel_speed = telemetry_state.get("wheel_speed")

        # Check for sensor faults (missing or None values)
        if wheel_speed is None:
            return "sensor_fault"
        if voltage is None:
            return "sensor_fault"
        if temperature is None:
            return "sensor_fault"
        if gyro is None:
            return "sensor_fault"

        # Validate data types
        if not all(
            isinstance(x, (int, float))
            for x in [voltage, temperature, gyro, wheel_speed]
        ):
            return "sensor_fault"

        # Cast to float for type safety (we know they are numbers now)
        v_val = float(voltage)  # type: ignore
        t_val = float(temperature)  # type: ignore
        g_val = float(gyro)  # type: ignore
        w_val = float(wheel_speed)  # type: ignore

        # Check for power fault (voltage)
        if v_val < THRESHOLDS["voltage_critical"]:  # type: ignore
            return "power_fault_critical"
        if v_val < THRESHOLDS["voltage_low"]:  # type: ignore
            return "power_fault"

        # Check for thermal fault (temperature)
        if t_val > THRESHOLDS["temperature_critical"]:  # type: ignore
            return "thermal_fault_critical"
        if t_val > THRESHOLDS["temperature_high"]:  # type: ignore
            return "thermal_fault"

        # Check for attitude fault (gyro)
        if abs(g_val) > THRESHOLDS["gyro_critical"]:  # type: ignore
            return "attitude_fault_critical"
        if abs(g_val) > THRESHOLDS["gyro_high"]:  # type: ignore
            return "attitude_fault"

        # Check for wheel speed anomaly
        wheel_range = THRESHOLDS["wheel_speed_nominal"]
        if isinstance(wheel_range, tuple):
            wheel_min, wheel_max = wheel_range
            if not (wheel_min <= w_val <= wheel_max):
                return "wheel_anomaly"

        # Check for sensor fault (None values or invalid data)
        if any(v is None for v in [voltage, temperature, gyro, wheel_speed]):
            return "sensor_fault"

        return "normal"

    except Exception as e:
        print(f"Error in fault classification: {e}")
        return "unknown"


def get_fault_severity(fault_type: str) -> str:
    """Get the severity level for a given fault type.

    Args:
        fault_type: Type of fault

    Returns:
        Severity level: "critical", "high", "medium", or "low"
    """
    severity_map = {
        "power_fault": "critical",
        "power_fault_critical": "critical",
        "thermal_fault": "high",
        "thermal_fault_critical": "critical",
        "attitude_fault": "medium",
        "attitude_fault_critical": "high",
        "sensor_fault": "medium",
        "wheel_anomaly": "high",
        "normal": "low",
        "unknown": "medium",
    }

    return severity_map.get(fault_type, "medium")


def get_fault_description(fault_type: str) -> str:
    """Get human-readable description for a fault type.

    Args:
        fault_type: Type of fault

    Returns:
        Human-readable fault description
    """
    descriptions = {
        "power_fault": "Power system anomaly detected - voltage below operational threshold",
        "power_fault_critical": "CRITICAL POWER FAILURE - Voltage critically low",
        "thermal_fault": "Thermal anomaly detected - temperature above safe operating limits",
        "thermal_fault_critical": "CRITICAL THERMAL RUNAWAY - Temperature critically high",
        "attitude_fault": "Attitude control anomaly detected - excessive angular rates",
        "attitude_fault_critical": "CRITICAL ATTITUDE LOSS - Spacecraft tumbling",
        "sensor_fault": "Sensor malfunction detected - invalid or missing telemetry data",
        "wheel_anomaly": "Reaction wheel speed anomaly detected",
        "normal": "All systems operating within normal parameters",
        "unknown": "Unknown system state - requires investigation",
    }

    return descriptions.get(fault_type, "Unknown fault type")


def validate_telemetry_for_classification(
    telemetry_state: Dict[str, Optional[float]],
) -> ValidationResult:
    """Validate telemetry data for fault classification.

    Args:
        telemetry_state: Dictionary containing telemetry parameters

    Returns:
        Dictionary with validation results and recommendations
    """
    validation_result: ValidationResult = {
        "valid": True,
        "missing_fields": [],
        "invalid_values": [],
        "warnings": [],
        "can_classify": True,
    }

    required_fields = ["voltage", "current", "temperature", "gyro", "wheel_speed"]

    # Check for missing fields
    for field in required_fields:
        if field not in telemetry_state:
            validation_result["missing_fields"].append(field)
            validation_result["valid"] = False
        elif telemetry_state[field] is None:
            validation_result["missing_fields"].append(f"{field} (None)")
            validation_result["valid"] = False

    # Check for invalid values
    for field, value in telemetry_state.items():
        if value is not None and not isinstance(value, (int, float)):
            validation_result["invalid_values"].append(f"{field}: {type(value)}")
            validation_result["valid"] = False
        elif isinstance(value, (int, float)):
            # Check for unreasonable values
            if field == "voltage" and (value < 0 or value > 15):
                validation_result["warnings"].append(f"{field}: {value} (unreasonable)")
            elif field == "temperature" and (value < -50 or value > 100):
                validation_result["warnings"].append(f"{field}: {value} (unreasonable)")
            elif field == "wheel_speed" and (value < 0 or value > 10000):
                validation_result["warnings"].append(f"{field}: {value} (unreasonable)")

    # Determine if classification is possible
    validation_result["can_classify"] = (
        validation_result["valid"] and len(validation_result["invalid_values"]) == 0
    )
    return validation_result


def main() -> None:
    """Main function to test fault classification."""
    # Test cases
    test_cases = [
        {
            "name": "Normal operation",
            "data": {
                "voltage": 7.9,
                "current": 0.55,
                "temperature": 24,
                "gyro": 0.01,
                "wheel_speed": 480,
            },
        },
        {
            "name": "Power fault",
            "data": {
                "voltage": 6.5,
                "current": 0.55,
                "temperature": 24,
                "gyro": 0.01,
                "wheel_speed": 480,
            },
        },
        {
            "name": "Thermal fault",
            "data": {
                "voltage": 7.9,
                "current": 0.55,
                "temperature": 35,
                "gyro": 0.01,
                "wheel_speed": 480,
            },
        },
        {
            "name": "Attitude fault",
            "data": {
                "voltage": 7.9,
                "current": 0.55,
                "temperature": 24,
                "gyro": 0.08,
                "wheel_speed": 480,
            },
        },
        {
            "name": "Sensor fault",
            "data": {
                "voltage": 7.9,
                "current": 0.55,
                "temperature": 24,
                "gyro": 0.01,
                "wheel_speed": None,
            },
        },
    ]

    print("Fault Classification Test Results:")
    print("=" * 50)

    for test in test_cases:
        print(f"\n{test['name']}:")
        print(f"Data: {test['data']}")

        # Validate telemetry
        validation = validate_telemetry_for_classification(test["data"])  # type: ignore

        if validation["can_classify"]:
            # Classify fault
            fault_type = classify(test["data"])  # type: ignore
            severity = get_fault_severity(fault_type)
            description = get_fault_description(fault_type)

            print(f"Fault Type: {fault_type}")
            print(f"Severity: {severity}")
            print(f"Description: {description}")


if __name__ == "__main__":
    main()
