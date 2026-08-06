# Scripts Operacionais do Backend

## Gate de Backfill e Quarentena Antes de Constraints

O procedimento versionado para preparar dados legados antes de ativar constraints fica em:

```bash
python backend/scripts/run_backfill_quarantine_gate.py --mode full
```

O script gera um relatório JSON auditável em `outputs/qa/backfill-quarantine-gate/` com a sequência:

1. `sql_prepare_constraint_data`
2. `sql_validate_constraint_readiness`
3. `neo4j_audit`
4. `neo4j_backfill_entity_canonical`
5. `neo4j_apply_constraints` ou `skipped`
6. `sql_apply_prepared_constraints` ou `skipped`
7. `sql_final_constraint_readiness`

### Uso recomendado

Dry-run operacional, sem aplicar constraints:

```bash
python backend/scripts/run_backfill_quarantine_gate.py --mode full
```

Aplicação controlada após validação de prontidão:

```bash
python backend/scripts/run_backfill_quarantine_gate.py --mode full --apply-constraints
```

Somente SQL relacional:

```bash
python backend/scripts/run_backfill_quarantine_gate.py --mode sql-only --apply-constraints
```

Somente grafo Neo4j:

```bash
python backend/scripts/run_backfill_quarantine_gate.py --mode neo4j-only --apply-constraints
```

### Critério operacional

- Constraints só podem ser aplicadas quando `sql_validate_constraint_readiness` retornar `ready`.
- Se o relatório final sair como `blocked`, os bloqueios listados no JSON devem ser tratados antes de qualquer nova tentativa.
- O relatório é a evidência mínima para auditoria do procedimento.
