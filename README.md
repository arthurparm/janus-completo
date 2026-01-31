# Janus AI Architect

**Janus AI Architect** is an advanced AI system capable of multi-agent orchestration, complex reasoning, and software architecture generation. It leverages a hybrid memory architecture (episodic/vector + semantic/graph) and utilizes state-of-the-art techniques like GraphRAG, Reflection, and Language Agent Tree Search (LATS).

## 📚 Documentation

The root `docs/` directory acts as the central knowledge base for the project's status and inventory.

- **[🗺️ Roadmap & Strategy](docs/ROADMAP.md)**: Strategy, backlog, scientific foundation, and critical path for V1.
- **[📋 Inventory & Tasks](docs/INVENTORY.md)**: Detailed system inventory, API route listings, and technical task breakdowns.

## 🏗️ Project Structure

The repository is divided into two main components:

### 🐍 Backend (`janus/`)
The core logic, API, and agent orchestration.
- **Stack**: Python 3.11+, FastAPI, SQLAlchemy, LangGraph.
- **Setup**:
  ```bash
  cd janus
  pip install -r requirements.txt
  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
  ```

### 🎨 Frontend (`front/`)
The web interface for interacting with Janus.
- **Stack**: Angular 20, TailwindCSS.
- **Setup**:
  ```bash
  cd front
  npm install
  npm start
  ```

## 🚀 Getting Started

Please refer to the `README.md` files within the `janus/` and `front/` directories for specific setup and development instructions.
