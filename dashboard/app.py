import streamlit as st
import pandas as pd
import numpy as np
import time
import sys
import os
from datetime import datetime

# Add parent directory to path to import modules
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from state_machine.state_engine import StateMachine, MissionPhase
from state_machine.mission_policy import PolicyManager
from state_machine.mission_phase_policy_engine import MissionPhasePolicyEngine
from config.mission_phase_policy_loader import MissionPhasePolicyLoader
from anomaly_agent.phase_aware_handler import PhaseAwareAnomalyHandler

# Initialize state machine and policy systems
state_machine = StateMachine()
policy_loader = MissionPhasePolicyLoader()
policy_engine = MissionPhasePolicyEngine(policy_loader.get_policy())
phase_aware_handler = PhaseAwareAnomalyHandler(state_machine, policy_loader)
policy_manager = PolicyManager()  # Keep for backward compatibility

# Initialize session state
if "telemetry_active" not in st.session_state:
    st.session_state.telemetry_active = False
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["voltage","temp","gyro","wheel"])
if "logs" not in st.session_state:
    st.session_state.logs = []
if "decision_logs" not in st.session_state:
    st.session_state.decision_logs = []
if "mission_phase" not in st.session_state:
    st.session_state.mission_phase = MissionPhase.NOMINAL_OPS.value
if "simulation_mode" not in st.session_state:
    st.session_state.simulation_mode = os.getenv("ASTRAGUARD_SIMULATION_MODE", "").lower() == "true"

# Sidebar controls
st.sidebar.title("Flight Controls")
start_btn = st.sidebar.button("Start Telemetry")
stop_btn = st.sidebar.button("Stop Telemetry")

st.sidebar.markdown("---")

# Mission Phase Display and Control
st.sidebar.subheader("🚀 Mission Phase")

# Display current phase with description
current_phase = MissionPhase(st.session_state.mission_phase)
phase_description = state_machine.get_phase_description(current_phase)

st.sidebar.write(f"**Current:** {current_phase.value}")
st.sidebar.info(phase_description)

# Phase transition controls - only in simulation mode
if st.session_state.simulation_mode:
    st.sidebar.markdown("---")
    st.sidebar.warning("⚠️ **SIMULATION MODE ACTIVE** - Phase control enabled for testing only")
    
    phase_options = [p.value for p in MissionPhase]
    new_phase_value = st.sidebar.selectbox(
        "Simulate Phase Transition (TESTING ONLY)", 
        phase_options,
        index=phase_options.index(st.session_state.mission_phase)
    )
    
    if new_phase_value != st.session_state.mission_phase:
        try:
            new_phase = MissionPhase(new_phase_value)
            # Try normal transition first
            if state_machine.is_phase_transition_valid(new_phase):
                state_machine.set_phase(new_phase)
                st.session_state.mission_phase = new_phase.value
                st.sidebar.success(f"✓ Transitioned to {new_phase.value}")
            else:
                # Offer forced transition option
                if st.sidebar.button(f"Force transition to {new_phase_value}?"):
                    state_machine.force_safe_mode() if new_phase == MissionPhase.SAFE_MODE else state_machine.set_phase(new_phase)
                    st.session_state.mission_phase = new_phase.value
                    st.sidebar.success(f"✓ Forced transition to {new_phase.value}")
        except Exception as e:
            st.sidebar.error(f"Transition error: {e}")
else:
    st.sidebar.caption("💡 Tip: Set `ASTRAGUARD_SIMULATION_MODE=true` env var to enable phase control")

# Phase constraints display
constraints = phase_aware_handler.get_phase_constraints(current_phase)
with st.sidebar.expander("🔒 Phase Constraints"):
    st.write("**Allowed Actions:**")
    st.write(", ".join(constraints['allowed_actions']) if constraints['allowed_actions'] else "None")
    st.write("\n**Forbidden Actions:**")
    st.write(", ".join(constraints['forbidden_actions']) if constraints['forbidden_actions'] else "None")
    st.write(f"\n**Threshold Multiplier:** {constraints['threshold_multiplier']}x")

