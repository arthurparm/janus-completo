# Janus AI Architect

**Janus** is an integrated development environment for self-improving AI agents, designed to act as an autonomous software architect. It combines advanced reasoning capabilities, memory management, and secure execution to help build and maintain complex software systems.

## 🚀 Overview

The project is divided into two main components:

- **[Janus Backend](janus/)**: The core intelligence, built with Python (FastAPI), implementing the Hybrid Agent Architecture, Memory Systems (Neo4j/Qdrant), and Autonomy Loops.
- **[Janus Frontend](front/)**: The web interface, built with Angular 20, providing a professional environment for interacting with agents, managing goals, and visualizing the knowledge graph.

## 📚 Documentation

The documentation is organized to track the project's evolution and technical details:

- **[Roadmap & Backlog](docs/ROADMAP.md)**: The strategic vision, scientific foundations, and critical path for V1.
- **[Inventory & Tasks](docs/INVENTORY.md)**: Detailed system listings, API inventories, and technical debt tracking.

## 🛠️ Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### Running the Stack

1. **Start Infrastructure**:
   ```bash
   docker-compose up -d
   ```
   This will start Neo4j, Qdrant, Redis, RabbitMQ, and other support services.

2. **Backend Setup**:
   ```bash
   cd janus
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Frontend Setup**:
   ```bash
   cd front
   npm install
   npm start
   ```

Access the frontend at `http://localhost:4200`.

## 🏗️ Architecture

Janus is built on the shoulders of giants, integrating state-of-the-art concepts from recent AI research:

- **Reasoning**: Uses **LangGraph** for complex agent orchestration (Planner, Reflector, Executor).
- **Memory**: A hybrid approach using **Neo4j** for semantic knowledge (GraphRAG) and **Qdrant** for episodic memory (Vector).
- **Security**: Code execution is sandboxed using Docker containers to ensure safety.

For a deep dive into the scientific papers and concepts backing this project (like LATS, Reflexion, Graph of Thoughts), please refer to the [Scientific Foundation](docs/ROADMAP.md#%F0%9F%94%AC-scientific-foundation-state-of-the-art) section in the Roadmap.

## 🤝 Contributing

This project is currently in active development. Check the [Roadmap](docs/ROADMAP.md) to see what's coming next.
