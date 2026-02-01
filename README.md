# Janus

**Janus** is an advanced AI Architect platform designed to orchestrate multi-agent systems, manage complex reasoning tasks, and provide a robust interface for AI-driven development.

## 📂 Project Structure

This repository is organized into the following components:

*   **[`janus/`](janus/)**: The Backend application (Python/FastAPI). Handles the core logic, agents, memory (Qdrant/Neo4j), and API endpoints.
*   **[`front/`](front/)**: The Frontend application (Angular 20). Provides the web interface for interacting with Janus.
*   **[`docs/`](docs/)**: Project documentation, roadmap, and technical inventories.

## 📖 Documentation

*   **[Roadmap & Strategy](docs/ROADMAP.md)**: Strategic vision, backlog, and scientific foundations.
*   **[Inventory & Tasks](docs/INVENTORY.md)**: Detailed technical inventory of endpoints and pending tasks.
*   **[Frontend Documentation](docs/FRONTEND.md)**: Specific details about the Angular frontend.

## 🚀 Getting Started

Please refer to the `README.md` files in each component directory for specific setup instructions:

*   **Backend**: [janus/README.md](janus/README.md)
*   **Frontend**: [front/README.md](front/README.md)

## 🏗️ Architecture

Janus follows a **Single Source of Truth (SSOT)** architecture where this repository serves as the central point for code and documentation.

### Core Technologies
*   **Backend**: Python 3.11+, FastAPI, LangGraph, PydanticAI, SQLAlchemy.
*   **Frontend**: Angular 20, Vite, TailwindCSS.
*   **Memory**: Neo4j (Graph), Qdrant (Vector), Redis (State).
*   **Infrastructure**: Docker, RabbitMQ.

---
*Generated for Janus Project.*
