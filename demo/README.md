# AstraGuard AI Demo

This directory contains materials for demonstrating AstraGuard AI's capabilities.

## 🎥 Demo Video

[![AstraGuard AI Demo](https://img.youtube.com/vi/YOUR_VIDEO_ID/0.jpg)](https://www.youtube.com/watch?v=YOUR_VIDEO_ID)

## 🚀 Quick Demo

### Prerequisites
- Python 3.9+
- Dependencies from `requirements.txt`

### Running the Demo

1. **Start the telemetry simulator**:
   ```bash
   python astraguard/telemetry/telemetry_stream.py
   ```

2. **In a new terminal, start the dashboard**:
   ```bash
   streamlit run dashboard/app.py
   ```

3. **In another terminal, run the 3D visualization**:
   ```bash
   python simulation/attitude_3d.py
   ```

## 📋 Demo Script

See [demo_script.md](demo_script.md) for a detailed walkthrough of the demo.

## 📊 Demo Scenarios

### 1. Normal Operation
- Observe nominal telemetry patterns
- Check system status (NOMINAL)
- Monitor resource usage

### 2. Anomaly Injection
- Enable anomaly simulation
- Observe detection and classification
- Monitor system response

### 3. Recovery Process
- Watch autonomous recovery
- Observe state transitions
- Verify system returns to normal

## 🎮 Interactive Demo

Use the dashboard to:
- Adjust telemetry parameters
- Inject specific faults
- View detailed metrics
- Explore historical data

## 📝 Notes for Presenters

1. **Key Points to Highlight**:
   - Real-time anomaly detection
   - Machine learning integration
   - Autonomous recovery
   - System resilience

2. **Troubleshooting**:
   - Ensure all services are running
   - Check port availability (8501 for Streamlit)
   - Verify dependencies are installed

3. **Customization**:
   - Modify `config.yaml` for different scenarios
   - Adjust anomaly detection sensitivity
   - Customize dashboard layout

## 📈 Performance Metrics

| Metric | Value |
|--------|-------|
| Detection Latency | < 50ms |
| Classification Accuracy | > 95% |
| Recovery Success Rate | > 99% |
| Dashboard Update Rate | 1 Hz |

## 🤝 Support

For help with the demo:
1. Check the [FAQ](../docs/FAQ.md)
2. Open an [issue](https://github.com/sr-857/AstraGuard-AI/issues)
3. Contact the team

## 📄 License

This demo is part of AstraGuard AI, licensed under the MIT License.
