# Melhorias Possíveis (Roadmap Janus)

Este documento rastreia dívidas técnicas, melhorias de arquitetura e funcionalidades planejadas.

## ✅ Concluídas (Entregas Recentes)

- [x] **SOTA Planning (Reflexion)**: O `planner.py` implementa um pipeline **Reflexion** (Draft -> Critique -> Refine) que gera planos auto-corrigidos de alta fidelidade. O sistema de execução suporta `critical`, `retry` e `fallback_tool`.
- [x] **Runtime Self-Correction (OODA)**: O `AutonomyService` implementa um loop de **Observe-Orient-Decide-Act**. Se uma ação falhar criticamente, o sistema invoca o `Replanner` (LLM) que decide dinamicamente entre IGNORE, RETRY ou NEW_PLAN.

---

## 🚨 Alta Prioridade & Riscos Críticos

### Segurança & Integridade de Dados

- [ ] **Ghost Data Risk (Critical)**: `user_models.py` usa `ON DELETE CASCADE` no MySQL, mas Qdrant (Vetores) e Neo4j (Grafo) não sincronizam a deleção. Risco de dados órfãos (Violação LGPD/GDPR).
- [ ] **Secret Management**: `config.py` possui senhas padrão. Garantir falha na inicialização em produção se ENV VARs não estiverem definidas.
- [ ] **Prompt Injection Risk**: `PolicyEngine` não sanitiza o *conteúdo* de prompts de planejamento.
- [ ] **Security Headers**: Implementar middleware para HSTS, CSP, X-Content-Type-Options em `main.py`.
- [ ] **Dependency Audit**: Executar auditoria em `package.json` e `requirements.txt` (deps misturadas/antigas).

### Performance

- [x] **Event Loop Blocking (Critical)**: `ChatService.send_message` chama métodos síncronos do SQLAlchemy sem `await asyncio.to_thread`. Bloqueia o servidor com >1 usuário.
- [x] **Docker Resource Limits**: `docker-compose.yml` sem limites de CPU/Memória (risco de OOM no host).

---

## 🧠 Autonomia & Arquitetura Agêntica (SOTA 2025)

- [x] **Volatile Memory (Solved)**: Implementação **Local-First** com **SQLite WAL**. Inclui **Integrity Checks**, **Rolling Backups** e **Self-Healing** no boot. Robustez Máxima.
- [x] **Meta-Agent Architecture (SOTA Graph)**: Refatoração completa de `MetaAgent` para usar fluxos baseados em **Grafos de Estado**. Inclui Nodes de Monitoramento, Diagnóstico, Planejamento, **Reflexão (Crítica)** e Execução com **Pydantic Validation**.
- [x] **Robustness Layers**: State Checkpointing, Node Timeouts, Reflexion Loops (Retry) e Pydantic Validation.
- [ ] **Agent "Hardcoded Minds"**: Prompts de `multi_agent_system.py` estão hardcoded. Extrair para sistema de templates/DB.
- [x] **Industry Benchmark (LangGraph)**: Migração concluída para `langgraph.graph.StateGraph` com checkpoints (SQLite), Type Safety (`TypedDict`) e Reflexion Loops nativos.
- [ ] **Projeto Aprendiz Neural (Long Prazo)**: Planejamento para treinar um modelo local robusto (Sucessor/Clone) usando **Imitation Learning** a partir de +1000 trajetórias de alta qualidade (`training_data.jsonl`) do modelo atual. Foco em "regras da casa" e especialização proprietária.

---

## 🏗️ Backend & Infraestrutura

### Qualidade de Código & Refatoração

- [ ] **ChatService Refactor**: Quebrar monolito (+1600 linhas) em `PromptBuilderService`, `ToolExecutorService`, `RAGService`.
- [ ] **Loose Typing**: Migrar `Dict[str, Any]` em modelos críticos (`Experience`, `TaskState`) para Pydantic Models.
- [ ] **Weak Testing Patterns**: Substituir uso de repositórios reais em testes unitários por Mocks.
- [ ] **Orquestração WebRTC**: Implementar lógica de sinalização no backend para parear com o frontend.
- [ ] **Lógica Simbólica em Auto-Análise**: Substituir mocks em `/auto-analysis/health-check` por análise real de logs.

### Infraestrutura

- [ ] **Migration System**: Migrar de `db_migration_service.py` para **Alembic**.
- [ ] **Distributed Rate Limiting**: Migrar de memória local para Redis.
- [ ] **Tooling Modernization**: Considerar migração de `poetry` para `uv` (Astral).

---

## 🎨 Frontend (Angular)

### Arquitetura & State

- [ ] **State Management**: Migrar de "God Service" (`janus-api.service.ts`) para **Angular Signals** ou **SignalStore**.
- [ ] **God Components**: Refatorar `conversations.ts` (+800 linhas) separando Store e Service.
- [ ] **RxJS Anti-patterns**: Eliminar "subscribe inside subscribe" (ex: `conversations.ts`).
- [ ] **Dual-PaaS Conflict**: Decidir entre Firebase e Supabase como SSOT.

### UI/UX & Acessibilidade

- [ ] **Feedback de Erros Invisível**: Adicionar `<app-notification-banner>` ao `app.html` para exibir erros globais.
- [ ] **A11y Violations**: Adicionar `<main>` e landmarks ARIA em `app.html` e dashboard.
- [ ] **Empty States**: Adicionar estados vazios em Listagens (Sprints, Tools).
- [ ] **Feedback de Carregamento**: Padronizar Skeleton Loaders.
- [ ] **Internacionalização**: Implementar `@ngx-translate` (hoje hardcoded pt-BR/EN).

---

## 📚 Documentação & Processos

- [ ] **Inconsistência de Versões**: Unificar versionamento (Código diz 0.x, Docs diz 1.0).
- [ ] **Documentação Duplicada**: Renderizar Markdown de `docs/` no frontend em vez de hardcode no HTML.
- [ ] **SEO Básico**: Melhorar meta tags em `index.html`.
- [ ] **CI/CD Void**: Implementar pipeline básico em `.github/workflows`.
