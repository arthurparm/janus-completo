# Janus AI Architect

Janus is a Meta-Agent architecture designed for autonomous software development and orchestration. It uses a hybrid memory architecture (Qdrant + Neo4j) and follows an OODA loop (Observe, Orient, Decide, Act) with validation and reflection.

## Architecture

The system consists of two main components:

- **Frontend (`front/`)**: An Angular application serving as the user interface.
- **Backend (`janus/`)**: A Python/FastAPI backend implementing the Multi-Agent System (MAS), using LangGraph, SQLAlchemy, and various other tools.

## Getting Started

### Prerequisites

- Node.js 20+
- Python 3.11+
- Docker & Docker Compose (for infrastructure like Neo4j, Qdrant, Redis, RabbitMQ)

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repo-url>
    cd janus-repo
    ```

2.  **Start Infrastructure:**
    ```bash
    docker-compose up -d
    ```

3.  **Backend Setup:**
    See [janus/README.md](janus/README.md) for detailed instructions.
    ```bash
    cd janus
    pip install -r requirements.txt
    uvicorn app.main:app --host 0.0.0.0 --port 8000
    ```

4.  **Frontend Setup:**
    See [front/README.md](front/README.md) for detailed instructions.
    ```bash
    cd front
    npm install
    npm start
    ```

## Documentation

- **Roadmap & Inventory**: See [docs/INVENTORY.md](docs/INVENTORY.md) for detailed system inventory, scientific foundations, and technical debt.
- **Backend Documentation**: See `janus/docs/`.

## License

[License Information]
