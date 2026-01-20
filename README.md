# Janus AI Architect

**Janus** is an advanced AI Architect system designed to operate as a strategic supervisor and autonomous developer. It leverages a hybrid agentic architecture, combining **LangGraph** for orchestration, **Neo4j** for semantic memory (Knowledge Graph), and **Qdrant** for episodic memory (Vector Database).

The system implements a **Meta-Agent** architecture capable of Monitor, Diagnose, Plan, Reflect, and Execute cycles, operating distinct from the operational Autonomy Loop.

## 📚 Documentation

*   **[Roadmap & Critical Path](docs/ROADMAP.md)**: Current status, backlog, and V1 launch blockers.
*   **[System Inventory](docs/INVENTORY.md)**: Detailed API inventory, route listings, and technical debt analysis.
*   **[Backend (Janus)](janus/README.md)**: Python/FastAPI application setup.
*   **[Frontend (Angular)](front/README.md)**: Angular application setup.

## 🏗️ Architecture Overview

The system is split into two main components:
*   **Frontend (`front/`)**: An Angular 20 application providing the user interface for interaction, visualization of thought streams, and system management.
*   **Backend (`janus/`)**: A Python 3.11+ FastAPI application serving as the brain, handling the Meta-Agent logic, LLM interactions, and database operations.

## 🔬 Scientific Foundation (State-of-the-Art)

The Janus architecture is grounded in 13+ seminal papers that fundament its intelligence and reasoning capabilities.

### 🧠 Reasoning & Planning (The Brain)

*   **Reflexion** (*Shinn et al., 2023*): Agents that verbalize errors and store lessons in short-term memory. Implemented as a self-correction loop in `CoderAgent`.
*   **Graph of Thoughts (GoT)** (*Besta et al., 2023*): Models thought as a graph (DAG), allowing combining and refining ideas. Implemented in the LangGraph Supervisor Node.
*   **Chain of Thought (CoT)** (*Wei et al., 2022*): "Let's think step by step". Mandatory pattern in all system prompts.
*   *(Planned)* **LATS (Language Agent Tree Search)** (*Zhou et al., 2023*): Combines LLM with MCTS to explore multiple solution paths.
*   *(Planned)* **Tree of Thoughts (ToT)** (*Yao et al., 2023*): Deliberate exploration of multiple reasoning branches.

### 💾 Memory & Learning (The Soul)

*   **HyDE (Hypothetical Document Embeddings)** (*Gao et al., 2022*): Generates hypothetical ideal answers to search for similar documents. Improves Qdrant vector search.
*   *(Planned)* **Generative Agents** (*Park et al., 2023*): Memory with Recency, Importance, and Relevance + Consolidation ("Dreaming").
*   *(Planned)* **MemGPT** (*Packer et al., 2023*): Infinite context management via pagination (OS-like memory management).
*   *(Planned)* **Voyager** (*Wang et al., 2023*): Continuous learning via Skill Library (persistence of successful tools/scripts).

### 🔍 Retrieval & RAG (The Knowledge)

*   *(Planned)* **Self-RAG** (*Asai et al., 2023*): The model critiques its own retrieval (`[IsREL]`, `[IsSUP]`).
*   *(Planned)* **RAPTOR** (*Sarthi et al., 2024*): Recursive tree indexing (summaries of summaries) in Neo4j.

### 🤖 Multi-Agent (The Body)

*   *(Planned)* **MetaGPT** (*Hong et al., 2023*): Standard Operating Procedures (SOPs) encoded for agents (PM, Architect, Engineer).
*   *(Planned)* **CAMEL** (*Li et al., 2023*): Role-playing architecture for communicative communication.

### 🛡️ Safety & Alignment (The Conscience)

*   *(Planned)* **Constitutional AI** (*Bai et al., 2022*): Behavior control through a "Constitution" (natural rules) enforced by `ReflectorAgent`.

### ⚡ Optimization & Economy (The Efficiency)

*   *(Planned)* **FrugalGPT** (*Chen et al., 2023*): Call smaller/cheaper models first; scale to SOTA models only if confidence is low (`ModelRouter`).
*   *(Planned)* **DSPy** (*Khattab et al., 2023*): Abstract prompts as optimizable parameters.

### 🎨 HCI & Experience (The Interface)

*   *(Planned)* **Generative UI** (*Vercel AI SDK v5*): UI generated dynamically by LLM to adapt to user intent (using Angular Dynamic Components).

## 🚀 Getting Started

### Prerequisites

*   **Docker & Docker Compose**: For running infrastructure (Neo4j, Qdrant, Redis, RabbitMQ).
*   **Python 3.11+**: For the backend.
*   **Node.js 20**: For the frontend.

### Quick Setup

1.  **Start Infrastructure**:
    ```bash
    docker-compose up -d
    ```

2.  **Start Backend**:
    See [janus/README.md](janus/README.md) for details.
    ```bash
    cd janus
    pip install -r requirements.txt
    uvicorn app.main:app --host 0.0.0.0 --port 8000
    ```

3.  **Start Frontend**:
    See [front/README.md](front/README.md) for details.
    ```bash
    cd front
    npm install
    npm start
    ```

## License

[MIT](LICENSE)
