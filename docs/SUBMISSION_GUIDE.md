# 🚀 AstraGuard AI: Hackathon Submission Guide

This document provides a "ready-to-submit" breakdown of AstraGuard AI for the **Synaptix Frontier AI Hackathon**. Use these sections to fill out your submission form.

---

## 1. Project Title & Tagline
**Title:** AstraGuard AI  
**Tagline:** Autonomous Fault Detection & Recovery System for CubeSats with Adaptive Memory.

---

## 2. Problem & Solution (The "Why")
**Problem:**  
CubeSats face a "Latency Gap" where critical hardware failures happen faster than ground control can respond. Traditional AI models are either too "static" (threshold-based) or too "heavy" (LLM context bloat) for edge deployment in space.

**Solution:**  
AstraGuard AI implements a **Security-First Agentic Architecture**. It uses the **Pathway Engine** for real-time streaming awareness and a biologically-inspired **Adaptive Memory Engine** that prunes irrelevant data while reinforcing critical failure patterns. It doesn't just detect; it reasons and acts autonomously to save the spacecraft.

---

## 3. Technical Deep Dive (The "How")

### A. Real-Time Streaming (Pathway)
We use Pathway to process 5Hz telemetry streams. Unlike batch processing, Pathway allows the agent to maintain a "live" state of the satellite, enabling sub-350ms response times from detection to recovery action.

### B. Adaptive Memory Engine
Our custom memory store implements:
- **Temporal Decay**: $W = e^{-\lambda t}$ ensures the agent focuses on recent trends.
- **Recurrence Resonance**: A signal reinforcement algorithm that boosts the importance of repeating minor faults before they become catastrophic.
- **Safe Pruning**: Critical events are "pinned" in memory, ensuring the agent never forgets a high-severity failure signature.

### C. Agentic Decision Loop
The agent follows a **Detect → Recall → Reason → Act → Learn** cycle. It uses vector embeddings (384-dim) to find similar historical incidents, allowing it to "remember" how it solved a similar problem in the past.

---

## 4. Innovations & Analysis
- **Sub-Second Latency**: Total pipeline latency is ~325ms, outperforming human operators by orders of magnitude.
- **Edge-Ready**: Memory footprint is optimized (<400MB) for satellite On-Board Computers (OBCs).
- **Explainable Agency**: Every autonomous action is accompanied by a reasoning trace, ensuring human operators can trust the AI's decisions.

---

## 5. Future Scope & Roadmap
- **Swarm Intelligence**: Multi-satellite memory sharing for constellation-wide learning.
- **Deep BDH Integration**: Implementing sparse neural activation for ultra-low power "Eclipse Mode" operations.
- **Hardware-in-the-Loop**: Deploying to Jetson Nano/Raspberry Pi flatsats for physical validation.

---

## 6. Links & Assets
- **GitHub Repository:** [https://github.com/sr-857/AstraGuard](https://github.com/sr-857/AstraGuard)
- **Landing Site:** [https://ide-birch-01200854.figma.site/](https://ide-birch-01200854.figma.site/)
- **Technical Report:** [docs/FINAL_REPORT.md](https://github.com/sr-857/AstraGuard/blob/main/docs/FINAL_REPORT.md)

---
**AstraGuard AI** | *Protecting the future of space with intelligent autonomy.* 🛰️✨
