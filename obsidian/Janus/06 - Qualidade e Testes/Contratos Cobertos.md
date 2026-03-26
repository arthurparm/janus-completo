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
- Visibilidade de endpoints de observabilidade, especialmente `audit/events`, `requests/{request_id}/dashboard` e `slo/domains`.
- Agregação do dashboard de pipeline por `request_id`.
- Instrumentação do `ObservabilityService` para `domain_slo_report`, `request_pipeline_dashboard` e `observe_ux_metric_record`.
- Lógica de breach e `insufficient_data` do SLO por domínio.
- Migração de schema.
- Query de conhecimento por código.
- Status de workers, incluindo casos `disabled` e `composite`.
- Guardrails do executor de ferramentas.
- Política de quotas de memória.
- Sanitização de export de auditoria.

## Arquivos-fonte
- `qa/test_api_visibility_endpoints.py`
- `qa/test_chat_endpoint_contract.py`
- `qa/test_chat_stream_sse_contract.py`
- `qa/test_observability_request_dashboard.py`
- `qa/test_observability_export.py`
- `backend/tests/unit/test_observability_service_instrumentation.py`
- `backend/tests/unit/test_oq002_domain_slo_alerts.py`
- `qa/test_db_migration_service_contract.py`
- `qa/test_knowledge_code_query_contract.py`
- `qa/test_workers_status_contract.py`
- `qa/test_tool_executor_policy_guards.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Ferramentas e Sandbox]]

## Riscos/Lacunas
- Contratos cobrem forma e semântica básica, não toda a experiência ponta a ponta distribuída.
- Na área de observabilidade, não há contrato dedicado para `health/system`, `health/check-all`, `metrics/summary`, poison pills, `graph/audit` ou `graph/quarantine/promote`.
- Também não há contrato forte, neste mapa, para `graph/quarantine`, `llm/usage` ou o health agregado inicial `unknown` antes do primeiro ciclo do monitor.
- `qa/test_api_visibility_endpoints.py` protege exposição e formato básico, mas não valida a semântica operacional completa dos cálculos de SLO, health agregado ou higiene de grafo.
