## Objetivo
1) Corrigir `dedupe_concepts` para usar `RELATES_TO` nos dois sentidos e eliminar duplicidades; 2) Registrar `CALLS`, `IMPLEMENTS`, `RELATES_TO` em `ensure_basic_constraints`; 3) Instrumentar dedupe com métricas/auditoria e consolidar contagens.

## Correções em dedupe_concepts
- Ajustar o tipo de relação para `RELATES_TO` corretamente nas duas direções (saída e entrada).
  - Corrigir uso literal "`${GraphRelationship.RELATES_TO.value}`" para `RELATES_TO` com f-string ou literal, garantindo que o tipo não seja gravado incorreto.
  - Local: `janus/app/repositories/knowledge_repository.py:133` e `:141`.
- Remover código redundante não utilizado (variável `canon_id`) e manter uma única transação por grupo.
  - Local: `janus/app/repositories/knowledge_repository.py:118–121`.
- Garantir registro do tipo de relacionamento antes da consolidação (defensivo, embora já exista ontologia).
  - `await self._db.register_relationship_type(tx, GraphRelationship.RELATES_TO.value)` antes dos `MERGE`.
- Resultado retornado mantém `{"groups": total_groups, "fixed": fixed}`.

## Remover duplicidades de função
- Verificar e manter dedupe de funções e classes baseado em chave `(name, file_path)`, sem duplicar arestas `CALLS`/`IMPLEMENTS`.
  - O código já usa `MERGE` nas duas direções: `janus/app/repositories/knowledge_repository.py:172–183` (funções) e `:198–209` (classes).
- Pequenos ajustes: adicionar contagem de grupos avaliados para funções e classes e confirmar que `MERGE` evita paralelas duplicadas.

## Registrar tipos de relacionamento em ensure_basic_constraints
- Em `janus/app/repositories/knowledge_repository.py:462–484`, dentro da transação, registrar explicitamente:
  - `GraphRelationship.CALLS.value`
  - `GraphRelationship.IMPLEMENTS.value`
  - `GraphRelationship.RELATES_TO.value`
- Manter o já existente `GraphRelationship.MENTIONS.value`.

## Métricas e Auditoria
- Definir Counters Prometheus no topo do repositório (junto aos existentes):
  - `graph_dedupe_groups_total{entity}`
  - `graph_dedupe_fixed_total{entity}`
- Incrementar métricas após cada grupo consolidado e ao final usar o total de grupos.
  - `entity` ∈ `concepts|functions|classes|files`.
- Registrar eventos de auditoria após cada consolidação e ao final de cada método:
  - `record_audit_event_direct({"endpoint": "graph", "action": "dedupe_concepts|dedupe_functions|dedupe_classes|dedupe_files", "status": "ok"})` com `user_id=None`.
- Em `dedupe_report` (`janus/app/repositories/knowledge_repository.py:252–256`), registrar um evento agregado com os totais consolidados.

## Consolidar contagens
- Ajustar retornos dos métodos para incluir `groups` e `fixed` em todos:
  - `dedupe_functions_and_classes`: retornar `{functions_groups, functions_fixed, classes_groups, classes_fixed}`.
  - `dedupe_files`: retornar `{files_groups, files_fixed}`.
- Atualizar `dedupe_report` para retornar estrutura agregada:
  - `{"concepts_groups": x, "concepts_fixed": y, "functions_groups": a, "functions_fixed": b, "classes_groups": c, "classes_fixed": d, "files_groups": e, "files_fixed": f, "total_groups": x+a+c+e, "total_fixed": y+b+d+f}`.

## Verificação
- Executar varreduras `MATCH` para duplicatas antes/depois e confirmar que `fixed == groups` em dados controlados.
- Checar se nenhum relacionamento com tipo incorreto foi criado (ex.: literal `${GraphRelationship.RELATES_TO.value}`).
- Validar métricas expostas e presença de eventos de auditoria.

## Referências de Código
- `dedupe_concepts`: `janus/app/repositories/knowledge_repository.py:102–153`.
- `dedupe_functions_and_classes`: `janus/app/repositories/knowledge_repository.py:155–218`.
- `dedupe_files`: `janus/app/repositories/knowledge_repository.py:220–250`.
- `dedupe_report`: `janus/app/repositories/knowledge_repository.py:252–256`.
- `ensure_basic_constraints`: `janus/app/repositories/knowledge_repository.py:462–484`.
- Enum de relações: `janus/app/models/schemas.py:43–60`.
- Registro de tipos: `janus/app/db/graph.py:171–178` e ontologia: `janus/app/db/graph.py:51–104`.
- Auditoria direta: `janus/app/repositories/observability_repository.py`.

Confirma prosseguir com a implementação?