# Gate Operacional de Backfill e Quarentena

## Objetivo

Padronizar um procedimento mínimo, versionado e auditável para preparar dados legados antes de ativar constraints ou restrições de integridade.

## Escopo

Este gate não depende de produção real. Ele organiza o que já existe no repositório e aponta para comandos reais:

- preparação e validação SQL via `DBMigrationService`;
- auditoria, backfill e constraints do Neo4j via `backend/scripts/neo4j_noise_maintenance.py`;
- evidências e revisão de quarentena via endpoints já expostos pela API.

## Artefatos canônicos

- Wrapper operacional: `python tooling/dev.py backfill-gate`
- Script raiz do gate: `python backend/scripts/run_backfill_quarantine_gate.py`
- Relatórios JSON: `outputs/qa/backfill-quarantine-gate/`
- Checklist operacional: `documentation/operations/backfill-quarantine-checklist.md`

## O que o gate executa

No modo `full`, o gate executa a seguinte sequência:

1. `sql_prepare_constraint_data`
2. `sql_validate_constraint_readiness`
3. `neo4j_audit`
4. `neo4j_backfill_entity_canonical`
5. `neo4j_apply_constraints` ou `skipped`
6. `sql_apply_prepared_constraints` ou `skipped`
7. `sql_final_constraint_readiness`

## Comandos recomendados

Dry-run completo, sem aplicar constraints:

```bash
python tooling/dev.py backfill-gate --mode full
```

Dry-run com relatório explícito:

```bash
python tooling/dev.py backfill-gate --mode full --report outputs/qa/backfill-quarantine-gate/manual-run.json
```

Aplicação controlada de constraints após prontidão:

```bash
python tooling/dev.py backfill-gate --mode full --apply-constraints
```

Somente fluxo SQL:

```bash
python tooling/dev.py backfill-gate --mode sql-only --apply-constraints
```

Somente fluxo Neo4j:

```bash
python tooling/dev.py backfill-gate --mode neo4j-only --apply-constraints
```

## Critério de bloqueio

Constraints não devem ser aplicadas quando o relatório final retornar `blocked`.

Hoje, os bloqueios SQL são derivados principalmente de:

- `pending_actions.user_id` ainda com linhas sem owner;
- `experiments.owner_user_id` ainda sem backfill;
- `profiles` com perfis duplicados por usuário;
- `auth_migration_quarantine` com itens pendentes.

## Revisão de quarentena

Depois do dry-run, a equipe deve revisar a quarentena antes de qualquer aplicação definitiva:

- Grafo de conhecimento:
  - `GET /api/v1/knowledge/quarantine`
  - `POST /api/v1/knowledge/quarantine/promote`
- Observabilidade do grafo:
  - `GET /api/v1/observability/graph/quarantine`
  - `POST /api/v1/observability/graph/quarantine/promote`
- Poison pills:
  - `GET /api/v1/observability/poison-pills/quarantined`
  - `POST /api/v1/observability/poison-pills/release`
  - `POST /api/v1/observability/poison-pills/cleanup`
- Revisão administrativa de entidades quarentenadas:
  - `POST /api/v1/autonomy/admin/knowledge/quarantine/review`

## Evidência mínima para liberar constraints

Antes de aplicar constraints em qualquer ambiente real, arquivar pelo menos:

- relatório JSON do gate;
- snapshot dos bloqueios remanescentes ou confirmação de `ready`;
- evidência da revisão de quarentena;
- decisão explícita de seguir com `--apply-constraints`.

## Observações

- O gate é aditivo: ele prepara, valida e só aplica constraints quando a prontidão estiver verde.
- O runbook fecha o processo operacional mínimo, mas não substitui a execução em ambiente real quando essa etapa for autorizada.
