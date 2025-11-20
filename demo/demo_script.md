# AstraGuard AI Demo Script

This script provides a step-by-step guide for demonstrating AstraGuard AI's capabilities.

## 🎬 Introduction (1-2 minutes)

**Talking Points:**
- "Welcome to AstraGuard AI, an autonomous fault detection and recovery system for CubeSats."
- "Today, I'll demonstrate how our system monitors spacecraft telemetry, detects anomalies, and performs autonomous recovery."
- "The system uses machine learning for anomaly detection and a state machine for autonomous decision making."

## 🖥️ System Overview (2-3 minutes)

1. **Dashboard Walkthrough**
   - Point out the main components:
     - Telemetry metrics
     - System status
     - Anomaly detection panel
     - Recovery status
     - Event timeline

2. **3D Visualization**
   - Show the spacecraft model
   - Explain the coordinate system
   - Demonstrate attitude control

## 🚀 Demo: Normal Operation (3-4 minutes)

1. **Start the System**
   ```bash
   # Terminal 1 - Start telemetry
   python telemetry/telemetry_stream.py
   
   # Terminal 2 - Start dashboard
   streamlit run dashboard/app.py
   
   # Terminal 3 - Start 3D visualization
   python simulation/attitude_3d.py
   ```

2. **Observe Nominal Behavior**
   - Show telemetry streams
   - Point out normal ranges
   - Highlight system status (NOMINAL)

## ⚠️ Demo: Anomaly Detection (4-5 minutes)

1. **Inject Anomaly**
   - In the dashboard, click "Simulate Anomaly"
   - Or use the CLI:
     ```bash
     python demo/inject_anomaly.py --type power --severity high
     ```

2. **Observe Detection**
   - Watch anomaly score increase
   - See fault classification
   - Note system state change

3. **Explain ML Model**
   - Isolation Forest algorithm
   - Training on nominal data
   - Real-time scoring

## 🔄 Demo: Recovery Process (3-4 minutes)

1. **Show State Transitions**
   - NOMINAL → ANOMY_DETECTED
   - ANOMY_DETECTED → RECOVERY
   - RECOVERY → NOMINAL

2. **Explain Recovery Actions**
   - Power cycle components
   - Switch to backup systems
   - Adjust operational parameters

3. **Verify Recovery**
   - Show telemetry returning to normal
   - Confirm system status
   - Review event log

## 📊 Advanced Features (2-3 minutes)

1. **Historical Analysis**
   - Show past anomalies
   - Filter by date/severity
   - Export data options

2. **Configuration**
   - Adjust detection sensitivity
   - Modify recovery parameters
   - Customize dashboard layout

## ❓ Q&A (Remaining Time)

**Common Questions:**
1. How does the ML model handle new types of anomalies?
2. What's the system's response time for critical failures?
3. How does it handle multiple simultaneous anomalies?
4. What's the training data source?
5. How does it perform with real satellite data?

## 🎉 Conclusion (1 minute)

- Recap key features
- Highlight unique aspects
- Share next steps
- Provide contact information

## 🛠️ Troubleshooting

**Issue: Dashboard not updating**
- Check if telemetry stream is running
- Verify port 8501 is available
- Check browser console for errors

**Issue: 3D visualization lagging**
- Reduce update frequency
- Close other GPU-intensive applications
- Try a different browser

## 📝 Notes
- This demo takes approximately 15-20 minutes
- Practice timing before the actual presentation
- Have backup screenshots/videos ready
- Prepare answers to technical questions

## 📞 Support
For immediate assistance:
- Email: support@astraguard.ai
- GitHub Issues: https://github.com/sr-857/AstraGuard-AI/issues
