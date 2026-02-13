# Janus Completo - Sistema Agentico de IA

## Visão Geral

O repositório `janus-completo` organiza um sistema agentico de IA com duas partes principais:
- **Frontend (`front`)**: Interface web construída com Angular 20, consumindo a API via REST e SSE.
- **Backend (`janus`)**: API FastAPI orientada a serviços e workers, integrando Redis, RabbitMQ, Neo4j e Qdrant para processamento autônomo.

O sistema permite conversas assistidas por agentes com streaming, memória episódica, grafo de conhecimento (RAG híbrido) e operação autônoma via workers.

## Arquitetura

O sistema segue uma arquitetura modular:
- **Frontend**: Angular 20 (SPA), RxJS, TailwindCSS.
- **Backend**: Python 3.11+, FastAPI, SQLAlchemy.
- **Infraestrutura**:
  - **RabbitMQ**: Broker de mensagens para comunicação assíncrona.
  - **Redis**: Cache e gerenciamento de sessões.
  - **Neo4j**: Banco de dados orientado a grafos para memória semântica.
  - **Qdrant**: Banco de dados vetorial para memória episódica.
  - **PostgreSQL**: Persistência relacional (configurações, logs).

## Stack Tecnológica

### Frontend
- Framework: Angular `^20.0.0`
- Linguagem: TypeScript `~5.9.2`
- Build: Angular CLI + `@angular/build` (Vite)
- Testes: Vitest + Testing Library

### Backend
- Framework: FastAPI + Uvicorn
- Linguagem: Python `>=3.11,<3.13`
- IA/LLM: LangChain, OpenRouter, OpenAI, Gemini, Ollama, DeepSeek
- Banco de Dados: PostgreSQL (+pgvector), Neo4j `>=5.19.0`, Qdrant `>=1.9.2`

## Instalação e Execução

### Pré-requisitos
- Node.js 20+
- Python 3.11+ (mas < 3.13)
- Docker e Docker Compose (recomendado para infraestrutura)

### Frontend (`front/`)

```bash
cd front
npm install
npm start
```
Acesse em: `http://localhost:4200` (proxy configurado para `/api` -> `http://localhost:8000`)

### Backend (`janus/`)

```bash
cd janus
# Recomendado usar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # ou .venv\Scripts\activate no Windows

# Instalar dependências (pode ser necessário excluir pacotes conflitantes no Linux/Python 3.12 como tflite-runtime se houver erro)
pip install -r requirements.txt

# Executar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Diretrizes de Desenvolvimento

### Regras Críticas (Backend)
- **Tipagem**: Manter tipagem forte com MyPy strict. Novas funções devem ter types completos.
- **Arquitetura**: Respeitar a separação `endpoints -> services -> repositories`. Lógica de negócio fica nos services.
- **Workers**: Tarefas longas devem usar workers/RabbitMQ, nunca bloquear a thread do request.
- **Testes**: Manter padrão `test_*.py` em `janus/tests`.

### Regras Críticas (Frontend)
- **Componentes**: Manter componentes enxutos; mover lógica para `services` e `stores`.
- **SSE**: Seguir padrão do `ChatStreamService` para streaming de respostas.
- **Commits**: Seguir Conventional Commits (ex: `feat(ui): adicionar gráfico`).

## Roadmap e Backlog (Consolidado)

### 1) Estudo do Próprio Código (Code Intelligence)
- [x] Corrigir modelagem de entidades de código no grafo (File/Function/Class) (2026-02-12)
- [x] Endpoint de pergunta sobre código com citação (2026-02-12)
- [ ] Indexação incremental por `git diff`
- [ ] Extração AST de imports, decorators, assinatura

### 2) Memória, RAG e Conhecimento
- [x] Telemetria obrigatória por etapa (2026-02-13)
- [x] Threshold de confiança com fluxo de confirmação (2026-02-13)
- [ ] Reranking semântico com features de qualidade
- [ ] Memória de longo prazo com consolidação transacional no grafo

### 3) Agentes, Planejamento e Execução
- [ ] Planejamento hierárquico com decomposição de metas
- [ ] Simulação antes de execução de ações destrutivas
- [ ] Detecção de loop e escape automático

### 4) Ferramentas, Segurança e Governança
- [x] Substituir parser frágil de tool call por envelope JSON estrito (2026-02-13)
- [x] Validação de args por schema (pydantic) (2026-02-13)
- [x] Sandboxing por capability e allowlist de comandos (2026-02-13)

### 5) Observabilidade, Qualidade e Confiabilidade
- [x] Dashboard único por request_id (2026-02-13)
- [x] Contract tests para endpoints críticos e SSE (2026-02-13)
- [ ] Tracing distribuído fim-a-fim

### 6) Produto e Experiência (Front + API)
- [x] UI de citação clicável para código e documentos (2026-02-13)
- [x] Centro de aprovações pendentes com comparação de risco (2026-02-13)
- [ ] Tela de explicação de resposta (fontes, confiança, latência)
- [ ] Timeline de memória por conversa

### 7) Plataforma, Dados e Integrações
- [x] Alinhamento definitivo de schema SQL (2026-02-13)
- [ ] Migrações idempotentes e auditadas
- [ ] Backup/restore automatizado

### 8) DevEx e Fluxo de Entrega
- [x] Seed de dados e cenários de teste reproduzíveis (2026-02-13)
- [x] Lint/type/test gates padronizados em CI (2026-02-13)

### 9) IA Aplicada ao Produto (Futuro)
- [ ] Roteamento dinâmico de modelos por tipo de pergunta e custo
- [ ] Avaliador automático de factualidade

---
_Documentação consolidada em Fev/2026._
