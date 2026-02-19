# Manual de Arquitetura do Sistema Janus

**Versão:** 1.0
**Data:** 11/02/2026
**Idioma:** Português (PT-BR)

## 1. Visão Geral

O Janus é um sistema agêntico avançado projetado para atuar como um arquiteto de software autônomo e assistente inteligente. Ele opera como um monorepo dividido em duas partes principais:

*   **Frontend (`front/`)**: Uma Single Page Application (SPA) moderna construída em Angular 20.
*   **Backend (`janus/`)**: Uma API robusta em Python (FastAPI) baseada em microsserviços lógicos e workers assíncronos.

O sistema utiliza uma arquitetura orientada a eventos para garantir escalabilidade, resiliência e capacidade de processamento paralelo de tarefas complexas (como geração de código, consolidação de memória e raciocínio profundo).

---

## 2. Arquitetura Frontend (`front/`)

O frontend é a interface de operação do Janus, permitindo interação via chat, monitoramento de observabilidade e gestão de ferramentas.

### 2.1. Stack Tecnológico
*   **Framework**: Angular 20 (focado em performance com Signals e Zoneless Change Detection).
*   **Linguagem**: TypeScript.
*   **Estilização**: SCSS + TailwindCSS + Angular Material.
*   **Comunicação**: HTTP Client (REST) e EventSource (Server-Sent Events para streaming).
*   **Gerenciamento de Estado**: Angular Signals (reatividade fina).

### 2.2. Estrutura de Módulos
A aplicação é modularizada em `features`:
*   **Conversations (`features/conversations`)**: O núcleo da interação. Gerencia o chat, histórico, streaming de respostas e exibição de artefatos (código, documentos).
*   **Observability (`features/observability`)**: Dashboards para monitorar métricas do sistema, status dos workers e saúde da infraestrutura.
*   **Tools (`features/tools`)**: Interface para gestão e execução manual de ferramentas e scripts.
*   **Auth (`features/auth`)**: Gestão de autenticação e registro de usuários.

### 2.3. Fluxo de Dados no Frontend
1.  **Interação**: O usuário envia uma mensagem no componente `ConversationsComponent`.
2.  **Envio**: O `JanusApiService` envia a mensagem via POST para a API.
3.  **Streaming**: O `ChatStreamService` abre uma conexão SSE (`/api/v1/chat/stream/{id}`) para receber tokens em tempo real, pensamentos do agente e eventos de sistema.
4.  **Estado**: As atualizações (novas mensagens, status de typing) são propagadas via Signals para a UI, garantindo renderização eficiente sem zone pollution.

---

## 3. Arquitetura Backend (`janus/`)

O backend é o cérebro do sistema, orquestrando múltiplos modelos de IA, memória de longo prazo e execução de código.

### 3.1. Stack Tecnológico
*   **Framework**: FastAPI (Python 3.11+).
*   **Banco de Dados Relacional**: PostgreSQL (via SQLAlchemy) para dados estruturados (usuários, configurações).
*   **Banco de Dados Vetorial**: Qdrant para memória episódica (busca semântica).
*   **Banco de Dados de Grafo**: Neo4j para memória semântica (Knowledge Graph).
*   **Mensageria**: RabbitMQ para comunicação assíncrona entre serviços e workers.
*   **Cache**: Redis para rate limiting e cache de respostas LLM.
*   **Orquestração de IA**: LangChain e LangGraph.

### 3.2. Camadas do Sistema (`janus/app/`)
1.  **API Layer (`api/`)**: Controladores REST que recebem requisições, validam input (Pydantic) e delegam para serviços.
2.  **Service Layer (`services/`)**: Contém a regra de negócio. Ex: `ChatService`, `LLMService`, `MemoryService`.
3.  **Core Layer (`core/`)**: O coração do sistema.
    *   **Workers**: Processos em background que consomem filas do RabbitMQ.
    *   **LLM**: Abstração de múltiplos provedores (OpenAI, Anthropic, DeepSeek, Ollama, etc.).
    *   **Memory**: Lógica de indexação e recuperação (RAG Híbrido).
