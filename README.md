# Janus AI Architect

Janus is an advanced cognitive architecture designed to operate as a strategic supervisor (Meta-Agent), capable of reasoning, planning, and orchestrating complex tasks through a specialized multi-agent system.

It implements a hybrid memory architecture (Episodic/Vector + Semantic/Graph) and uses State-of-the-Art (SOTA) concepts such as **Graph of Thoughts (GoT)**, **Language Agent Tree Search (LATS)**, and **Self-Correction (Reflexion)** to deliver high-precision autonomous software engineering and system architecture capabilities.

---

## 📚 Documentation

*   [**Roadmap & Technical Debt**](docs/ROADMAP.md) - Critical path for V1, scientific backlog, and infrastructure strategy.
*   [**System Inventory**](docs/INVENTORY.md) - Detailed listings of API endpoints, system components, and technical debt surveys.
*   [**Backend Documentation**](janus/README.md) - Specific setup for the Python/FastAPI backend.
*   [**Frontend Documentation**](front/README.md) - Specific setup for the Angular frontend.

---

## 🔬 Scientific Foundations

Janus is built upon 13+ seminal papers that ground its intelligence:

### 🧠 Reasoning & Planning (The Brain)
*   **Graph of Thoughts (GoT)**: Models thought as a graph (DAG), allowing combining and refining ideas.
*   **LATS (Language Agent Tree Search)**: Simulates scenarios via MCTS before executing critical actions.
*   **Reflexion**: Self-correction loops where agents verbalize errors and learn from them.
*   **Chain of Thought (CoT)**: Mandatory "step-by-step" reasoning in all system prompts.

### 💾 Memory & Learning (The Soul)
*   **Generative Agents**: Memory with Recency, Importance, and Relevance.
*   **HyDE (Hypothetical Document Embeddings)**: Generates hypothetical answers to improve retrieval.
*   **Hybrid Memory**: Combines **Qdrant** (Vector/Episodic) and **Neo4j** (Graph/Semantic).

### 🔍 Retrieval & RAG (The Knowledge)
*   **Native GraphRAG**: Knowledge retrieval using graph structures for deeper context.
*   **Self-RAG**: The model critiques its own retrieval to ensure relevance and support.

---

## 🏛️ High-Level Architecture

The system is composed of two main artifacts:

1.  **Janus Backend (`janus/`)**: A Python 3.11+ application using **FastAPI**, **LangGraph**, and **SQLAlchemy**.
    *   **Meta-Agent Supervisor**: Orchestrates the Monitor, Diagnose, Plan, Reflect, and Execute cycle.
    *   **Multi-Agent System**: Specialized workers (Coder, Architect, Reviewer) for execution.
    *   **Memory Systems**: Integration with Neo4j and Qdrant.
    *   **Sandboxed Execution**: Docker-based sandbox for safe code execution.

2.  **Janus Frontend (`front/`)**: An **Angular 20** application (Vite-based).
    *   **Real-time Interaction**: Chat interface with streaming thought processes.
    *   **Dashboard**: Visualization of goals, memory, and system health.
    *   **Professional UI**: Built with Tailwind CSS and modern design principles.

---

## 🚀 Getting Started

### Prerequisites

*   **Docker & Docker Compose**: For running infrastructure (Redis, Neo4j, Qdrant, RabbitMQ).
*   **Python 3.11+**: For the backend.
*   **Node.js 20+**: For the frontend.

### 1. Infrastructure Setup

Start the required services using Docker Compose from the root directory:

```bash
docker-compose up -d
```

This will start Redis, RabbitMQ, Neo4j, and Qdrant.

### 2. Backend Setup (`janus/`)

Navigate to the backend directory and install dependencies:

```bash
cd janus
# Recommended: Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

See [janus/README.md](janus/README.md) for detailed backend instructions.

### 3. Frontend Setup (`front/`)

Navigate to the frontend directory and install dependencies:

```bash
cd front
npm install

# Start the development server
npm start
```

The application will be available at `http://localhost:4200`.

See [front/README.md](front/README.md) for detailed frontend instructions.

---

## 🤝 Contributing

Please refer to the detailed documentation in `docs/` before contributing. Ensure you follow the code quality standards enforced by our pre-commit hooks.