if start_btn:
    st.session_state.telemetry_active = True
if stop_btn:
    st.session_state.telemetry_active = False

# Fake anomaly detection function
def detect_anomaly(row):
    # Adjust thresholds based on phase
    multiplier = policy_manager.get_threshold_multiplier(st.session_state.mission_phase)
    return row["voltage"] > (4.2 * multiplier) or row["temp"] > (75 * multiplier)

def classify_anomaly_type(row):
    """Classify the type of fault based on telemetry."""
    if row.get("voltage", 8.0) < 7.0:
        return "power_fault"
    elif row.get("temp", 25.0) > 40.0:
        return "thermal_fault"
    elif abs(row.get("gyro", 0.0)) > 0.1:
        return "attitude_fault"
    else:
        return "unknown_fault"

def calculate_severity_score(row):
    """Calculate a normalized severity score from 0-1."""
    score = 0.0
    if row.get("voltage", 8.0) < 7.0:
        score += 0.4
    if row.get("temp", 25.0) > 40.0:
        score += 0.3
    if abs(row.get("gyro", 0.0)) > 0.1:
        score += 0.3
    # Normalize to 0-1
    return min(1.0, score / 0.7 * np.random.uniform(0.8, 1.0))

# Memory search simulation
def memory_search(row):
    if len(st.session_state.df) < 3:
        return []
    past = st.session_state.df.tail(3)
    results = []
    for _, r in past.iterrows():
        sim = 100 - abs(r["voltage"] - row["voltage"])*10
        results.append({
            "summary": f"Voltage {r['voltage']:.2f}V, Temp {r['temp']:.1f}C",
            "similarity": max(0, min(100, sim)),
            "timestamp": time.strftime("%H:%M:%S")
        })
    return results

# Header
col_head1, col_head2, col_head3 = st.columns([2, 1, 1])
with col_head1:
    st.title("AstraGuard – Mission Control")
    st.caption("Real-time telemetry and anomaly detection with mission-phase awareness")
with col_head2:
    st.metric("Phase", st.session_state.mission_phase, "🚀")
with col_head3:
    status_indicator = "🟢 ACTIVE" if st.session_state.telemetry_active else "🔴 OFFLINE"
    st.write(f"**Telemetry**\n{status_indicator}")

# Display phase history if expanded
with st.expander("📋 Phase History"):
    history = state_machine.get_phase_history()
    history_df = pd.DataFrame([
        {"Phase": p[0], "Time": p[1]} for p in history[-10:]
    ])
    st.dataframe(history_df, use_container_width=True)

status = "Telemetry Active" if st.session_state.telemetry_active else "Telemetry Offline"
st.write(f"**System Status:** {status}")

# Main loop
if st.session_state.telemetry_active:
    new_row = {
        "voltage": np.random.uniform(3.5, 5.0),
        "temp": np.random.uniform(20, 90),
        "gyro": np.random.uniform(-5, 5),
        "wheel": np.random.uniform(2000, 8000)
    }
    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)

    anomaly = detect_anomaly(new_row)
    mem = memory_search(new_row)

    # Log event
    log = f"[{time.strftime('%H:%M:%S')}] {'ANOMALY' if anomaly else 'OK'} | {new_row['voltage']:.2f}V | {new_row['temp']:.1f}C"
    st.session_state.logs.append(log)

    # Layout
    col1, col2 = st.columns([2,1])

    with col1:
        st.subheader("Live Telemetry Stream")
        st.line_chart(st.session_state.df[["voltage","temp","gyro","wheel"]])

    with col2:
        st.subheader("Anomaly Radar")
        if anomaly:
            st.error("Anomaly Detected!")
            st.write("**Confidence:** 87.3%")
            st.write("**Severity:** Medium")
            st.write("**Recurrence:** 3×")
        else:
            st.success("All signals normal")

    # Memory Matches
    st.subheader("Memory Matches")
    if mem:
        for m in mem:
            st.write(f"- {m['summary']} (Similarity: {m['similarity']:.1f}%)")
    else:
        st.write("Memory warming up...")

