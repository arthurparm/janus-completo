## Objetivo
- Consolidar memória episódica (Qdrant) em memória semântica (Neo4j) com maior qualidade, menor duplicação e governança clara.

## Estado Atual
- Worker de consolidação existente com extração via LLM, normalização e persistência: `janus/app/core/workers/knowledge_consolidator_worker.py:91-111,124-133,248-267,270-331,378-447,448-470,472-551,552-621,622-637,639-811`
- Guardião do grafo com enums, sinônimos e validações: `janus/app/core/memory/graph_guardian.py:16-44,46-75,76-130,132-215,218-227,233-276,296-338,339-377,378-407,408-451,454-455`
- Ontologia e índices já bootstrapados: `janus/app/db/graph.py:51-99,166-173`
- Memória episódica com quotas, PII, criptografia e recall: `janus/app/core/memory/memory_core.py:34-63,85-171,194-304`

## Lacunas Principais
- Limiar de confiança e metadados de origem em relações/entidades são opcionais.
- Quarentena com regras simples; falta score/confidence e `source_snippet`.
- Consolidação em lote não considera deduplicação semântica avançada (mesmo conceito com propriedades diferentes).
- Auditoria focada em relações fora do enum e relatório por sessão/usuário não está integrado.

## Escopo (Fase 1–2)
- Elevar qualidade e reduzir duplicatas mantendo compatibilidade com os módulos acima.

## Melhorias Técnicas
- Limiar de confiança mínimo:
  - Aplicar `confidence ≥ 0.6` em insights e relações quando disponível; caso ausente, estimar heuristicamente pela consistência de nomes e tipo (fallback).
  - Propagar `confidence` em `r.confidence` e usar para quarentena.
- Quarentena enriquecida:
  - Exigir `source_experience` ou `source_document`; opcional `source_snippet`.
  - Enviar entradas com baixa qualidade para `:Quarantine` com `[:EXTRACTED_FROM]` e motivo detalhado.
- Deduplicação semântica:
  - Usar `MERGE` por `name` para entidades (já feito), mas consolidar propriedades via política (preferir última/maior confiança).
  - Para relações, `MERGE (a)-[r:TYPE]->(b)` (já feito) e atualizar propriedades agregadas (`first_seen`, `last_seen`, `occurrences += 1`).
- Agrupamento transacional:
  - Manter UNWIND por tipo (existente) e garantir registro do `RelationshipType` antes do MERGE.
- Metadados canônicos:
  - Garantir `original_name`, `original_from`, `original_to`, `source_experience/source_document`, `discovered_at/last_seen`.
- Consolidação periódica:
  - Usar `consolidate_batch(limit, min_score)` com janela e filtros por `metadata.type` e `ts_ms` (MemoryCore já suporta filtros/tempo).
- Observabilidade:
  - Métricas já presentes: `knowledge_consolidation_total`, `knowledge_consolidation_latency_seconds`, `knowledge_entities_extracted_total`, `knowledge_relationships_created_total`.
  - Adicionar painéis e endpoint de auditoria (referências): `janus/app/api/v1/endpoints/observability.py:93-97`, `janus/app/services/observability_service.py:108-115`, `janus/app/repositories/observability_repository.py:120-183`.
- Testes de governança:
  - Teste falha se surgir tipo fora do enum canônico (GraphRelationship/RelationType).
  - Teste garante registro de `RelationshipType` para qualquer aresta criada.

## Faseamento
- Fase 1 — Quick Wins
  - Adicionar `confidence` ao persistir relações/insights; enriquecer `Quarantine` com `source_snippet` e motivos.
  - Registrar `first_seen/last_seen` e `occurrences` em arestas; atualizar `Experience.insights` já existente.
- Fase 2 — Deduplicação e Auditoria
  - Consolidação de propriedades de entidades por política (maior confiança vence; manter `previous_name` quando mudar).
  - Endpoint de auditoria do grafo: listar relações fora de padrão e não registradas, promover da quarentena (HITL básico).
- Fase 3 — Versionamento e HITL
  - `valid_from/valid_to` em entidades mutáveis; reconciliação semântica.
  - UI/API para revisão e promoção da quarentena.

## Critérios de Aceitação
- Relações e insights abaixo do limiar vão para `:Quarantine` com `[:EXTRACTED_FROM]` e motivo.
- Não criar duplicatas de nós/arestas; `occurrences` e `last_seen` atualizados.
- Auditoria lista tipos não canônicos e relações fora do padrão; permite promover/rejeitar.
- Métricas refletem redução de duplicatas e latência estável.

## Referências do Repositório
- Consolidator: `janus/app/core/workers/knowledge_consolidator_worker.py:248-331,378-447,472-551,552-621`
- Graph Guardian: `janus/app/core/memory/graph_guardian.py:296-338,339-377`
- Ontologia/Índices: `janus/app/db/graph.py:51-99,166-173`
- MemoryCore (episódica): `janus/app/core/memory/memory_core.py:85-171,194-304`
- Observabilidade: `janus/app/core/infrastructure/logging_config.py`, `janus/app/api/v1/endpoints/observability.py:93-97`

Confirma este plano para iniciarmos as alterações da Fase 1?