# Janus

Janus is an advanced AI Architect platform designed to orchestrate multi-agent systems, manage complex reasoning tasks, and provide a seamless interface for AI-driven development.

## Project Structure

The project is divided into two main components:

*   **`janus/` (Backend)**: A Python-based backend using FastAPI, SQLAlchemy, and LangGraph for agent orchestration.
*   **`front/` (Frontend)**: An Angular 20 application providing the user interface.

## Prerequisites

*   **Backend**: Python 3.11+
*   **Frontend**: Node.js 20+
*   **Infrastructure**: Docker (optional, for running dependencies like Neo4j, Qdrant, Redis, RabbitMQ)

## Getting Started

### Backend (`janus/`)

1.  Navigate to the backend directory:
    ```bash
    cd janus
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: If you encounter issues with `ag-ui-protocol`, refer to the troubleshooting guide or remove it temporarily.*
3.  Run the server:
    ```bash
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    The API will be available at `http://localhost:8000`.

### Frontend (`front/`)

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
    The application will be available at `http://localhost:4200`.

## Documentation

*   **Backend Documentation**: See `janus/docs/` for technical details on RAG, resilience, and other backend subsystems.
*   **Frontend Documentation**: See `front/README.md` for specific frontend guidelines.
*   **System Inventory**: See `docs/INVENTORY.md` (if available) for system listings.
*   **Roadmap**: See `docs/ROADMAP.md` (if available) for strategy and backlog.
