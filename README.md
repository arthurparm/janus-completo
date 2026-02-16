# Janus AI Architect

Janus is an advanced agentic system designed to orchestrate complex workflows, featuring a "Bicameral" memory architecture (Fast Thinking via Qdrant, Slow Thinking via Neo4j) and a Meta-Agent architecture for autonomous operation.

## Documentation

- **[Roadmap](./ROADMAP.md)**: Future plans and improvements.
- **[Detailed Documentation](./docs/)**: Architecture, API contracts, and guides.

## Repository Structure

- `front/`: Angular 20 frontend application.
- `janus/`: Python/FastAPI backend service.

## Getting Started

### Prerequisites

- **Python**: 3.11+ (< 3.13)
- **Node.js**: 20+
- **Docker**: Recommended for full stack deployment.

### Quick Start (Full Stack)

```bash
docker compose up -d
```

### Local Development

#### Frontend

```bash
cd front
npm install
npm start
```
Access at `http://localhost:4200`.

#### Backend

```bash
cd janus
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Access at `http://localhost:8000`.
