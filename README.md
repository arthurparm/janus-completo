# Janus AI Architect

Janus AI Architect is a robust, scientific-grade agentic system designed to handle complex reasoning, planning, and execution tasks. It employs a hybrid architecture combining a modern Angular frontend with a powerful Python/FastAPI backend.

## Project Structure

The repository is organized into two main components:

- **`front/`**: The frontend application built with Angular 20. It provides the user interface for interacting with the Janus system.
- **`janus/`**: The backend application built with Python 3.11+ and FastAPI. It houses the core logic, agent orchestration, memory systems (Neo4j/Qdrant), and API endpoints.

## Getting Started

Please refer to the specific documentation for each component for detailed setup and running instructions:

- [**Frontend Documentation**](front/README.md) - Instructions for setting up and running the Angular application.
- [**Backend Documentation**](janus/README.md) - Instructions for setting up and running the Python backend.

## Architecture Highlights

- **Hybrid Agent Architecture**: Uses LangGraph for stateful multi-agent orchestration.
- **Dual Memory System**:
  - **Episodic Memory**: Vector-based (Qdrant) for fast retrieval.
  - **Semantic Memory**: Graph-based (Neo4j) for deep knowledge connections.
- **Reasoning Capabilities**: Implements advanced techniques like HyDE (Hypothetical Document Embeddings) and potentially LATS (Language Agent Tree Search).
- **Observability**: extensive monitoring and resilience features (Circuit Breakers, specialized monitoring).
