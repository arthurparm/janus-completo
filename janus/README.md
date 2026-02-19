# Janus Backend (FastAPI + AI Workers)

Este diretório contém o código-fonte do backend do sistema Janus, construído com FastAPI e Python 3.11+. Ele é responsável pela API REST, orquestração de agentes de IA, memória (Neo4j/Qdrant) e workers assíncronos (RabbitMQ).

## 📋 Pré-requisitos

*   **Python 3.11+**
*   **Docker** (para rodar dependências como Postgres, Redis, RabbitMQ, Neo4j, Qdrant)

---

## 🚀 Configuração do Ambiente de Desenvolvimento

### 1. Criar Ambiente Virtual
Recomendamos o uso do `venv` nativo do Python:

```bash
# Linux/Mac
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 2. Instalar Dependências
```bash
pip install -r requirements.txt
```

### 3. Configurar Variáveis de Ambiente
Copie o exemplo (se existir) ou crie um arquivo `.env` dentro de `app/` (ou na raiz do `janus/`, dependendo de como o `config.py` carrega - padrão é `app/.env`):

```bash
cp app/.env.example app/.env
# Edite app/.env com suas chaves (OPENAI_API_KEY, etc.)
```

### 4. Subir Infraestrutura (Docker)
Para rodar apenas os bancos de dados e filas necessários para o backend local:

```bash
# Na raiz do monorepo (../)
docker compose up -d postgres redis rabbitmq neo4j qdrant
```

---

## ▶️ Executando a Aplicação

Para iniciar o servidor de desenvolvimento com auto-reload:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

A API estará disponível em:
*   **Swagger UI**: http://localhost:8000/docs
*   **ReDoc**: http://localhost:8000/redoc

---

## 🧪 Testes

O projeto utiliza `pytest` para testes unitários e de integração.

```bash
# Rodar todos os testes
pytest

# Rodar com cobertura
pytest --cov=app tests/
```

---

## 📂 Estrutura do Código

*   `app/api/`: Definição de rotas e endpoints (REST).
*   `app/core/`: Núcleo do sistema (Config, Workers, Infraestrutura).
*   `app/services/`: Lógica de negócio (Chat, LLM, Memória).
*   `app/repositories/`: Acesso a dados (SQL, Vetor, Grafo).
*   `app/models/`: Modelos de dados (Pydantic, SQLAlchemy).

Para mais detalhes sobre a arquitetura, consulte o **[Manual de Arquitetura](../docs/MANUAL_ARQUITETURA.md)** na raiz do projeto.
