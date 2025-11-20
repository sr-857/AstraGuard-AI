# Getting Started with AstraGuard AI

Welcome to AstraGuard AI! This guide will help you set up and start using the Autonomous Fault Detection & Recovery System for CubeSats.

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- pip (Python package manager)
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sr-857/AstraGuard-AI.git
   cd AstraGuard-AI
   ```

2. **Create and activate a virtual environment** (recommended)
   ```bash
   # On Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # On macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## 🖥️ Running the Dashboard

1. **Start the Streamlit dashboard**
   ```bash
   streamlit run dashboard/app.py
   ```

2. **Open your browser** to the URL shown in the terminal (usually http://localhost:8501)

## 🛠️ Running the Simulation

To run the 3D attitude simulation:
```bash
python simulation/attitude_3d.py
```

## 🔍 Testing the System

Run the test suite:
```bash
pytest
```

## 📊 Understanding the System

### System Architecture

```
AstraGuard AI/
├── dashboard/         # Streamlit web interface
├── telemetry/         # Telemetry generation and simulation
├── anomaly/           # Anomaly detection using ML
├── classifier/        # Fault classification
├── state_machine/     # Autonomous recovery logic
├── simulation/        # 3D visualization
└── logs/              # Event logging and timeline
```

### Key Components

1. **Telemetry System**
   - Simulates spacecraft sensors
   - Generates realistic telemetry data
   - Handles data streaming

2. **Anomaly Detection**
   - Machine learning-based detection
   - Real-time scoring
   - Configurable thresholds

3. **Fault Classification**
   - Rule-based classification
   - Severity assessment
   - Recovery recommendations

4. **State Machine**
   - Autonomous decision making
   - Recovery procedures
   - System health management

## 📈 Monitoring and Debugging

View system logs:
```bash
# View recent logs
python -m logs.timeline

# Filter logs by type
python -m logs.timeline --filter ANOMALY
```

## 🚀 Deployment

For production deployment, consider using:
- Docker containers
- Kubernetes for orchestration
- Prometheus for monitoring
- Grafana for visualization

## 📚 Learning Resources

- [Documentation](https://github.com/sr-857/AstraGuard-AI/wiki)
- [API Reference](docs/API.md)
- [Video Tutorials](https://youtube.com/playlist?list=YOUR_PLAYLIST_ID)

## 🤝 Getting Help

If you encounter any issues:
1. Check the [FAQ](docs/FAQ.md)
2. Search the [issue tracker](https://github.com/sr-857/AstraGuard-AI/issues)
3. Open a new issue if your problem isn't reported

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
