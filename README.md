# 🌌 Janus AI Architect

**The Meta-Agent System for Autonomous Software Development.**

Janus is an advanced AI system designed to assist in software architecture, development, and evolution. It employs a **Meta-Agent Architecture** orchestrated by LangGraph, capable of reasoning, planning, reflecting, and executing complex coding tasks.

---

## 📚 Documentation & Roadmap

This `README.md` serves as the entry point. For detailed documentation, please refer to:

- **[Roadmap & Technical Debt (V1 Launch)](docs/ROADMAP.md)**: Critical path, scientific foundation, and future evolution.
- **[System Inventory & Tasks](docs/INVENTORY.md)**: Detailed listing of API endpoints, services, and current task batches.

---

## 📂 Repository Structure

The project is organized into the following components:

- **`janus/`**: The Backend Core. Built with **Python 3.11+** and **FastAPI**. It handles the agentic logic, memory systems (Neo4j + Qdrant), and LLM orchestration.
  - [Go to Backend README](janus/README.md)
- **`front/`**: The Frontend Interface. Built with **Angular 20**. It provides a professional UI for interacting with Janus, visualizing thought streams, and managing projects.
  - [Go to Frontend README](front/README.md)
- **`docs/`**: Project-level documentation.

---

## 🚀 Getting Started

### Prerequisites

- **Docker & Docker Compose**: Required for running infrastructure dependencies (Neo4j, Qdrant, RabbitMQ, Redis).
- **Python 3.11+**: For the backend.
- **Node.js 20+**: For the frontend.

### Quick Start

1.  **Start Infrastructure**:
    ```bash
    docker-compose up -d
    ```

2.  **Setup Backend (`janus/`)**:
    Follow the instructions in [`janus/README.md`](janus/README.md) to install dependencies and start the server.

3.  **Setup Frontend (`front/`)**:
    Follow the instructions in [`front/README.md`](front/README.md) to install dependencies and start the web interface.

---

## 🏗️ Architecture Highlights

- **Meta-Agent**: Implemented with LangGraph (Monitor, Diagnose, Plan, Reflect, Execute).
- **Hybrid Memory**: Episodic (Qdrant Vector DB) + Semantic (Neo4j Graph DB).
- **Dual-LLM Strategy**: "Workhorse" (DeepSeek V3) for heavy lifting and "Architect" (Qwen 2.5 72B) for reasoning/review.
- **Resilience**: Circuit Breakers, Rate Limiting, and Constitutional AI safety checks.

---

> *Note: This project is under active development. Please consult the [Roadmap](docs/ROADMAP.md) for the current status.*
