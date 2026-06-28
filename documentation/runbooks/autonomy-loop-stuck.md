# Runbook: Autonomy Loop Travou

## Sintomas
- Loop de autonomia sem executar ciclos há mais de 5 minutos
- Métrica Prometheus `autonomy_loop_active` = 1
- Nenhum evento `autonomy_cycle_started` no audit ledger nos últimos 5 minutos
- Endpoint `GET /autonomy/health` retorna `overall_status: degraded`

## Diagnóstico
1. Verificar status do loop: `GET /autonomy/health`
   - `active: true` mas `last_cycle_at` estagnado → loop bloqueado
2. Verificar leases Redis: `GET /autonomy/health` → campo `leases`
   - Se `lease_held: false` → outra instância pode ter tomado o lock
3. Verificar circuit breakers: `GET /autonomy/health` → campo `domain_health`
   - Domínios com `is_open: true` podem bloquear execução
4. Verificar throttle: `GET /autonomy/health` → campo `throttle`
   - Se `action_count_minute >= max_per_minute` → throttle ativo
5. Verificar logs do container janus-api:
   ```bash
   docker compose -f docker-compose.pc1.yml logs janus-api --tail 100 | grep autonomy
   ```

## Recuperação
### Opção 1: Reset via endpoint
```bash
curl -X POST http://localhost:8000/api/v1/autonomy/admin/throttle/reset \
  -H "Authorization: Bearer <admin_token>"
```

### Opção 2: Parar e reiniciar o loop
```bash
curl -X POST http://localhost:8000/api/v1/autonomy/stop \
  -H "Authorization: Bearer <admin_token>"
curl -X POST http://localhost:8000/api/v1/autonomy/start \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <admin_token>" \
  -d '{"interval_seconds": 60, "risk_profile": "balanced", "execution_mode": "enqueue_router"}'
```

### Opção 3: Reiniciar container (último recurso)
```bash
docker compose -f docker-compose.pc1.yml restart janus-api
```
