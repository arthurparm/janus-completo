# Janus AI Architect

Janus AI Architect is a cognitive architecture and multi-agent system designed for high reasoning capabilities, integrating State-of-the-Art scientific concepts like GraphRAG, Reflexion, and Language Agent Tree Search (LATS).

## 🌍 Overview

Janus aims to provide a robust, scientifically-grounded AI system capable of complex autonomy and reasoning. It features:
- **Hybrid Memory Architecture:** Episodic (Qdrant) and Semantic (Neo4j) memory.
- **Multi-Agent System:** Specialized agents for planning, coding, and review.
- **Advanced Reasoning:** Implementation of Graph of Thoughts (GoT) and LATS.
- **Security & Safety:** "Constitutional AI" approach with `ReflectorAgent`.

## 📂 Project Structure

- `front/`: Angular 20 frontend application (Vite-based).
- `janus/`: Python/FastAPI backend (The Core).

## 🚀 Quick Start

### Backend (`janus/`)

1.  **Prerequisites:** Python 3.11+, PostgreSQL, Neo4j, Qdrant, RabbitMQ, Redis.
2.  **Setup:**
    ```bash
    cd janus
    pip install -r requirements.txt
    ```
3.  **Run:**
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    *Note: Ensure all infrastructure services are running.*

### Frontend (`front/`)

1.  **Prerequisites:** Node.js 20+.
2.  **Setup:**
    ```bash
    cd front
    npm install
    ```
3.  **Run:**
    ```bash
    npm start
    ```
    Access at `http://localhost:4200`.

## 📚 Documentation

Detailed technical documentation is available in `janus/docs/`:
- [RAG with HyDE](janus/docs/RAG_HYDE.md)
- [Qdrant Resilience](janus/docs/qdrant_resilience_improvements.md)

## 🗺️ Roadmap & Status

The project is currently focusing on **V1 Launch** with strict scientific foundations.

**Key Objectives:**
- **Scientific Foundation:** LATS, Reflexion, Graph of Thoughts.
- **Infrastructure:** Model Routing (DeepSeek V3, Qwen 2.5), Dual-Wallet Budgeting.
- **Critical Path:** Security Hardening, Frontend Refactor, Stability Improvements.
