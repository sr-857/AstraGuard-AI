
# AstraGuard AI — Round 2 Prototype (Complete)

**Overview**
AstraGuard AI simulates an onboard intelligence stack that detects anomalies in CubeSat telemetry and autonomously triggers recovery actions.

**Quickstart**
1. python3 -m pip install -r requirements.txt
2. python3 anomaly/anomaly_detector.py   # trains model if missing
3. streamlit run dashboard/app.py
4. (Optional) python3 simulation/attitude_3d.py

**Project Structure**
- telemetry/ : telemetry_stream.py (produces JSON lines)
- anomaly/ : anomaly_detector.py (IsolationForest model)
- classifier/ : fault_classifier.py
- state_machine/ : state_engine.py
- dashboard/ : Streamlit UI
- simulation/ : 3D attitude visualizer
- logs/ : event_log.txt and timeline.py
- demo/ : demo scripts and video script

**Author**
Subhajit Roy
