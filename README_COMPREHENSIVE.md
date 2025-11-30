# 🧠 ADAM - Agentic Decentralized Autonomous Machines

### _Multi-Agent Methane Monitoring with Blockchain Governance_

---

## 📋 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Features](#-features)
- [Quick Start](#-quick-start)
- [Installation](#%EF%B8%8F-installation)
- [Running Configurations](#-running-configurations)
- [Paper Reproducibility](#-paper-reproducibility)
- [Troubleshooting](#-troubleshooting)
- [Citation](#-citation)

---

## 🎯 Overview

**ADAM** is an autonomous methane monitoring system demonstrating **intelligent crew-based coordination** for decentralized physical infrastructure networks (DePIN). The system combines:

- 🤖 **CrewAI** - Dynamic multi-agent coordination
- 🧠 **GPT-4 API** - Adaptive reasoning and decision-making
- 🗄️ **Weaviate** - Vector database for efficient historical data retrieval
- ⛓️ **Blockchain** - Decentralized governance (Fides Innova)
- 🌐 **Edge Computing** - Runs on Raspberry Pi 4 hardware

ADAM enables IoT devices to **autonomously form crews**, **reason collaboratively**, and **execute actions** while maintaining explainable audit trails.

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ADAM System Architecture                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Raspberry Pi   │    │  Raspberry Pi   │    │  Raspberry Pi   │
│   Node 1        │    │   Node 2        │    │   Node 3        │
│                 │    │                 │    │                 │
│  ┌───────────┐  │    │  ┌───────────┐  │    │  ┌───────────┐  │
│  │ MQ-4      │  │    │  │ MQ-4      │  │    │  │ MQ-4      │  │
│  │ Sensor    │  │    │  │ Sensor    │  │    │  │ Sensor    │  │
│  └─────┬─────┘  │    │  └─────┬─────┘  │    │  └─────┬─────┘  │
│        │        │    │        │        │    │        │        │
│  ┌─────▼─────┐  │    │  ┌─────▼─────┐  │    │  ┌─────▼─────┐  │
│  │ Sensor    │  │    │  │ Sensor    │  │    │  │ Sensor    │  │
│  │ Agent     │  │    │  │ Agent     │  │    │  │ Agent     │  │
│  └───────────┘  │    │  └───────────┘  │    │  └───────────┘  │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         │          WiFi 802.11ac                      │
         └──────────────────┬───────────────────────────┘
                            │
              ┌─────────────▼─────────────┐
              │   Shared Infrastructure   │
              ├───────────────────────────┤
              │                           │
              │  ┌─────────────────────┐  │
              │  │ Weaviate Vector DB  │  │
              │  │ (Docker Container)  │  │
              │  │                     │  │
              │  │ • Sensor readings   │  │
              │  │ • Decision traces   │  │
              │  │ • HNSW index        │  │
              │  └─────────────────────┘  │
              │                           │
              │  ┌─────────────────────┐  │
              │  │ Fides Innova Chain  │  │
              │  │ (Blockchain)        │  │
              │  │                     │  │
              │  │ • Governance rules  │  │
              │  │ • Crew registry     │  │
              │  │ • Decision logger   │  │
              │  │ • Consensus         │  │
              │  └─────────────────────┘  │
              │                           │
              │  ┌─────────────────────┐  │
              │  │ OpenAI GPT-4 API    │  │
              │  │ (External)          │  │
              │  │                     │  │
              │  │ • Anomaly reasoning │  │
              │  │ • Decision support  │  │
              │  └─────────────────────┘  │
              └───────────────────────────┘
```

### **Crew Workflow**

```
┌───────────────────────────────────────────────────────────────────┐
│                      ADAM Crew Workflow                           │
└───────────────────────────────────────────────────────────────────┘

  Sensor Reading          Crew Formation         LLM Reasoning
       (1 Hz)              (Auto-trigger)        (GPT-4 API)
         │                       │                     │
         ▼                       ▼                     ▼
    ┌────────┐            ┌────────────┐        ┌──────────┐
    │ MQ-4   │──Normal──▶ │  Weaviate  │        │  OpenAI  │
    │ Sensor │            │   Store    │        │   API    │
    └────────┘            └────────────┘        └──────────┘
         │                       ▲                     ▲
      Anomaly                    │                     │
      (≥5000ppm)                 │                     │
         │                       │                     │
         ▼                       │                     │
    ┌────────────────────────────┼─────────────────────┤
    │  Crew Assembly             │                     │
    ├────────────────────────────┼─────────────────────┤
    │                            │                     │
    │  1. Sensor Agent    ───────┘                     │
    │     • Detects trigger                            │
    │     • Posts to Weaviate                          │
    │                                                   │
    │  2. Aggregator Agent ────────────────────────────┤
    │     • Queries multi-sensor data                  │
    │     • Spatial/temporal aggregation               │
    │                                                   │
    │  3. Decision Agent   ─────────────────────────────▶
    │     • Calls GPT-4 for reasoning
    │     • Analyzes patterns
    │     • Recommends actions
    │
    │  4. Coordinator Agent
    │     • Validates consensus  ──────┐
    │     • Executes actions           │
    │     • Logs to blockchain         │
    └──────────────────────────────────┼──────────────────┐
                                       │                  │
                                       ▼                  ▼
                                  ┌──────────┐      ┌─────────┐
                                  │Blockchain│      │  Email  │
                                  │  Logger  │      │  Alert  │
                                  └──────────┘      └─────────┘
```

---

## ✨ Features

### **Core Capabilities**

- ✅ **Dynamic Crew Formation** - Agents self-organize without centralized orchestration
- ✅ **LLM-Based Reasoning** - Adaptive decision-making using GPT-4 API
- ✅ **Multi-Sensor Aggregation** - Spatial/temporal data fusion across nodes
- ✅ **Blockchain Governance** - Byzantine fault-tolerant consensus on Fides Innova
- ✅ **Vector Database** - Efficient historical data retrieval with Weaviate HNSW
- ✅ **Resource Efficient** - Runs on Raspberry Pi 4 (4GB RAM, no GPU)

### **Paper Reproducibility**

- 📊 **8 System Configurations** - Full system + 3 baselines + 4 ablations
- 📈 **Automated Metrics Collection** - Accuracy, latency, resource usage
- 🔬 **72-Hour Evaluation** - Continuous operation with 450+ coordination events
- 📉 **Figure Generation** - Automated creation of paper figures and tables

---

## 🚀 Quick Start

### **Prerequisites**

- Python 3.12+
- Docker Desktop
- Node.js 16+ (for blockchain deployment)
- OpenAI API key
- Gmail account (for alerts)

### **5-Minute Setup**

```bash
# 1. Clone repository
git clone https://github.com/your-repo/adam.git
cd adam

# 2. Install dependencies
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Start infrastructure
docker compose up -d

# 4. Configure environment
cp configs/.env.full .env
# Edit .env with your API keys

# 5. Initialize database
python -m data_layer.create_schema

# 6. Run ADAM
python -m autonomous.crew
```

---

## ⚙️ Installation

### **Step 1: System Requirements**

| Component   | Minimum                               | Recommended    |
| ----------- | ------------------------------------- | -------------- |
| **RAM**     | 4GB                                   | 8GB+           |
| **Storage** | 10GB                                  | 20GB+          |
| **CPU**     | 2 cores                               | 4+ cores       |
| **OS**      | macOS 13+, Windows 10+, Ubuntu 20.04+ | Latest version |

### **Step 2: Install Python Dependencies**

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install packages
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

**Required packages:**

- `crewai` - Multi-agent orchestration
- `openai` - GPT-4 API client
- `weaviate-client` - Vector database
- `fastapi` - API server
- `web3` - Blockchain integration (optional)

### **Step 3: Start Weaviate Vector Database**

```bash
# Start Docker containers
docker compose up -d

# Wait for startup (30-60 seconds)
docker compose logs -f weaviate

# Verify connection
curl http://127.0.0.1:8080/v1/.well-known/ready
```

**Expected response:** `{"status": "healthy"}`

### **Step 4: Configure Environment**

Create `.env` file in project root:

```bash
# Database
WEAVIATE_URL=http://localhost:8080

# OpenAI API
OPENAI_API_KEY=sk-...
O1_MODEL_NAME=o1-mini
CHAT_MODEL_NAME=gpt-4o-mini

# Email Alerts
GMAIL_USER=your_email@gmail.com
GMAIL_APP_PASSWORD=your_app_password
ALERT_TO=your_email@gmail.com
ALERT_FROM_NAME=Methane Monitor

# Detection Parameters
ABSOLUTE_EMERGENCY_PPM=5000.0
CHECK_INTERVAL_SECONDS=15
ALERT_COOLDOWN_SECONDS=300
DETECTION_LIMIT=50

# Blockchain (Optional - for ADAM Full only)
ENABLE_BLOCKCHAIN=false  # Set true after deploying contracts
FIDES_RPC_URL=https://fidesf1-rpc.fidesinnova.io/
AGENT_PRIVATE_KEY=your_key_here
```

**Get Gmail App Password:**

1. Go to Google Account → Security → App Passwords
2. Generate new password
3. Copy to `GMAIL_APP_PASSWORD`

### **Step 5: Initialize Database Schema**

```bash
python -m data_layer.create_schema
```

**Expected output:**

```
✅ Collection created successfully
Schema ready for use
```

### **Step 6: Deploy Blockchain (Optional - ADAM Full only)**

```bash
cd blockchain

# Install dependencies
npm install

# Generate agent keys
node scripts/generate_keys.js

# Deploy to Fides Innova
npm run deploy:fides

# Register agents
node scripts/register_agents.js
```

**See** `blockchain/README.md` for detailed blockchain setup.

---

## 🎮 Running Configurations

ADAM supports 8 different system configurations for evaluation:

### **Configuration Overview**

| #   | Configuration          | File                                 | Purpose                              |
| --- | ---------------------- | ------------------------------------ | ------------------------------------ |
| 1   | **ADAM (Full)**        | `autonomous/crew.py`                 | Complete system with all components  |
| 2   | **Static-Threshold**   | `ablations/crew_static_threshold.py` | Baseline: No AI, just if/else rules  |
| 3   | **Cloud-Only**         | `ablations/crew_cloud_only.py`       | Baseline: Centralized processing     |
| 4   | **Single-Agent**       | `ablations/crew_single_agent.py`     | Baseline: One agent, no crew         |
| 5   | **ADAM-No-Aggregator** | `ablations/crew_no_aggregator.py`    | Ablation: Skip multi-sensor fusion   |
| 6   | **ADAM-No-LLM**        | `ablations/crew_no_llm.py`           | Ablation: Statistical rules vs GPT-4 |
| 7   | **ADAM-No-Blockchain** | Use .env: `ENABLE_BLOCKCHAIN=false`  | Ablation: No blockchain validation   |
| 8   | **ADAM-No-Weaviate**   | `ablations/crew_no_weaviate.py`      | Ablation: File-based storage         |

### **Run Single Configuration**

```bash
# ADAM (Full)
./run/run_full.sh

# Static-Threshold baseline
./run/run_static.sh

# No-LLM ablation
./run/run_no_llm.sh
```

### **Run All Configurations (72-hour evaluation)**

```bash
# Sequential execution with metrics collection
./run/run_all_ablations.sh

# This will:
# 1. Run each configuration for 72 hours
# 2. Collect metrics (accuracy, latency, resources)
# 3. Save to evaluation/metrics/*.csv
# 4. Generate summary report
```

### **Manual Execution**

```bash
# Activate environment
source .venv/bin/activate

# Run specific configuration
python -m autonomous.crew  # ADAM Full
python -m autonomous.ablations.crew_static_threshold  # Static baseline
python -m autonomous.ablations.crew_no_llm  # No-LLM ablation
```

---

## 🔬 Paper Reproducibility

### **Reproducing All Results**

```bash
# 1. Complete setup (Steps 1-6 from Installation)

# 2. Run 72-hour evaluation
./run/run_all_ablations.sh

# 3. Generate paper figures and tables
cd evaluation
python analyze_results.py

# Outputs:
# - figures/confusion_matrices.png (Figure 6)
# - figures/latency_f1.pdf (Figure 5)
# - figures/scalability_4panel.pdf (Figure 7)
# - figures/resource_efficiency.pdf (Figure 8)
# - results_summary.txt (Tables 1-4)
```

### **Metrics Collected**

Each configuration logs:

**Detection Accuracy:**

- Precision, Recall, F1-score
- False alarm rate
- Confusion matrix

**Latency:**

- Crew formation time (ms)
- Decision latency (ms)
- Median, P95 percentiles

**Resource Usage:**

- CPU utilization (%)
- RAM footprint (MB)
- Network bandwidth (KB/s)
- LLM API costs ($)

**Output format:** CSV files in `evaluation/metrics/`

### **Expected Results**

| Metric                | ADAM (Full)   | Static-Threshold | ADAM-No-LLM   |
| --------------------- | ------------- | ---------------- | ------------- |
| F1-Score              | 0.925 ± 0.014 | 0.776 ± 0.030    | 0.827 ± 0.034 |
| Decision Latency (ms) | 2197 ± 235    | 918 ± 91         | 1061 ± 129    |
| CPU (%)               | 16.6 ± 2.9    | 10.1 ± 2.3       | 13.4 ± 2.1    |
| RAM (MB)              | 643 ± 41      | 592 ± 27         | 606 ± 26      |

### **Time Requirements**

- **Single configuration:** 72 hours (3 days)
- **All 8 configurations:** 576 hours (24 days) if sequential
- **Parallel execution:** 72 hours with 8 Raspberry Pis

---

## 🔧 Troubleshooting

### **Common Issues**

#### ❌ Docker not starting

```bash
# Solution: Open Docker Desktop manually
open -a Docker  # macOS
# Wait for "Docker is running" indicator
```

#### ❌ Weaviate connection failed

```bash
# Check if running
docker ps | grep weaviate

# Restart if needed
docker compose restart weaviate

# Check logs
docker compose logs weaviate
```

#### ❌ OpenAI API errors

```bash
# Verify API key
python -c "import openai; openai.api_key='your-key'; print('OK')"

# Check rate limits
# If rate limited, wait or upgrade plan
```

#### ❌ Email alerts not sending

```bash
# Verify Gmail App Password (not regular password)
# Check .env file has correct credentials
# Test connection:
python -c "from autonomous.email_alert import send_email_alert; send_email_alert('Test', 'Body', ['your@email.com'])"
```

#### ❌ ModuleNotFoundError

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### **Debug Mode**

```bash
# Run with verbose logging
LOG_LEVEL=DEBUG python -m autonomous.crew

# Check Weaviate data
curl http://127.0.0.1:8080/v1/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ Get { SensorEvent(limit:5) { node_id methane_ppm timestamp } } }"}'
```

### **Reset System**

```bash
# Stop all services
docker compose down

# Remove volumes (clears data)
docker compose down -v

# Restart fresh
docker compose up -d
python -m data_layer.create_schema
```

---

## 📂 Project Structure

```
adam/
├── autonomous/           # Core system
│   ├── crew.py          # ADAM (Full)
│   ├── reasoning_agent.py
│   ├── email_alert.py
│   ├── api_server.py
│   └── ablations/       # Baseline & ablation variants
├── data_layer/          # Weaviate integration
├── blockchain/          # Smart contracts & deployment
├── simulation/          # Data generation
├── run/                 # Execution scripts
├── evaluation/          # Metrics & analysis
├── configs/             # Environment configs
├── docker-compose.yml
├── requirements.txt
└── README.md
```

**See:** `FILE_PLACEMENT_GUIDE.md` for complete structure

---

## 📚 Additional Documentation

- 📖 [File Placement Guide](FILE_PLACEMENT_GUIDE.md) - Where to put each file
- 🔗 [Blockchain Setup](blockchain/README.md) - Deploy smart contracts
- 📊 [Metrics Collection](evaluation/README.md) - Data analysis guide
- 🎓 [Paper Supplement](PAPER_REPRODUCIBILITY.md) - Detailed evaluation protocol

---

## 📄 Citation

If you use ADAM in your research, please cite:

```bibtex
@article{your2025adam,
  title={Agentic Decentralized Autonomous Machines for Adaptive Multi-Agent Coordination in DePIN},
  author={Your Name},
  journal={IEEE Conference},
  year={2025}
}
```

---

## 📧 Contact

- **Author:** Your Name
- **Email:** your.email@university.edu
- **Paper:** [Link to paper](your-paper-link)
- **Issues:** [GitHub Issues](https://github.com/your-repo/adam/issues)

---

## 📜 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **CrewAI** for multi-agent orchestration framework
- **Weaviate** for vector database infrastructure
- **OpenAI** for GPT-4 API access
- **Fides Innova** for blockchain testnet
- **University of Wyoming** for research support

---

<p align="center">
  <strong>Built with ❤️ for decentralized autonomous systems research</strong>
</p>

<p align="center">
  ⭐ Star this repo if you find it useful!
</p>
