# Runbook: Ferramenta Evolutiva com Falha

## Sintomas
- Evento `autonomy_action_failed` no audit ledger
- Ferramenta do namespace `evolution` retornando erros
- Métrica `autonomy_slo_rollback_recovery_s` ativa
- Endpoint `GET /autonomy/admin/tools/{name}/provenance` mostra `evolution_attempt_id`

## Diagnóstico
1. Identificar ferramenta com falha:
   ```bash
   curl http://localhost:8000/api/v1/autonomy/admin/tools/{name}/provenance \
     -H "Authorization: Bearer <admin_token>"
   ```
2. Verificar logs do EvolutionSandbox:
   ```bash
   docker compose -f docker-compose.pc1.yml logs janus-api --tail 200 | grep evolution_sandbox
   ```
3. Verificar se rollback automático ocorreu:
   ```bash
   curl http://localhost:8000/api/v1/autonomy/admin/tools/{name}/provenance \
     -H "Authorization: Bearer <admin_token>"
   # Se 'rolled_back_at' estiver preenchido, rollback já ocorreu
   ```

## Recuperação
### Opção 1: Rollback manual (se automático falhou)
```bash
curl -X POST http://localhost:8000/api/v1/autonomy/admin/tools/{name}/rollback \
  -H "Authorization: Bearer <admin_token>"
```

### Opção 2: Investigar e reprocessar no Lab
1. Obter código da ferramenta com falha via provenance
2. Executar manualmente no Lab:
   ```python
   from app.core.evolution.evolution_sandbox import evolution_sandbox
   ok, reason = evolution_sandbox.validate(failed_code)
   if not ok:
       print(f"Validation failed: {reason}")
   ```
3. Corrigir e reprocessar via EvolutionManager

### Opção 3: Quarentena da ferramenta
Se a ferramenta não puder ser corrigida, remova-a do namespace evolution e mova para quarentena.
