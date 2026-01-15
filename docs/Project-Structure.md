# Janus — Organização do Projeto (Atualizado)

Este documento descreve a estrutura, nomenclatura e o mapeamento lógico dos ~750 arquivos do projeto, facilitando a navegação e o entendimento da arquitetura descrita no [README.md](../README.md).

## Visão Geral da Estrutura

```
/ (raiz)
├─ README.md                      # Manual completo e ponto de entrada
├─ ROADMAP.md                     # Planejamento estratégico e débito técnico
├─ docker-compose.yml             # Orquestração de containers (API, Front, BDs)
├─ front/                         # Aplicação Angular (Interface do Usuário)
├─ janus/                         # Backend Python (Cérebro do Sistema)
│  ├─ app/                        # Código-fonte da aplicação
│  │  ├─ api/                     # Interface HTTP (FastAPI Endpoints)
│  │  ├─ core/                    # Núcleo da lógica agêntica e infraestrutura
│  │  ├─ services/                # Camada de aplicação e regras de negócio
│  │  ├─ repositories/            # Acesso a dados (Neo4j, Qdrant, MySQL)
│  │  ├─ models/                  # Definições de tipos (Pydantic) e esquemas
│  │  ├─ config.py                # Configuração centralizada
│  │  └─ main.py                  # Entrypoint, lifecycle e composição
│  └─ tests/                      # Testes automatizados
└─ docs/                          # Documentação técnica detalhada
```

---

## Mapeamento Lógico: Onde encontrar o quê?

Esta seção conecta os conceitos arquiteturais do Manual (`README.md`) aos arquivos físicos.

### 1. Orquestração e API (A Porta de Entrada)
Responsável por receber requisições, autenticar e despachar para serviços.
- **Entrypoint**: `janus/app/main.py` (Inicia API, conecta BDs, sobe workers).
- **Rotas**: `janus/app/api/v1/endpoints/`
  - `chat.py`: Endpoints de conversa e streaming.
  - `llm.py`: Invocação direta de modelos.
  - `autonomy.py`: Controle do loop autônomo.
  - `tasks.py` / `workers.py`: Gestão de tarefas assíncronas.

### 2. O Cérebro (LLM & Roteamento)
Onde a decisão de qual modelo usar acontece, controle de custos e resiliência.
- **Roteamento e Seleção**: `janus/app/core/llm/router.py` (Lógica FAST/CHEAP vs HIGH/QUALITY).
- **Gestão de Ciclo de Vida**: `janus/app/core/llm/llm_manager.py` (Cache, Circuit Breaker, Budgets).
- **Clientes**: `janus/app/core/llm/client.py` (Abstração sobre OpenAI/Anthropic/Ollama).

### 3. Memória e Conhecimento (Hot Path & Cold Path)
Como o Janus lembra e aprende.
- **Hot Path (Vetor Rápido)**:
  - `janus/app/core/memory/memory_core.py`: Gravação imediata no Qdrant.
  - `janus/app/services/memory_service.py`: Busca e contexto de curto prazo.
- **Cold Path (Consolidação em Grafo)**:
  - `janus/app/core/workers/knowledge_consolidator_worker.py`: Worker que processa memórias em background.
  - `janus/app/core/memory/graph_guardian.py`: Normalização de entidades para o Neo4j.
  - `janus/app/services/knowledge_service.py`: Lógica de alto nível do grafo.
- **Documentos & RAG**:
  - `janus/app/services/document_service.py`: Ingestão, chunking e indexação.
  - `janus/app/core/memory/graph_rag_core.py`: Lógica de RAG híbrido.

### 4. Autonomia e Agentes (Policy & Tools)
Onde o sistema age sobre o mundo.
- **Meta-Agente (O Supervisor)**:
  - `janus/app/core/agents/meta_agent.py`: Implementação do grafo de estado (LangGraph) OODA.
  - `janus/app/core/agents/meta_agent_worker.py`: Worker que roda ciclos do meta-agente.
- **Parlamento (Multi-Agentes)**:
  - `janus/app/core/workers/code_agent_worker.py`: Agente programador.
  - `janus/app/core/workers/professor_agent_worker.py`: Agente revisor.
  - `janus/app/core/workers/router_worker.py`: Distribuidor de tarefas.
- **Governança (Policy Engine)**:
  - `janus/app/core/autonomy/policy_engine.py`: Regras de segurança (Risk Profile, Allowlist).
  - `janus/app/core/tools/action_module.py`: Registro e execução de ferramentas.

### 5. Workers e Mensageria (RabbitMQ)
O sistema nervoso assíncrono.
- **Broker**: `janus/app/core/infrastructure/message_broker.py` (Publicação/Consumo resiliente).
- **Workers**: `janus/app/core/workers/` (Todos os consumidores de fila ficam aqui).
- **Orquestrador**: `janus/app/core/workers/orchestrator.py` (Inicia e gerencia processos worker).

### 6. Frontend (Angular)
A interface visual.
- **Páginas**: `front/src/app/pages/` (Documentação, Chat, Arquitetura).
- **Serviços de API**: `front/src/app/services/` (Comunicação com o backend).
- **Componentes Compartilhados**: `front/src/app/shared/`.

---

## Convenções de Nomenclatura

- **Python (Backend)**:
  - Módulos e pacotes: `snake_case` (ex: `llm_manager.py`).
  - Classes: `PascalCase` (ex: `LLMManager`).
  - Variáveis/Funções: `snake_case`.
- **TypeScript (Frontend)**:
  - Componentes: `PascalCase` (ex: `ChatComponent`).
  - Arquivos: `kebab-case` (ex: `chat-component.ts`).

## Princípios de Organização

1.  **Separação por Responsabilidade**: `core` contém a infraestrutura e lógica pura; `services` orquestra casos de uso; `api` apenas expõe via HTTP.
2.  **Workers Isolados**: Cada worker em `janus/app/core/workers` deve ser independente e focado em uma tarefa (Consolidação, Treino, Execução).
3.  **Configuração Centralizada**: Tudo que é variável de ambiente passa por `janus/app/config.py`.

Dúvidas sobre onde colocar um novo arquivo? Consulte o diretório `services/` para lógica de negócio ou `core/` se for uma funcionalidade fundamental do sistema.
