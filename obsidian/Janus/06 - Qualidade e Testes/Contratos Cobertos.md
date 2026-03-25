---
tipo: qualidade
dominio: testes
camada: contratos
fonte-de-verdade: codigo
status: ativo
---

# Contratos Cobertos

## Objetivo
Explicitar o que já possui proteção formal de contrato.

## Responsabilidades
- Ligar testes a superfícies do sistema.
- Ajudar a distinguir cobertura forte de cobertura implícita.

## Entradas
- suíte `qa`

## Saídas
- Mapa de contratos protegidos.

## Dependências
- [[06 - Qualidade e Testes/Mapa de Testes]]
- [[02 - Backend/API por Bounded Context]]

## Contratos fortemente visíveis
- Visibilidade e forma de endpoints.
- Contrato do chat HTTP e SSE.
- Status de observabilidade.
- Migração de schema.
- Query de conhecimento por código.
- Status de workers.
- Guardrails do executor de ferramentas.
- Política de quotas de memória.

## Arquivos-fonte
- `qa/test_api_visibility_endpoints.py`
- `qa/test_chat_endpoint_contract.py`
- `qa/test_chat_stream_sse_contract.py`
- `qa/test_observability_request_dashboard.py`
- `qa/test_db_migration_service_contract.py`
- `qa/test_knowledge_code_query_contract.py`
- `qa/test_workers_status_contract.py`
- `qa/test_tool_executor_policy_guards.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Ferramentas e Sandbox]]

## Riscos/Lacunas
- Contratos cobrem forma e semântica básica, não toda a experiência ponta a ponta distribuída.
