#!/usr/bin/env python3
"""
State Machine Module for AstraGuard AI

This module implements the decision-making logic for autonomous fault recovery
based on classified fault types and system state.

Author: Subhajit Roy
"""

import time
from enum import Enum
from typing import Dict, Optional, Tuple


class SystemState(Enum):
    """System operational states."""

    NORMAL = "NORMAL"
    SAFE_MODE = "SAFE_MODE"
    COOLING = "COOLING"
    STABILIZING = "STABILIZING"
    DIAGNOSTICS = "DIAGNOSTICS"
    UNKNOWN = "UNKNOWN"


class FaultSeverity(Enum):
    """Fault severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def decide_action(fault_type: str) -> Tuple[str, str]:
    """
    Decide recovery action based on fault type.

    Args:
        fault_type: Classified fault type

    Returns:
        Tuple of (action, description) for recovery
    """
    action_map = {
        "power_fault": (
            SystemState.SAFE_MODE.value,
            "Reduce load, disable payload, conserve power",
        ),
        "thermal_fault": (
            SystemState.COOLING.value,
            "Adjust heaters/thermal valves or reduce load",
        ),
        "attitude_fault": (
            SystemState.STABILIZING.value,
            "Fire reaction wheels / command attitude correction",
        ),
        "sensor_fault": (
            SystemState.DIAGNOSTICS.value,
            "Run sensor reset and redundancy switch",
        ),
        "normal": (SystemState.NORMAL.value, "No action required"),
        "unknown": (SystemState.UNKNOWN.value, "Investigate unknown system state"),
    }

    return action_map.get(
        fault_type, (SystemState.UNKNOWN.value, "Investigate unknown fault")
    )


def get_recovery_commands(action: str) -> Dict[str, any]:
    """
    Get specific recovery commands for a given action.

    Args:
        action: System state action

    Returns:
        Dictionary containing recovery commands and parameters
    """
    commands = {
        SystemState.NORMAL.value: {
            "commands": [],
            "duration": 0,
            "priority": "low",
            "auto_resume": True,
        },
        SystemState.SAFE_MODE.value: {
            "commands": [
                "disable_payload",
                "reduce_power_consumption",
                "enable_backup_power",
            ],
            "duration": 300,  # 5 minutes
            "priority": "critical",
            "auto_resume": False,
        },
        SystemState.COOLING.value: {
            "commands": [
                "reduce_processing_load",
                "activate_cooling_system",
                "adjust_thermal_control",
            ],
            "duration": 180,  # 3 minutes
            "priority": "high",
            "auto_resume": True,
        },
        SystemState.STABILIZING.value: {
            "commands": [
                "enable_momentum_wheel",
                "execute_attitude_correction",
                "verify_stability",
            ],
            "duration": 120,  # 2 minutes
            "priority": "medium",
            "auto_resume": True,
        },
        SystemState.DIAGNOSTICS.value: {
            "commands": [
                "run_sensor_self_test",
                "switch_to_backup_sensor",
                "verify_sensor_readings",
            ],
            "duration": 60,  # 1 minute
            "priority": "medium",
            "auto_resume": True,
        },
        SystemState.UNKNOWN.value: {
            "commands": [
                "log_detailed_telemetry",
                "notify_ground_station",
                "await_manual_intervention",
            ],
            "duration": 0,
            "priority": "high",
            "auto_resume": False,
        },
    }

    return commands.get(action, commands[SystemState.UNKNOWN.value])


class StateMachine:
    """State machine for managing system states and transitions."""

    def __init__(self):
        self.current_state = SystemState.NORMAL
        self.state_start_time = time.time()
        self.last_fault_time = None
        self.fault_history = []
        self.recovery_in_progress = False

    def process_fault(
        self, fault_type: str, telemetry_data: Optional[Dict] = None
    ) -> Dict[str, any]:
        """
        Process a fault and determine appropriate response.

        Args:
            fault_type: Type of fault detected
            telemetry_data: Current telemetry data (optional)

        Returns:
        Dictionary with response details
        """
        current_time = time.time()

        # Log fault
        fault_record = {
            "timestamp": current_time,
            "fault_type": fault_type,
            "previous_state": self.current_state.value,
        }
        self.fault_history.append(fault_record)
        self.last_fault_time = current_time

        # Determine action
        action, description = decide_action(fault_type)
        recovery_commands = get_recovery_commands(action)

        # Update state
        new_state = SystemState(action)
        state_changed = new_state != self.current_state

        if state_changed:
            self.current_state = new_state
            self.state_start_time = current_time
            self.recovery_in_progress = True

        return {
            "fault_type": fault_type,
            "action": action,
            "description": description,
            "commands": recovery_commands["commands"],
            "duration": recovery_commands["duration"],
            "priority": recovery_commands["priority"],
            "auto_resume": recovery_commands["auto_resume"],
            "state_changed": state_changed,
            "new_state": new_state.value,
            "timestamp": current_time,
        }

    def check_recovery_complete(self) -> bool:
        """
        Check if current recovery action is complete.

        Returns:
            True if recovery is complete and system can resume normal operation
        """
        if not self.recovery_in_progress:
            return True

        current_time = time.time()
        recovery_commands = get_recovery_commands(self.current_state.value)
        duration = recovery_commands["duration"]

        if duration > 0 and (current_time - self.state_start_time) >= duration:
            return recovery_commands["auto_resume"]

        return False

    def resume_normal_operation(self) -> Dict[str, any]:
        """
        Resume normal operation after recovery.

        Returns:
            Dictionary with resume operation details
        """
        previous_state = self.current_state.value
        self.current_state = SystemState.NORMAL
        self.state_start_time = time.time()
        self.recovery_in_progress = False

        return {
            "action": "RESUME_NORMAL",
            "description": "Resuming normal operation after recovery",
            "previous_state": previous_state,
            "new_state": SystemState.NORMAL.value,
            "timestamp": time.time(),
        }

    def get_system_status(self) -> Dict[str, any]:
        """
        Get current system status.

        Returns:
            Dictionary with system status information
        """
        current_time = time.time()
        state_duration = current_time - self.state_start_time

        return {
            "current_state": self.current_state.value,
            "state_duration": state_duration,
            "recovery_in_progress": self.recovery_in_progress,
            "last_fault_time": self.last_fault_time,
            "total_faults": len(self.fault_history),
            "recent_faults": self.fault_history[-5:] if self.fault_history else [],
        }


def main() -> None:
    """
    Main function to test the state machine.
    """
    # Create state machine instance
    sm = StateMachine()

    # Test fault processing
    print("State Machine Test Results:")
    print("=" * 50)

    # Test different fault types
    fault_types = [
        "power_fault",
        "thermal_fault",
        "attitude_fault",
        "sensor_fault",
        "normal",
    ]

    for fault_type in fault_types:
        print(f"\nProcessing fault: {fault_type}")
        response = sm.process_fault(fault_type)

        print(f"  Action: {response['action']}")
        print(f"  Description: {response['description']}")
        print(f"  Commands: {response['commands']}")
        print(f"  Priority: {response['priority']}")
        print(f"  State Changed: {response['state_changed']}")

        # Get system status
        status = sm.get_system_status()
        print(f"  Current State: {status['current_state']}")
        print(f"  Recovery in Progress: {status['recovery_in_progress']}")


if __name__ == "__main__":
    main()
