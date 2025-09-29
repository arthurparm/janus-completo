# Janus AI Architect

[![Python Version](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Janus** é uma aplicação de arquitetura de software de IA autônoma e modular, projetada para analisar bases de código, gerenciar conhecimento e executar tarefas de forma proativa. O sistema utiliza uma combinação de Grafos de Conhecimento, Memória Vetorial e Agentes de IA especializados para entender e operar sobre um ambiente de software.

## ✨ Principais Funcionalidades

-   **Arquitetura Modular**: O sistema é construído com uma clara separação de responsabilidades (`api`, `core`, `db`, `models`), facilitando a manutenção e a escalabilidade.
-   **Agentes de IA Especializados**: Utiliza diferentes tipos de agentes (`TOOL_USER`, `ORCHESTRATOR`, `META_AGENT`) com prompts e ferramentas distintas para realizar tarefas específicas com o princípio do menor privilégio.
-   **Ciclo de Autoanálise (Meta-Agente)**: Um agente supervisor monitora proativamente a saúde do sistema, analisando experiências passadas para detectar padrões de falha e sugerir correções.
-   **Grafo de Conhecimento (Neo4j)**: Realiza uma análise estática da base de código, mapeando arquivos, classes, funções e suas inter-relações (`CALLS`, `CONTAINS`) em um grafo de conhecimento.
-   **Memória Episódica (Qdrant)**: Armazena o histórico de ações e observações dos agentes como "experiências" em um banco de dados vetorial, permitindo buscas por similaridade semântica.
-   **Observabilidade Avançada**: Expõe métricas detalhadas para o Prometheus (latência, erros, estado de Circuit Breakers) e inclui um dashboard Grafana pré-configurado para visualização.
-   **Resiliência e Segurança**: Implementa padrões como Circuit Breaker para chamadas a serviços externos, Rate Limiting na API, validação de caminhos para prevenir *Path Traversal* e redação de segredos em logs.

## 🏗️ Arquitetura

O sistema é orquestrado em torno de uma API FastAPI que serve como ponto de entrada. As requisições são processadas pelo `AgentManager`, que seleciona o agente de IA apropriado com base na tarefa. Os agentes utilizam um conjunto de ferramentas (`agent_tools`) para interagir com os subsistemas principais:

1.  **LLM Manager**: Um roteador dinâmico que seleciona o modelo de linguagem (local via Ollama ou na nuvem como OpenAI/Gemini) com base em critérios de prioridade e função.
2.  **Knowledge Graph Core (Neo4j)**: A base de conhecimento de longo prazo sobre a estrutura do código.
3.  **Episodic Memory Core (Qdrant)**: A memória de curto e médio prazo sobre eventos e ações.
4.  **Filesystem Manager**: Uma camada segura para interações com o sistema de arquivos, restrita a um *workspace*.

```plaintext
                   +-------------------+
                   |   FastAPI (API)   |
                   +-------------------+
                           |
            +--------------+---------------+
            |        Agent Manager         |
            | (TOOL_USER, META_AGENT, etc.)|
            +--------------+---------------+
                           |
            +--------------+---------------+
            |         LLM Manager          |
            | (Router: Ollama, OpenAI, ...) |
            +------------------------------+
                           |
      +--------------------+--------------------+
      |                    |                    |
+-----+------+      +------+-----+       +------+-------+
| Knowledge  |      | Episodic   |       | Filesystem   |
| Graph Core |      | Memory Core|       | Manager      |
|  (Neo4j)   |      |  (Qdrant)  |       | (Workspace)  |
+------------+      +------------+       +--------------+
```

## 🚀 Começando

### Pré-requisitos

- Docker
- Docker Compose

### Instalação e Configuração

1.  **Clone o repositório:**
    ```bash
    git clone <URL_DO_REPOSITORIO>
    cd janus-1.0
    ```

2.  **Crie o arquivo de ambiente:**
    Copie o arquivo de exemplo para criar seu ambiente local.
    ```bash
    cp .env.example .env
    ```
    Agora, edite o arquivo `.env` e preencha as credenciais necessárias, como `OPENAI_API_KEY` ou `GEMINI_API_KEY`. As configurações padrão para Neo4j, Qdrant e Ollama já estão definidas para o ambiente Docker.

3.  **Inicie os serviços:**
    Use o Docker Compose para construir as imagens e iniciar todos os contêineres em modo detached.
    ```bash
    docker-compose up -d --build
    ```
    Isso iniciará a API do Janus, o banco de dados Neo4j, o banco vetorial Qdrant e o servidor local de LLMs Ollama.

## ⚙️ Uso da Aplicação

Após a inicialização, os seguintes serviços estarão disponíveis:

-   **API do Janus**: `http://localhost:8000`
-   **Documentação da API (Swagger UI)**: `http://localhost:8000/docs`
-   **Painel do Neo4j Browser**: `http://localhost:7474`
-   **API do Ollama**: `http://localhost:11434`
-   **Métricas do Prometheus**: `http://localhost:8000/metrics`

### Exemplos de Requisições

1.  **Verificar o Status do Sistema**
    Confirma se a aplicação está operacional.
    ```bash
    curl -X GET "http://localhost:8000/api/v1/system/status"
    ```

2.  **Indexar a Base de Código**
    Dispara o processo de análise do código-fonte para popular o Grafo de Conhecimento.
    ```bash
    curl -X POST "http://localhost:8000/api/v1/knowledge/index" -H "Content-Type: application/json" -d '{}'
    ```

3.  **Executar um Agente**
    Envia uma instrução para um agente executar uma tarefa. Neste exemplo, o agente escreve um arquivo no workspace.
    ```bash
    curl -X POST "http://localhost:8000/api/v1/agent/execute" \
    -H "Content-Type: application/json" \
    -d '{
      "question": "Crie um arquivo chamado '\''exemplo.txt'\'' e escreva o texto '\''Olá, Janus!'\'' nele.",
      "agent_type": "tool_user"
    }'
    ```

## 📊 Observabilidade

-   **Métricas**: Todas as métricas da aplicação são expostas no endpoint `http://localhost:8000/metrics` e podem ser coletadas por um servidor Prometheus.
-   **Dashboard**: Um dashboard pré-configurado para Grafana está disponível em `dashboards/janus_component_resilience_dashboard.json`. Ele monitora a latência, taxa de erros e o estado dos Circuit Breakers dos componentes.

## 📁 Estrutura do Projeto

```
.
├── app/                  # Código fonte da aplicação
│   ├── api/              # Módulos da API (endpoints, routers)
│   ├── core/             # Lógica de negócio principal (agentes, memória, etc.)
│   ├── db/               # Abstrações de banco de dados (graph, vector_store)
│   ├── models/           # Esquemas de dados Pydantic
│   └── main.py           # Ponto de entrada da aplicação FastAPI
├── dashboards/           # Dashboards Grafana
├── http/                 # Coleção de requisições para testes manuais
├── .env.example          # Arquivo de exemplo para variáveis de ambiente
├── docker-compose.yml    # Orquestração dos serviços
├── Dockerfile            # Definição da imagem da aplicação
└── requirements.txt      # Dependências Python
```

## 🤝 Contribuições

Contribuições são bem-vindas! Sinta-se à vontade para abrir uma issue para relatar bugs ou sugerir novas funcionalidades. Se desejar contribuir com código, por favor, abra um Pull Request.

Áreas que precisam de ajuda:

-   Expansão da suíte de testes de unidade.
-   Melhoria da documentação de código.
-   Criação de novos `agent_tools`.
