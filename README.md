# Janus

**Janus** is an advanced AI Architect Agent System designed to orchestrate complex tasks, manage memory and knowledge, and provide an autonomous coding and planning experience.

## 📚 Documentation

Detailed documentation about the project roadmap, tasks, and system inventory can be found in the `docs/` directory:

- [**Roadmap & Strategy**](docs/ROADMAP.md): Project goals, scientific foundation, infrastructure strategy, and critical path.
- [**Inventory & Tasks**](docs/INVENTORY.md): Detailed surveys of the system, API inventory, and task batches.

## 🏗️ Components

The project consists of two main components:

### 1. Backend (`janus/`)
The core of the system, built with **Python 3.11+** and **FastAPI**. It handles agent orchestration, memory (Neo4j/Qdrant), LLM integration, and business logic.

- [**Explore Backend**](janus/)

### 2. Frontend (`front/`)
The web interface, built with **Angular 20**. It provides a professional UI for chatting with agents, managing autonomy goals, and observing system health.

- [**Explore Frontend**](front/)

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+

### Running the System

Please refer to the specific README files in each component directory for detailed setup instructions.

- **Backend Setup**: See `janus/README.md` (or check local setup in `janus/` folder structure).
- **Frontend Setup**: See [`front/README.md`](front/README.md).

For a full system startup using Docker:
```bash
docker-compose up -d
```
*(Ensure all environment variables are configured in `.env`)*

## 📄 License

[MIT](LICENSE)