# Main loop
if st.session_state.telemetry_active:
    new_row = {
        "voltage": np.random.uniform(3.5, 5.0),
        "temp": np.random.uniform(20, 90),
        "gyro": np.random.uniform(-5, 5),
        "wheel": np.random.uniform(2000, 8000)
    }
    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_row])], ignore_index=True)

    anomaly = detect_anomaly(new_row)
    mem = memory_search(new_row)

    # Log event
    timestamp = time.strftime('%H:%M:%S')
    log = f"[{timestamp}] {'ANOMALY' if anomaly else 'OK'} | {new_row['voltage']:.2f}V | {new_row['temp']:.1f}C | Phase: {st.session_state.mission_phase}"
    st.session_state.logs.append(log)

    # Process anomaly through phase-aware handler if detected
    policy_decision = None
    if anomaly:
        anomaly_type = classify_anomaly_type(new_row)
        severity_score = calculate_severity_score(new_row)
        
        # Get decision from phase-aware handler
        policy_decision = phase_aware_handler.handle_anomaly(
            anomaly_type=anomaly_type,
            severity_score=severity_score,
            confidence=0.87,
            anomaly_metadata={"subsystem": "POWER_THERMAL"}
        )
        
        st.session_state.decision_logs.append(policy_decision)
        
        # Update mission phase if escalation occurred
        current_phase = state_machine.get_current_phase()
        st.session_state.mission_phase = current_phase.value

    # Layout
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Live Telemetry Stream")
        st.line_chart(st.session_state.df[["voltage","temp","gyro","wheel"]])

    with col2:
        st.subheader("Anomaly Radar")
        if anomaly and policy_decision:
            if policy_decision['should_escalate_to_safe_mode']:
                st.error("🚨 CRITICAL - Escalating to SAFE_MODE!")
                st.metric("Severity", policy_decision['severity_score'], delta="ESCALATE")
            else:
                st.warning("⚠️ Anomaly Detected")
                st.metric("Severity", policy_decision['severity_score'])
            
            st.write(f"**Type:** {policy_decision['anomaly_type']}")
            st.write(f"**Confidence:** {policy_decision['detection_confidence']:.1%}")
            st.write(f"**Recurrence:** {policy_decision['recurrence_info']['count']}×")
        else:
            st.success("✓ All signals normal")

    # Memory Matches
    st.subheader("Memory Matches")
    if mem:
        for m in mem:
            st.write(f"- {m['summary']} (Similarity: {m['similarity']:.1f}%)")
    else:
        st.write("Memory warming up...")

    # Reasoning Console with Phase Awareness
    st.subheader("Reasoning Console")
    if anomaly and policy_decision:
        reasoning_text = policy_decision['reasoning']
        st.info(f"🧠 {reasoning_text}")
        
        # Show policy decision details
        with st.expander("Policy Decision Details"):
            pd_info = policy_decision['policy_decision']
            st.write(f"**Mission Phase:** {pd_info['mission_phase']}")
            st.write(f"**Anomaly Type:** {pd_info['anomaly_type']}")
            st.write(f"**Severity Level:** {pd_info['severity']}")
            st.write(f"**Response Allowed:** {pd_info['is_allowed']}")
            st.write(f"**Escalation Level:** {pd_info['escalation_level']}")
            st.write(f"**Allowed Actions:** {', '.join(pd_info['allowed_actions']) if pd_info['allowed_actions'] else 'None'}")
    else:
        st.write("No anomaly to reason over.")

    # Response Actions with Phase-Awareness
    st.subheader("Response & Recovery")
    if anomaly and policy_decision:
        st.write(f"**Recommended Action:** `{policy_decision['recommended_action']}`")
        
        if policy_decision['should_escalate_to_safe_mode']:
            st.error("🚨 Escalating to SAFE_MODE for critical anomaly")
        else:
            # Show what actions would be allowed
            allowed_actions = policy_decision['policy_decision']['allowed_actions']
            if allowed_actions:
                st.write(f"**Available in {st.session_state.mission_phase}:**")
                for action in allowed_actions:
                    st.write(f"  ✓ {action}")
            else:
                st.warning(f"⚠️ No automated actions available in {st.session_state.mission_phase}")
    else:
        st.write("No active recovery actions.")

    # Event Log Stream
    st.subheader("Event Log Stream")
    st.code("\n".join(st.session_state.logs[-10:]))

    # Decision Log Stream (phase-aware decisions)
    if st.session_state.decision_logs:
        with st.expander("📊 Decision Log (Phase-Aware)"):
            decision_display = []
            for d in st.session_state.decision_logs[-5:]:
                decision_display.append({
                    "Time": d['timestamp'].strftime("%H:%M:%S"),
                    "Phase": d['mission_phase'],
                    "Anomaly": d['anomaly_type'],
                    "Severity": f"{d['severity_score']:.2f}",
                    "Action": d['recommended_action'],
                    "Escalated": "✓" if d['should_escalate_to_safe_mode'] else ""
                })
            st.dataframe(pd.DataFrame(decision_display), use_container_width=True)

    # Footer
    st.markdown("""
    <style>
    .site-footer {
        background: rgba(10, 14, 26, 0.8);
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        padding: 2rem 0;
        margin-top: 3rem;
        color: #b8b8d1;
        font-family: 'Source Sans Pro', sans-serif;
    }
    .footer-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
    }
    .footer-logo {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-weight: 700;
        color: #ffffff;
    }
    .footer-links {
        display: flex;
        gap: 1.5rem;
    }
    .footer-links a {
        color: #b8b8d1;
        text-decoration: none;
        font-size: 0.9rem;
        transition: color 0.2s;
    }
    .footer-links a:hover {
        color: #3b82f6;
    }
    .footer-copyright {
        font-size: 0.85rem;
        color: #8b8ba7;
    }
    </style>
    <div class="site-footer">
        <div class="footer-content">
            <div class="footer-logo">
                <span>AstraGuard</span>
            </div>
            <div class="footer-links">
                <a href="#" target="_self">Start Telemetry</a>
                <a href="#" target="_self">Stop Telemetry</a>
            </div>
            <div class="footer-copyright">
                &copy; 2025 AstraGuard AI. All rights reserved.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    time.sleep(0.5)  # Slow down slightly to see changes
    st.rerun()
else:
    st.info("📡 Telemetry is offline. Click 'Start Telemetry' to view streams.")

    # Footer for offline state
    st.markdown("""
    <style>
    .site-footer {
        background: rgba(10, 14, 26, 0.8);
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        padding: 2rem 0;
        margin-top: 3rem;
        color: #b8b8d1;
        font-family: 'Source Sans Pro', sans-serif;
    }
    .footer-content {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 1rem;
    }
    .footer-logo {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-weight: 700;
        color: #ffffff;
    }
    .footer-links {
        display: flex;
        gap: 1.5rem;
    }
    .footer-links a {
        color: #b8b8d1;
        text-decoration: none;
        font-size: 0.9rem;
        transition: color 0.2s;
    }
    .footer-links a:hover {
        color: #3b82f6;
    }
    .footer-copyright {
        font-size: 0.85rem;
        color: #8b8ba7;
    }
    </style>
    <div class="site-footer">
        <div class="footer-content">
            <div class="footer-logo">
                <span>AstraGuard</span>
            </div>
             <div class="footer-links">
                <a href="#" target="_self">Start Telemetry</a>
                <a href="#" target="_self">Stop Telemetry</a>
            </div>
            <div class="footer-copyright">
                &copy; 2025 AstraGuard AI. All rights reserved.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
