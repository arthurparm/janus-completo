# Runbook: Revisão de Entidades em Quarentena

## Sintomas
- Entidades acumulando com label `Quarantine` no Neo4j
- Métrica `autonomy_quarantined_entities_count` crescente
- Qualidade de busca RAG degradada (respostas irrelevantes ou incorretas)

## Diagnóstico
1. Listar entidades em quarentena:
   ```bash
   curl http://localhost:8000/api/v1/autonomy/admin/self-study/neo4j-audit?orphan_limit=50 \
     -H "Authorization: Bearer <admin_token>"
   ```
2. Verificar entidades mais antigas (risco de purge automático):
   - Entidades > 30 dias sem revisão são removidas automaticamente
3. Inspecionar razão da quarentena:
   - `no_code_evidence`: entidade extraída por LLM sem corroboração no código fonte
   - Verificar se a entidade corresponde a uma função/classe/arquivo real que o AST não detectou

## Recuperação
### Opção 1: Aprovar entidade (remover quarentena)
```bash
curl -X POST http://localhost:8000/api/v1/autonomy/admin/knowledge/quarantine/review \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"entity_name": "NomeDaEntidade", "action": "approve"}'
```

### Opção 2: Rejeitar entidade (manter quarentena)
```bash
curl -X POST http://localhost:8000/api/v1/autonomy/admin/knowledge/quarantine/review \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"entity_name": "NomeDaEntidade", "action": "reject"}'
```
Entidades rejeitadas são removidas no próximo ciclo de purge (> 30 dias).

### Opção 3: Reprocessar extração
Se muitas entidades legítimas estão em quarentena, execute um ciclo de self-study full:
```bash
curl -X POST http://localhost:8000/api/v1/autonomy/admin/self-study/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"mode": "full"}'
```
