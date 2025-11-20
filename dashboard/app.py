#!/usr/bin/env python3
# AstraGuard AI Dashboard
"""
Real-time monitoring dashboard for CubeSat telemetry, anomaly detection,
and autonomous fault recovery system.

Author: Subhajit Roy
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Dict

import altair as alt
import pandas as pd
import streamlit as st

# Import project modules
from anomaly.anomaly_detector import detect_anomaly, load_model
from classifier.fault_classifier import (
    classify,
    get_fault_description,
    get_fault_severity,
)
from logs.timeline import log_event, read_recent
from state_machine.state_engine import StateMachine


def initialize_session_state() -> None:
    """Initialize Streamlit session state variables."""
    if "history" not in st.session_state:
        st.session_state.history = {
            "timestamp": [],
            "voltage": [],
            "current": [],
            "temperature": [],
            "gyro": [],
            "wheel_speed": [],
            "anomaly_score": [],
            "fault_type": [],
            "system_state": [],
        }

    if "state_machine" not in st.session_state:
        st.session_state.state_machine = StateMachine()

    if "telemetry_process" not in st.session_state:
        st.session_state.telemetry_process = None

    if "model_loaded" not in st.session_state:
        st.session_state.model_loaded = False

    if "total_samples" not in st.session_state:
        st.session_state.total_samples = 0

    if "anomaly_count" not in st.session_state:
        st.session_state.anomaly_count = 0


def start_telemetry_stream() -> subprocess.Popen:
    """Start the telemetry stream as a subprocess."""
    telemetry_py = Path(__file__).parent.parent / "telemetry" / "telemetry_stream.py"

    try:
        proc = subprocess.Popen(
            ["python3", str(telemetry_py)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        return proc
    except Exception as e:
        st.error(f"Failed to start telemetry stream: {e}")
        return None


def load_anomaly_model() -> bool:
    """Load the anomaly detection model."""
    try:
        load_model()
        return True
    except Exception as e:
        st.warning(f"Model loading/training issue: {e}")
        return False


def update_telemetry_history(
    telemetry_data: Dict, anomaly_score: float, fault_type: str, system_state: str
) -> None:
    """Update telemetry history with new data point."""
    max_history = 100  # Keep last 100 samples

    # Add new data
    st.session_state.history["timestamp"].append(
        telemetry_data.get("timestamp", time.time())
    )
    st.session_state.history["voltage"].append(telemetry_data.get("voltage", 0))
    st.session_state.history["current"].append(telemetry_data.get("current", 0))
    st.session_state.history["temperature"].append(telemetry_data.get("temperature", 0))
    st.session_state.history["gyro"].append(telemetry_data.get("gyro", 0))
    st.session_state.history["wheel_speed"].append(telemetry_data.get("wheel_speed", 0))
    st.session_state.history["anomaly_score"].append(anomaly_score)
    st.session_state.history["fault_type"].append(fault_type)
    st.session_state.history["system_state"].append(system_state)

    # Trim history if too long
    if len(st.session_state.history["timestamp"]) > max_history:
        for key in st.session_state.history:
            st.session_state.history[key] = st.session_state.history[key][-max_history:]


def create_telemetry_charts() -> alt.Chart:
    """Create telemetry visualization charts."""
    if not st.session_state.history["timestamp"]:
        return alt.Chart().mark_text(text="No data available")

    df = pd.DataFrame(st.session_state.history)

    # Create individual charts
    voltage_chart = (
        alt.Chart(df)
        .mark_line(color="blue", strokeWidth=2)
        .encode(
            x=alt.X("index:Q", title="Time Steps"),
            y=alt.Y(
                "voltage:Q", title="Voltage (V)", scale=alt.Scale(domain=[7.0, 8.5])
            ),
        )
        .properties(height=120)
    )

    temperature_chart = (
        alt.Chart(df)
        .mark_line(color="red", strokeWidth=2)
        .encode(
            x=alt.X("index:Q", title="Time Steps"),
            y=alt.Y(
                "temperature:Q",
                title="Temperature (°C)",
                scale=alt.Scale(domain=[15, 45]),
            ),
        )
        .properties(height=120)
    )

    gyro_chart = (
        alt.Chart(df)
        .mark_line(color="green", strokeWidth=2)
        .encode(
            x=alt.X("index:Q", title="Time Steps"),
            y=alt.Y(
                "gyro:Q", title="Gyro (rad/s)", scale=alt.Scale(domain=[-0.1, 0.1])
            ),
        )
        .properties(height=120)
    )

    anomaly_chart = (
        alt.Chart(df)
        .mark_line(color="orange", strokeWidth=2)
        .encode(
            x=alt.X("index:Q", title="Time Steps"),
            y=alt.Y("anomaly_score:Q", title="Anomaly Score"),
        )
        .properties(height=120)
    )

    # Combine charts
    combined_chart = alt.vconcat(
        voltage_chart, temperature_chart, gyro_chart, anomaly_chart
    ).resolve_scale(y="independent")

    return combined_chart


def create_system_status_panel() -> None:
    """Create system status panel."""
    if not st.session_state.history["system_state"]:
        st.info("System initializing...")
        return

    current_state = st.session_state.history["system_state"][-1]
    current_fault = st.session_state.history["fault_type"][-1]
    current_score = st.session_state.history["anomaly_score"][-1]

    # System state
    state_color = {
        "NORMAL": "green",
        "SAFE_MODE": "red",
        "COOLING": "orange",
        "STABILIZING": "blue",
        "DIAGNOSTICS": "yellow",
        "UNKNOWN": "gray",
    }.get(current_state, "gray")

    st.markdown(f"### System State")
    st.markdown(
        f"<div style='background-color: {state_color}; color: white; padding: 10px; border-radius: 5px; text-align: center; font-weight: bold;'>{current_state}</div>",
        unsafe_allow_html=True,
    )

    # Fault status
    st.markdown(f"### Fault Status")
    if current_fault == "normal":
        st.success("✅ No active faults")
    else:
        severity = get_fault_severity(current_fault)
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
        }.get(severity, "⚪")

        st.error(f"{severity_emoji} {current_fault.upper()}")
        st.caption(get_fault_description(current_fault))

    # Statistics
    st.markdown(f"### Statistics")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Samples", st.session_state.total_samples)
        st.metric("Anomaly Count", st.session_state.anomaly_count)
    with col2:
        anomaly_rate = (
            st.session_state.anomaly_count / max(st.session_state.total_samples, 1)
        ) * 100
        st.metric("Anomaly Rate", f"{anomaly_rate:.1f}%")
        st.metric("Current Score", f"{current_score:.3f}")


def create_telemetry_display(telemetry_data: Dict) -> None:
    """Create real-time telemetry display."""
    st.markdown("### Current Telemetry")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Voltage", f"{telemetry_data.get('voltage', 0):.3f} V", "⚡")
        st.metric("Current", f"{telemetry_data.get('current', 0):.3f} A", "🔋")

    with col2:
        st.metric("Temperature", f"{telemetry_data.get('temperature', 0):.1f} °C", "🌡️")
        st.metric("Gyro", f"{telemetry_data.get('gyro', 0):.4f} rad/s", "🔄")

    with col3:
        wheel_speed = telemetry_data.get("wheel_speed", 0)
        if wheel_speed is None:
            st.metric("Wheel Speed", "N/A", "⚠️")
        else:
            st.metric("Wheel Speed", f"{wheel_speed} RPM", "⚙️")

    # Raw data (collapsible)
    with st.expander("Raw Telemetry Data"):
        st.json(telemetry_data)


def create_events_panel() -> None:
    """Create recent events panel."""
    st.markdown("### Recent Events")

    recent_events = read_recent(10)
    if not recent_events:
        st.info("No recent events")
        return

    for event in recent_events:
        parts = event.split(" | ")
        if len(parts) >= 3:
            timestamp, event_type, details = parts[0], parts[1], " | ".join(parts[2:])

            # Color code by event type
            if "ANOMALY" in event_type:
                st.markdown(f"🔴 **{timestamp}** - {event_type}: {details}")
            elif "FAULT" in event_type:
                st.markdown(f"🟠 **{timestamp}** - {event_type}: {details}")
            else:
                st.markdown(f"🟢 **{timestamp}** - {event_type}: {details}")


def main() -> None:
    """Main dashboard application."""
    # Configure page
    st.set_page_config(
        page_title="AstraGuard AI Dashboard",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Header
    st.title("🛰️ AstraGuard AI Dashboard")
    st.markdown("*Autonomous Fault Detection & Recovery System for CubeSats*")

    # Initialize session state
    initialize_session_state()

    # Sidebar controls
    with st.sidebar:
        st.header("🎛️ Controls")

        if st.button("🚀 Start Telemetry", type="primary"):
            if st.session_state.telemetry_process is None:
                st.session_state.telemetry_process = start_telemetry_stream()
                if st.session_state.telemetry_process:
                    st.success("Telemetry stream started")
                else:
                    st.error("Failed to start telemetry stream")
            else:
                st.warning("Telemetry already running")

        if st.button("⏹️ Stop Telemetry"):
            if st.session_state.telemetry_process:
                st.session_state.telemetry_process.terminate()
                st.session_state.telemetry_process = None
                st.success("Telemetry stream stopped")
            else:
                st.warning("No telemetry stream running")

        if st.button("🔄 Clear History"):
            for key in st.session_state.history:
                st.session_state.history[key] = []
            st.session_state.total_samples = 0
            st.session_state.anomaly_count = 0
            st.success("History cleared")

        st.markdown("---")
        st.markdown("### ℹ️ System Info")
        st.info(
            f"Model Status: {'✅ Loaded' if st.session_state.model_loaded else '❌ Not Loaded'}"
        )
        st.info(
            f"Telemetry: {'🟢 Running' if st.session_state.telemetry_process else '🔴 Stopped'}"
        )

    # Load model if not loaded
    if not st.session_state.model_loaded:
        st.session_state.model_loaded = load_anomaly_model()

    # Main layout
    if st.session_state.telemetry_process:
        # Read telemetry data
        try:
            line = st.session_state.telemetry_process.stdout.readline()
            if line:
                data = json.loads(line.strip())
                telemetry_state = data.get("data", {})
                injected_fault = data.get("fault")

                # Anomaly detection
                is_anomalous, anomaly_score = detect_anomaly(telemetry_state)

                # Fault classification
                fault_type = classify(telemetry_state)

                # State machine decision
                if is_anomalous or injected_fault:
                    response = st.session_state.state_machine.process_fault(
                        fault_type, telemetry_state
                    )
                    system_state = response["new_state"]

                    # Log event
                    log_event(
                        "ANOMALY_DETECTED" if is_anomalous else "FAULT_INJECTED",
                        f"{fault_type} score={anomaly_score:.3f} action={system_state}",
                    )
                else:
                    # Check if recovery should complete
                    if st.session_state.state_machine.check_recovery_complete():
                        response = (
                            st.session_state.state_machine.resume_normal_operation()
                        )
                        system_state = response["new_state"]
                        log_event("RECOVERY_COMPLETE", f"Resumed {system_state}")
                    else:
                        system_state = (
                            st.session_state.state_machine.current_state.value
                        )

                # Update counters
                st.session_state.total_samples += 1
                if is_anomalous:
                    st.session_state.anomaly_count += 1

                # Update history
                update_telemetry_history(
                    telemetry_state, anomaly_score, fault_type, system_state
                )

                # Create dashboard layout
                col1, col2 = st.columns([3, 1])

                with col1:
                    # Telemetry display
                    create_telemetry_display(telemetry_state)

                    # Charts
                    st.markdown("### 📊 Telemetry Trends")
                    charts = create_telemetry_charts()
                    st.altair_chart(charts, use_container_width=True)

                with col2:
                    # System status
                    create_system_status_panel()

                    # Recent events
                    create_events_panel()

        except Exception as e:
            st.error(f"Error processing telemetry: {e}")
            # Check if process ended
            if (
                st.session_state.telemetry_process
                and st.session_state.telemetry_process.poll() is not None
            ):
                st.session_state.telemetry_process = None
                st.warning("Telemetry stream ended unexpectedly")

    else:
        st.info("👆 Start telemetry stream to begin monitoring")

        # Show system status when not running
        st.markdown("### 📊 System Status")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("System State", "IDLE")
            st.metric("Telemetry Rate", "0 Hz")
        with col2:
            st.metric("Anomaly Rate", "0%")
            st.metric("Last Update", "N/A")


if __name__ == "__main__":
    main()