4.  **Repository Layer (`repositories/`)**: Abstração de acesso a dados (SQL, Vetor, Grafo).

### 3.3. Sistema de Workers e Filas
O Janus utiliza intensamente o RabbitMQ para desacoplar processos pesados. Os principais workers (definidos em `app/core/workers/orchestrator.py`) incluem:

*   **`agent_tasks_worker`**: Processa tarefas genéricas de agentes.
*   **`code_agent_worker`**: Especialista em geração de código (com loop de auto-correção de sintaxe).
*   **`codex_worker`**: Executor de ferramentas de CLI e manipulação de arquivos.
*   **`knowledge_consolidator_worker`**: Transforma memória episódica (conversas passadas) em nós de conhecimento no grafo (Neo4j).
*   **`neural_training_worker`**: (Experimental) Responsável por ajuste fino ou treinamento de modelos leves.
*   **`reflexion_worker`**: Analisa falhas e sucessos para melhorar o comportamento futuro.
*   **`meta_agent_worker`**: Supervisiona o sistema e planeja ações de longo prazo.

---

## 4. Fluxo de Processamento de Mensagem

1.  **Recepção**: A API recebe o POST `/chat`.
2.  **Orquestração**: O `ChatService` invoca o `OrchestratorAgent`.
3.  **Recuperação (RAG)**:
    *   O sistema busca contexto relevante no Qdrant (vetores) e Neo4j (grafo).
    *   Utiliza HyDE (Hypothetical Document Embeddings) para melhorar a busca.
4.  **Raciocínio**: O LLM gera uma resposta ou decide usar uma ferramenta.
5.  **Ação Assíncrona (Opcional)**: Se for necessário gerar código complexo ou consolidar conhecimento, uma mensagem é publicada no RabbitMQ.
6.  **Resposta**: A resposta final é enviada via SSE para o frontend.

---

## 5. Subsistemas Críticos

### 5.1. Memória Bicameral
O Janus implementa um sistema de memória inspirado na cognição humana:
*   **Sistema 1 (Rápido/Episódico)**: Qdrant armazena logs de chat e vetores para recuperação rápida por similaridade.
*   **Sistema 2 (Lento/Semântico)**: Neo4j armazena fatos, relações e entidades extraídas das conversas pelo `KnowledgeConsolidator`.

### 5.2. Autonomia e Planejamento
O sistema possui um loop OODA (Observe, Orient, Decide, Act) implementado através de agentes de autonomia que podem operar sem intervenção humana direta, perseguindo objetivos (`Goals`) definidos.

### 5.3. Observabilidade
O sistema exporta métricas (Prometheus) e traces (OpenTelemetry) para monitorar:
*   Latência de LLM.
*   Uso de tokens e custo.
*   Saúde das filas RabbitMQ.
*   Taxas de erro e Circuit Breakers.

---

## 6. Diagrama de Integração Simplificado

```mermaid
graph TD
    User[Usuário (Frontend)] -->|REST/SSE| API[Janus API (FastAPI)]
    API -->|Leitura/Escrita| DB[(Postgres)]
    API -->|Publica Tarefa| MQ[RabbitMQ]

    subgraph "Workers & Agentes"
        MQ -->|Consome| W_Code[Code Agent Worker]
        MQ -->|Consome| W_Know[Knowledge Consolidator]
        MQ -->|Consome| W_Meta[Meta Agent]
    end

    subgraph "Memória & Conhecimento"
        API <-->|Busca Vetorial| Qdrant[(Qdrant)]
        API <-->|Busca Grafo| Neo4j[(Neo4j)]
        W_Know -->|Grava| Neo4j
    end

    subgraph "LLM Providers"
        API <-->|Infeferência| LLM[OpenAI / DeepSeek / Ollama]
        W_Code <-->|Infeferência| LLM
    end
```
