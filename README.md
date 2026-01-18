# Janus AI Architect

Janus is a sophisticated AI architecture designed for autonomous reasoning, planning, and execution. It leverages a hybrid memory system (Qdrant + Neo4j) and a multi-agent orchestrated workflow (LangGraph) to solve complex tasks.

## 🏗️ Architecture

The system is composed of two main components:

*   **[Backend (Janus)](./janus/README.md)**: Python/FastAPI application handling the core intelligence, memory management, and agent orchestration.
*   **[Frontend](./front/README.md)**: Angular 20 application providing the user interface for interaction, monitoring, and management.

### Key Components
*   **Reasoning**: Implements Graph of Thoughts (GoT) and Reflexion for robust decision making.
*   **Memory**: Hybrid architecture with Episodic (Vector/Qdrant) and Semantic (Graph/Neo4j) memory.
*   **RAG**: Native GraphRAG with HyDE (Hypothetical Document Embeddings).
*   **Resilience**: Circuit Breakers and Fallback mechanisms for LLM providers.

## 🚀 Quick Start

### Prerequisites
*   Docker & Docker Compose
*   Python 3.11+
*   Node.js 20+

### Running the System
Please refer to the component READMEs for detailed setup instructions:
- [Backend Setup](./janus/README.md)
- [Frontend Setup](./front/README.md)

## 📚 Documentation & Roadmap

*   **[System Inventory & Technical Debt](./docs/INVENTORY.md)**: Detailed tracking of API endpoints, known issues, and technical debt.
*   **[Backend Documentation](./janus/docs/)**: Specific technical documents for RAG, Resilience, etc.

---

## 🔬 Scientific Foundation (State-of-the-Art)

*Arquitetura baseada em 13+ papers seminais que fundamentam a inteligência do Janus.*

### 🧠 Reasoning & Planning
*   **Reflexion**: Loops de auto-correção.
*   **Graph of Thoughts (GoT)**: Orquestração não-linear.
*   **Chain of Thought (CoT)**: Padrão em prompts.

### 💾 Memory & Learning
*   **Generative Agents**: Memória com Recência, Importância e Relevância.
*   **Voyager**: Persistência de habilidades.

### 🔍 Retrieval & RAG
*   **HyDE**: Hypothetical Document Embeddings for better retrieval.
*   **Self-RAG**: Verification steps in retrieval.

---

## 🧪 Scientific Frontier (Post-V1 Evolution)

*   **Self-Evolving Toolset**: Agent creating its own tools.
*   **Swarm Intelligence**: Dynamic handoffs between agents.
*   **Active Memory Management**: Context window management strategies.

---

## 🏛️ Infrastructure Strategy

*   **Model Routing**: Using DeepSeek V3/R1 as the workhorse and Qwen 2.5 72B for architectural review.
*   **Budget & Rate Limiting**: Dual-wallet strategy to optimize costs.
*   **Privacy**: Strong stance on data privacy (avoiding data sharing for training unless necessary).
