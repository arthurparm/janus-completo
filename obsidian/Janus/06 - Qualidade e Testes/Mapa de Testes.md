---
tipo: qualidade
dominio: testes
camada: cobertura
fonte-de-verdade: codigo
status: ativo
---

# Mapa de Testes

## Objetivo
Organizar a cobertura de testes real do repositório.

## Responsabilidades
- Mostrar onde há contrato e onde há smoke.
- Ligar testes aos domínios do sistema.

## Entradas
- `qa/`
- `backend/tests/`
- testes do frontend

## Saídas
- Navegação por cobertura.

## Dependências
- [[06 - Qualidade e Testes/Contratos Cobertos]]
- [[06 - Qualidade e Testes/Lacunas e Riscos]]

## Cobertura visível
- QA de contratos API:
  - `test_api_visibility_endpoints`
  - `test_chat_endpoint_contract`
  - `test_db_migration_service_contract`
  - `test_observability_request_dashboard`
  - `test_knowledge_code_query_contract`
  - `test_workers_status_contract`
- Guardrails:
  - `test_tool_executor_policy_guards`
  - `test_chat_agent_loop_content_safety`
  - `test_memory_quota_enforcement`
- Busca/memória:
  - `test_rag_hybrid_search_code`
  - `test_knowledge_space_contract`
  - `test_memory_timeline_user`
- Frontend:
  - specs de auth, layout, widgets e conversations

## Arquivos-fonte
- `qa/*.py`
- `backend/tests/**/*`
- `frontend/src/app/**/*.spec.ts`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Observabilidade]]

## Riscos/Lacunas
- A concentração de testes em contratos não cobre toda a complexidade de runtime distribuído.
