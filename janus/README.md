# Janus — Backend (Python/FastAPI)

> 📘 **Documentação Principal**: Para arquitetura completa, roadmap, e detalhes do projeto, veja o [README Principal](../README.md).

Este diretório contém o backend do Janus, construído com Python (FastAPI), LangGraph, e serviços de IA.

## Setup Local

### Requisitos
- Python 3.11+
- Dependências de infraestrutura (PostgreSQL, Redis, Neo4j, Qdrant, RabbitMQ) rodando (via docker-compose na raiz).

### Instalação

```bash
cd janus
pip install -r requirements.txt
```

### Execução

```bash
# Iniciar servidor de desenvolvimento
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Para mais detalhes sobre a arquitetura de Agentes e estrutura de diretórios, consulte a documentação na raiz.
