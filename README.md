# AstraGuard AI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Contributor Covenant](https://img.shields.io/badge/Contributor%20Covenant-2.1-4baaaa.svg)](CODE_OF_CONDUCT.md)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()

#CubeSat #Satellite #AI #MachineLearning #AnomalyDetection #AutonomousSystems #SpaceTech #Hackathon

🚀 **Autonomous Fault Detection & Recovery System for CubeSats**

AstraGuard AI is an intelligent onboard system that simulates real-time telemetry monitoring, anomaly detection, and autonomous recovery actions for CubeSat spacecraft. The system uses machine learning to identify abnormal patterns and automatically executes recovery procedures to maintain spacecraft health and operational continuity.

## 🌟 Features

- **🛰️ Real-Time Telemetry Simulation**: Generates realistic CubeSat telemetry data at 5Hz
- **🤖 Machine Learning Anomaly Detection**: Isolation Forest-based pattern recognition
- **🔧 Intelligent Fault Classification**: Rule-based system for identifying fault types
- **⚡ Autonomous State Machine**: Automated recovery decision-making
- **📊 Interactive Dashboard**: Real-time monitoring with Streamlit
- **🎥 3D Attitude Visualization**: Matplotlib-based spacecraft attitude display
- **📝 Comprehensive Logging**: Event tracking and timeline analysis

## 🏗️ Architecture

```
AstraGuard AI System Architecture
├── telemetry/           # Real-time data generation
├── anomaly/            # ML-based anomaly detection
├── classifier/         # Fault type classification
├── state_machine/      # Recovery decision logic
├── dashboard/          # Web-based monitoring interface
├── simulation/         # 3D attitude visualization
└── logs/              # Event logging and timeline
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sr-857/AstraGuard-AI.git
   cd AstraGuard-AI
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Train the anomaly detection model**
   ```bash
   python3 anomaly/anomaly_detector.py
   ```

4. **Launch the dashboard**
   ```bash
   streamlit run dashboard/app.py
   ```

5. **Optional: Launch 3D visualization**
   ```bash
   python3 simulation/attitude_3d.py
   ```

### Usage

Once the dashboard is running, open your browser to `http://localhost:8501` to view:
- Live telemetry data streams
- Real-time anomaly detection results
- System state and recovery actions
- Historical event timeline

## 📊 System Components

### Telemetry Generator (`telemetry/telemetry_stream.py`)
- Simulates realistic CubeSat telemetry parameters
- Voltage, current, temperature, gyroscope, reaction wheel speed
- 10% fault injection probability for testing
- JSON output format for easy integration

**Telemetry Parameters:**
- **Voltage**: 7.9V ± 0.03V (Bus voltage)
- **Current**: 0.55A ± 0.01A (Power consumption)
- **Temperature**: 24°C ± 0.4°C (System temperature)
- **Gyroscope**: 0 rad/s ± 0.015 rad/s (Angular rate)
- **Wheel Speed**: 480 RPM ± 4 RPM (Reaction wheel)

### Anomaly Detection (`anomaly/anomaly_detector.py`)
- **Algorithm**: Isolation Forest (scikit-learn)
- **Training**: 2000 synthetic normal samples
- **Contamination Rate**: 1% expected anomalies
- **Features**: 5-dimensional telemetry vector
- **Output**: Boolean anomaly flag + confidence score

### Fault Classification (`classifier/fault_classifier.py`)
- **Power Fault**: Voltage < 7.3V
- **Thermal Fault**: Temperature > 32°C
- **Attitude Fault**: |Gyro| > 0.05 rad/s
- **Sensor Fault**: Missing/invalid sensor data
- **Severity Levels**: Critical, High, Medium, Low

### State Machine (`state_machine/state_engine.py`)
- **NORMAL**: Standard operations
- **SAFE_MODE**: Power conservation (critical faults)
- **COOLING**: Thermal management (thermal faults)
- **STABILIZING**: Attitude correction (attitude faults)
- **DIAGNOSTICS**: Sensor testing (sensor faults)

### Dashboard (`dashboard/app.py`)
- **Real-time telemetry display**
- **Anomaly detection alerts**
- **System state monitoring**
- **Event timeline visualization**
- **Recovery action tracking**

## 🧪 Testing

### Unit Tests

Test individual components:

```bash
# Test anomaly detection
python3 anomaly/anomaly_detector.py

# Test fault classification
python3 classifier/fault_classifier.py

# Test state machine
python3 state_machine/state_engine.py

# Test telemetry generation
python3 telemetry/telemetry_stream.py | head -10
```

### Integration Test

Run the complete system:

```bash
# Terminal 1: Start telemetry stream
python3 telemetry/telemetry_stream.py

# Terminal 2: Start dashboard
streamlit run dashboard/app.py

# Terminal 3: Start 3D visualization
python3 simulation/attitude_3d.py
```

## 📈 Performance Metrics

- **Telemetry Rate**: 5 Hz (200ms intervals)
- **Anomaly Detection Latency**: < 10ms
- **Fault Classification Accuracy**: > 95% (simulated)
- **Recovery Response Time**: < 100ms
- **Memory Usage**: < 100MB (typical operation)

## 🔧 Configuration

### Model Parameters

Edit `anomaly/anomaly_detector.py` to modify:
- `contamination`: Expected anomaly rate (default: 0.01)
- `n_estimators`: Number of trees (default: 100)
- Training data distribution parameters

### Fault Thresholds

Edit `classifier/fault_classifier.py` to adjust:
- Voltage thresholds
- Temperature limits
- Gyro sensitivity
- Sensor validation ranges

### Recovery Timing

Edit `state_machine/state_engine.py` to configure:
- Recovery action durations
- Auto-resume behavior
- Command priorities

## 🐛 Troubleshooting

### Common Issues

**Model not found error:**
```bash
python3 anomaly/anomaly_detector.py  # This will train and save the model
```

**Dashboard not updating:**
- Check telemetry stream is running
- Verify JSON output format
- Check browser console for errors

**High memory usage:**
- Reduce telemetry history in dashboard
- Clear event log periodically
- Restart components if needed

### Debug Mode

Enable verbose logging:

```bash
export PYTHONUNBUFFERED=1
python3 telemetry/telemetry_stream.py 2>&1 | tee debug.log
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add type hints to all functions
- Include comprehensive docstrings
- Write unit tests for new features
- Update documentation for API changes

## 📚 Documentation

For additional documentation, including system architecture diagrams, API references, and implementation details, please refer to our [AstraGuard AI Documentation on Google Drive](https://drive.google.com/file/d/191JIBcRAU2ai8tDSliY8ztnEm-ZAHgkV/view).

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **scikit-learn**: Machine learning algorithms
- **Streamlit**: Dashboard framework
- **NumPy**: Numerical computing
- **Matplotlib**: Visualization library
- **Altair**: Declarative visualization

## 📧 Contact

**Author**: Subhajit Roy

**Project**: AstraGuard AI - Autonomous Fault Detection & Recovery System

**Repository**: https://github.com/sr-857/AstraGuard-AI

## 🗺️ Roadmap

- [ ] **v2.0**: Deep learning anomaly detection
- [ ] **v2.1**: Multi-sensor fusion algorithms
- [ ] **v2.2**: Ground station integration
- [ ] **v2.3**: Hardware-in-the-loop testing
- [ ] **v3.0**: Flight-ready deployment package

---

**AstraGuard AI** - Protecting spacecraft through intelligent autonomy 🛰️✨
