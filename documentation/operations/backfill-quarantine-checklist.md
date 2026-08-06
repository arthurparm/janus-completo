# Checklist Operacional de Backfill e Quarentena

- [ ] Executar `python tooling/dev.py backfill-gate --mode full` em modo dry-run.
- [ ] Arquivar o relatório JSON gerado em `outputs/qa/backfill-quarantine-gate/`.
- [ ] Revisar o campo `status` do relatório final.
- [ ] Se `status=blocked`, registrar e tratar todos os itens de `blockers` antes de qualquer constraint.
- [ ] Revisar itens de `auth_migration_quarantine` ainda pendentes.
- [ ] Revisar quarentena do grafo em `GET /api/v1/knowledge/quarantine`.
- [ ] Revisar quarentena operacional em `GET /api/v1/observability/graph/quarantine`.
- [ ] Revisar mensagens em quarentena em `GET /api/v1/observability/poison-pills/quarantined`.
- [ ] Executar promoções/liberações de quarentena somente com decisão operacional explícita.
- [ ] Executar `python tooling/dev.py backfill-gate --mode full --apply-constraints` somente após o gate estar pronto.
- [ ] Arquivar o relatório final pós-aplicação ou a decisão de bloqueio.
