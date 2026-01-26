# Janus

Janus is a **Meta-Agent Architecture** system designed for high-level software development and autonomy. It orchestrates specialized agents (Coder, Architect, Reviewer) using advanced reasoning patterns (OODA Loop, Graph of Thoughts) and memory systems (Episodic + Semantic).

## 📂 Repository Structure

*   **`front/`**: Angular 20 frontend application (Vite-based).
*   **`janus/`**: Python/FastAPI backend and Multi-Agent System.
*   **`docs/`**: Project documentation and roadmaps.

## 🚀 Getting Started

### Prerequisites
*   Python 3.11+
*   Node.js 20+
*   Docker & Docker Compose (for infrastructure like Neo4j, Qdrant, Redis, RabbitMQ)

### Backend Setup (`janus/`)

1.  Navigate to the backend directory:
    ```bash
    cd janus
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: If you encounter issues with `ag-ui-protocol`, refer to troubleshooting).*
3.  Start the server:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    The API documentation will be available at `http://localhost:8000/docs`.

### Frontend Setup (`front/`)

1.  Navigate to the frontend directory:
    ```bash
    cd front
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Start the development server:
    ```bash
    npm start
    ```
    Access the application at `http://localhost:4200`.

## 📖 Documentation

*   [**Roadmap & Strategy**](docs/ROADMAP.md): Project goals, backlog, and scientific foundations.
*   [**Inventory & Tasks**](docs/INVENTORY.md): Detailed system listings, route inventory, and maintenance tasks.

## 🧩 Architecture

Janus implements a cognitive architecture inspired by:
*   **OODA Loop**: Observe, Orient, Decide, Act.
*   **Memory**: Hybrid approach using Qdrant (Episodic/Vector) and Neo4j (Semantic/Graph).
*   **Planning**: Language Agent Tree Search (LATS) for simulating scenarios.
*   **Safety**: Constitutional AI principles enforced by a Reflector Agent.

## 🤝 Contributing

Please refer to the specific `README.md` files in `front/` and `janus/` for component-specific instructions.
