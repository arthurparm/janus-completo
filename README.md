# Janus AI Architect

Janus AI Architect is a cutting-edge Hybrid Agent Architecture system designed for complex reasoning, planning, and execution. It leverages GraphRAG (Neo4j), Vector Memory (Qdrant), and Multi-Agent Systems to deliver a robust and scientific approach to AI autonomy.

## 🏗️ Architecture Overview

The system is composed of two main components:

- **Backend (`janus/`)**: A high-performance Python/FastAPI application acting as the brain. It manages:
  - **Reasoning & Planning**: Using Language Agent Tree Search (LATS), Graph of Thoughts (GoT), and Reflexion.
  - **Memory**: Hybrid memory architecture with Episodic (Vector/Qdrant) and Semantic (Graph/Neo4j) memory.
  - **Multi-Agent System**: Orchestration of specialized agents (Coder, Architect, Product Manager).
  - **Infrastructure**: Redis for state/caching, RabbitMQ for messaging, and PostgreSQL for configuration/HITL.

- **Frontend (`front/`)**: A modern Angular 20 application providing the interface for:
  - **Chat & Collaboration**: Real-time interaction with the agent system.
  - **System Observability**: Monitoring agent states, memory, and performance.
  - **Management**: Configuration of tools, goals, and autonomous loops.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- Docker & Docker Compose (for Neo4j, Qdrant, Redis, RabbitMQ, Postgres)

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd janus
   ```
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the backend server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd front
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the development server:
   ```bash
   npm start
   ```
   The application will be available at `http://localhost:4200`.

## 📚 Documentation

- **[Roadmap & Strategy](docs/ROADMAP.md)**: Detailed roadmap, scientific foundation, and backlog.
- **[System Inventory](docs/INVENTORY.md)**: Comprehensive inventory of API routes, tasks, and system components.
- **[Frontend Documentation](front/README.md)**: Specific details about the Angular frontend.
- **Backend Documentation**: Technical docs located in `janus/docs/`.

## 🧪 Scientific Foundation

Janus is grounded in state-of-the-art research, implementing concepts such as:
- **LATS (Language Agent Tree Search)** for planning.
- **Reflexion** for self-correction.
- **GraphRAG** for structured retrieval.
- **HyDE** for improved semantic search.

For more details, refer to the [Roadmap](docs/ROADMAP.md).
