# Manual de Operação e Instalação do Janus

**Versão:** 1.0
**Data:** 11/02/2026
**Idioma:** Português (PT-BR)

Este manual descreve como instalar, configurar e operar o sistema Janus em ambientes locais e de servidor.

---

## 1. Pré-requisitos

Antes de começar, certifique-se de ter as seguintes ferramentas instaladas:

*   **Docker Desktop** (ou Docker Engine + Docker Compose Plugin) - *Essencial*
*   **Git** - Para clonar o repositório.

Para desenvolvimento local (sem rodar tudo em containers), você também precisará:
*   **Python 3.11+**
*   **Node.js 20+**

---

## 2. Instalação Rápida (Recomendada)

A maneira mais fácil de rodar o Janus completo é utilizando o Docker Compose. Isso sobe o frontend, backend, bancos de dados e sistemas de observabilidade.

### Passo 1: Clonar o Repositório
```bash
git clone <url-do-repositorio>
cd janus-completo
```

### Passo 2: Configurar Variáveis de Ambiente
O sistema vem com defaults funcionais, mas para usar LLMs externos (OpenAI, DeepSeek), você precisa configurar suas chaves.

1.  Navegue até `janus/app`.
2.  Crie ou edite o arquivo `.env` (baseado em algum exemplo se houver, ou crie do zero).
3.  Adicione suas chaves:
    ```env
    OPENAI_API_KEY=sk-...
    DEEPSEEK_API_KEY=sk-...
    # Se usar OpenRouter
    OPENROUTER_API_KEY=sk-...
    ```

### Passo 3: Iniciar o Sistema
Na raiz do projeto (onde está o `docker-compose.yml`):

```bash
docker compose up -d
```

Este comando irá baixar as imagens e iniciar os serviços:
*   `janus-api`: Backend na porta **8000**.
*   `front`: Frontend na porta **4200** (ou 80 dependendo da config do Nginx/Angular).
*   `postgres`, `redis`, `rabbitmq`, `neo4j`, `qdrant`: Infraestrutura de dados.
*   `prometheus`, `grafana`: Observabilidade.

### Passo 4: Acessar
*   **Frontend**: [http://localhost:4200](http://localhost:4200) (ou porta configurada no compose)
*   **API Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **Grafana**: [http://localhost:3000](http://localhost:3000) (admin/admin)
*   **RabbitMQ Management**: [http://localhost:15672](http://localhost:15672) (guest/guest)

---

## 3. Instalação para Desenvolvimento Local (Híbrida)

Para desenvolvedores que desejam alterar o código frequentemente, recomenda-se rodar a infraestrutura (BDs) no Docker e as aplicações (Front/Back) nativamente.

### 3.1. Subir Infraestrutura
Comente ou remova os serviços `janus-api` e `front` do `docker-compose.yml` (ou use um perfil, se configurado), e suba o resto:

```bash
docker compose up -d postgres redis rabbitmq neo4j qdrant
```

### 3.2. Configurar Backend (Python)
1.  Entre na pasta `janus`:
    ```bash
    cd janus
    ```
2.  Crie um ambiente virtual:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    # ou
    venv\Scripts\activate     # Windows
    ```
3.  Instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```
4.  Rode a API:
    ```bash
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ```

### 3.3. Configurar Frontend (Angular)
1.  Entre na pasta `front`:
    ```bash
    cd front
    ```
2.  Instale as dependências:
    ```bash
    npm install
    ```
3.  Inicie o servidor de desenvolvimento:
    ```bash
    npm start
    ```
4.  Acesse em [http://localhost:4200](http://localhost:4200).

---

## 4. Configuração e Variáveis de Ambiente

As configurações principais residem em `janus/app/config.py` e são sobrescritas pelo `.env`.

| Variável | Descrição | Padrão |
|---|---|---|
| `OPENAI_API_KEY` | Chave da OpenAI | N/A |
| `NEO4J_URI` | Endereço do Neo4j | bolt://localhost:7687 |
| `QDRANT_HOST` | Host do Qdrant | localhost |
| `RABBITMQ_HOST` | Host do RabbitMQ | localhost |
| `LLM_ECONOMY_POLICY` | Política de custos (strict, balanced, quality) | balanced |
| `PUBLIC_API_KEY` | (Opcional) Protege a API com chave estática | None |

> **Nota**: Para ambientes Docker, os hosts geralmente são os nomes dos serviços (`postgres`, `redis`, etc.), enquanto localmente são `localhost`. O `config.py` tenta gerenciar isso, mas verifique seu `.env`.

---

## 5. Operação Básica e Troubleshooting

### Ver Logs
Para ver logs de todos os containers:
```bash
docker compose logs -f
```
Para um serviço específico (ex: API):
```bash
docker compose logs -f janus-api
```

### Reiniciar um Serviço
Se o backend travar ou precisar de restart limpo:
```bash
docker compose restart janus-api
```

### Limpeza de Dados
Para resetar todo o sistema (cuidado: apaga bancos de dados!):
```bash
docker compose down -v
```

### Problemas Comuns

1.  **Portas em uso**:
    *   Erro: `Bind for 0.0.0.0:8000 failed: port is already allocated`.
    *   Solução: Pare o processo que está usando a porta ou altere o mapeamento no `docker-compose.yml`.

2.  **Erro de Conexão com DB/RabbitMQ no Startup**:
    *   Causa: Os containers de infra ainda não estão prontos quando a API sobe.
    *   Solução: A API possui mecanismos de retry, mas pode falhar se demorar muito. Reinicie a API: `docker compose restart janus-api`.

3.  **Erro de LLM (Rate Limit/Quota)**:
    *   Verifique os logs da API. Se houver erro 429 da OpenAI/Anthropic, verifique seus créditos e limites no painel do provedor.
