
#!/usr/bin/env python3
import streamlit as st
import subprocess, json, time, os
from pathlib import Path
from logs.timeline import read_recent, log_event
import altair as alt
import pandas as pd

st.set_page_config(page_title="AstraGuard AI Dashboard", layout="wide")
st.title("AstraGuard AI – Autonomous Fault Detection & Recovery")

col1, col2 = st.columns([2, 1])

# start telemetry producer as subprocess
TELEMETRY_PY = str(Path(__file__).parent.parent / "telemetry" / "telemetry_stream.py")
proc = subprocess.Popen(["python3", TELEMETRY_PY], stdout=subprocess.PIPE, text=True)

with col1:
    st.subheader("Live Telemetry")
    telemetry_area = st.empty()
    chart_area = st.empty()

with col2:
    st.subheader("System Status")
    state_box = st.empty()
    fault_box = st.empty()
    st.subheader("Recent Events")
    events_box = st.empty()

# history
history = {"voltage": [], "temperature": [], "gyro": [], "anomaly_score": []}
from anomaly.anomaly_detector import detect_anomaly, load_model
from classifier.fault_classifier import classify
from state_machine.state_engine import decide_action

# pre-load model
try:
    from anomaly.anomaly_detector import load_model as lm
    lm()
except Exception as e:
    st.warning("Training/loading anomaly model: " + str(e))

for i in range(200):
    line = proc.stdout.readline()
    if not line:
        time.sleep(0.1)
        continue
    data = json.loads(line)
    state = data["data"]
    injected = data.get("fault", None)

    telemetry_area.json(state)

    sample = [
        state.get("voltage") or 0,
        state.get("current") or 0,
        state.get("temperature") or 0,
        state.get("gyro") or 0,
        state.get("wheel_speed") or 0
    ]
    is_anom, score = detect_anomaly(sample)
    history["voltage"].append(sample[0])
    history["temperature"].append(sample[2])
    history["gyro"].append(sample[3])
    history["anomaly_score"].append(score)

    df = pd.DataFrame({
        "step": list(range(len(history["voltage"]))),
        "voltage": history["voltage"],
        "temperature": history["temperature"],
        "gyro": history["gyro"],
        "anomaly_score": history["anomaly_score"]
    })

    # charts
    chart = alt.Chart(df).mark_line().encode(x="step", y="voltage").properties(height=150)
    chart_temp = alt.Chart(df).mark_line().encode(x="step", y="temperature").properties(height=150)
    chart_gyro = alt.Chart(df).mark_line().encode(x="step", y="gyro").properties(height=150)
    chart_area.altair_chart(alt.vconcat(chart, chart_temp, chart_gyro), use_container_width=True)

    # classify and decide
    fault_type = classify(state)
    action, desc = decide_action(fault_type)
    if is_anom or injected:
        log_event("ANOMALY" if is_anom else "FAULT_INJECTED", f"{fault_type} score={score:.3f}")
    state_box.info(f"State: {action} — {desc}")
    if fault_type != "normal":
        fault_box.error(f"Detected: {fault_type}")
    else:
        fault_box.success("No active faults")

    events_box.text("\n".join(read_recent(8)))

    time.sleep(0.2)
