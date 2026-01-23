# Janus AI Architect

Janus is a **Meta-Agent Architecture** designed to orchestrate intelligent systems, capable of advanced reasoning, long-term planning, and autonomous execution. It combines state-of-the-art LLMs with graph-based memory (GraphRAG) and a multi-agent ecosystem.

**Documentation**:
- [Roadmap & Technical Debt](docs/ROADMAP.md)
- [System Inventory & API Surveys](docs/INVENTORY.md)
- [Backend Documentation](janus/docs/)

---

## 🔬 Scientific Foundations

*Architecture based on seminal papers that ground Janus's intelligence.*

### 🧠 Reasoning & Planning (The Brain)

*   **LATS (Language Agent Tree Search)** - *Zhou et al., 2023*
    *   **Concept**: Combines LLM with Monte Carlo Tree Search (MCTS) to explore multiple solution paths.
    *   **In Janus**: `Planner` node simulating scenarios before executing critical actions (e.g., deploy).
*   **Reflexion** - *Shinn et al., 2023*
    *   **Concept**: Agents that verbalize errors and keep lessons in short-term memory.
    *   **In Janus**: Self-correction loop in `CoderAgent` for compilation errors.
*   **Graph of Thoughts (GoT)** - *Besta et al., 2023*
    *   **Concept**: Models thought as a graph (DAG), allowing combining and refining ideas.
    *   **In Janus**: Non-linear orchestration in LangGraph (Supervisor Node).
*   **Tree of Thoughts (ToT)** - *Yao et al., 2023*
    *   **Concept**: Deliberate exploration of multiple reasoning branches.
    *   **In Janus**: Basis for the `Meta-Agent` decision process.
*   **Chain of Thought (CoT)** - *Wei et al., 2022*
    *   **Concept**: "Let's think step by step".
    *   **In Janus**: Mandatory pattern in all system prompts.

### 💾 Memory & Learning (The Soul)

*   **Generative Agents** - *Park et al., 2023*
    *   **Concept**: Memory with Recency, Importance, and Relevance + "Dream" (Consolidation).
    *   **In Janus**: `MemoryService` architecture and nightly consolidation worker in Neo4j.
*   **MemGPT** - *Packer et al., 2023*
    *   **Concept**: Infinite context management via pagination (OS-like memory management).
    *   **In Janus**: Context pagination strategy for long conversations.
*   **Voyager** - *Wang et al., 2023*
    *   **Concept**: Continuous learning via Skill Library.
    *   **In Janus**: Persistence of successful tools and scripts for reuse.

### 🔍 Retrieval & RAG (The Knowledge)

*   **Self-RAG** - *Asai et al., 2023*
    *   **Concept**: The model critiques its own retrieval (`[IsREL]`, `[IsSUP]`).
    *   **In Janus**: `NativeGraphRAG` pipeline with verification step.
*   **HyDE (Hypothetical Document Embeddings)** - *Gao et al., 2022*
    *   **Concept**: Generate hypothetical ideal response to search for similar documents.
    *   **In Janus**: Improvement in Qdrant vector search.
*   **RAPTOR** - *Sarthi et al., 2024*
    *   **Concept**: Recursive tree indexing (summaries of summaries).
    *   **In Janus**: Hierarchical knowledge structure in Neo4j.

### 🤖 Multi-Agent (The Body)

*   **MetaGPT** - *Hong et al., 2023*
    *   **Concept**: SOPs (Standard Operating Procedures) encoded for agents.
    *   **In Janus**: Rigid role definition (Product Manager, Architect, Engineer).
*   **CAMEL** - *Li et al., 2023*
    *   **Concept**: "Role-Playing" architecture for communicative agents.
    *   **In Janus**: Communication protocol between Supervisor and Workers.

### 🛡️ Safety & Alignment (The Conscience)

*   **Constitutional AI** - *Bai et al., 2022 (Anthropic)*
    *   **Concept**: Behavior control through a "Constitution" (natural rules) instead of extensive manual RLHF.
    *   **In Janus**: Extension of `ReflectorAgent` to validate outputs against security rules (`security.yaml`) before delivery.

### ⚡ Optimization & Economy (The Efficiency)

*   **FrugalGPT (LLM Cascades)** - *Chen et al., 2023*
    *   **Concept**: Call smaller/cheaper models first; scale to SOTA models only if confidence is low.
    *   **In Janus**: `ModelRouter` in infrastructure attempting to solve with Llama-3-Local/Mini before calling DeepSeek/GPT-4.
*   **DSPy (Programming with Prompts)** - *Khattab et al., 2023*
    *   **Concept**: Abstract prompts as optimizable parameters. The system "compiles" and improves its own prompts based on metrics.
    *   **In Janus**: Auto-tuning pipeline for Worker prompts based on error/success feedback.

### 🎨 HCI & Experience (The Interface)

*   **Generative UI** - *Vercel AI SDK v5 / Dynaboard*
    *   **Concept**: UI generated dynamically by the LLM to adapt to user intent (tables, charts, forms on-the-fly).
    *   **In Janus**: Use of `Angular Dynamic Components` + `ViewContainerRef` to render visual components based on tool-calls.

---

## 🏛️ Architecture Overview

The system is divided into two main components:

### Backend (`janus/`)
*   **Stack**: Python 3.11+, FastAPI, SQLAlchemy, LangGraph.
*   **Memory**: Hybrid architecture with Qdrant (Episodic/Vector) and Neo4j (Semantic/Graph).
*   **Architecture**: Layered (Repositories, Services, Core).
*   **Agents**: Multi-agent system orchestrated by a Supervisor using OODA loops.

### Frontend (`front/`)
*   **Stack**: Angular 20, Tailwind CSS.
*   **Build**: Vite (`@angular/build:application`).
*   **Communication**: Proxied requests to backend, SSE for real-time thought streams.

---

## 🚀 Getting Started

### Prerequisites
*   Python 3.11+
*   Node.js 20+
*   Docker (for database services)

### Backend Setup
```bash
cd janus
pip install -r requirements.txt
# See janus/README.md (if available) or docs/ for detailed setup
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup
```bash
cd front
npm install
npm start
# App running at http://localhost:4200
```
