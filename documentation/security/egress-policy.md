# Política de Egress (Ferramentas e Workers)

Classificação: internal-only (referência técnica)  
Objetivo: reduzir SSRF e exfiltração de dados via tráfego de saída, com auditoria de bloqueios.

## Escopo

- Ferramentas (tools) que fazem requisições HTTP/HTTPS
- Workers e integrações internas/externas que fazem HTTP/HTTPS
- Ferramentas de CLI externa (Codex/Jules): bloqueadas por padrão por risco de egress não controlado

## Controles implementados

### 1) Tools: deny-by-default + allowlist + SSRF hardening

- Implementação: [enforce_tool_http_egress](file:///h:/repos/janus-completo/backend/app/core/security/egress_policy.py)
- Requisitos:
  - host deve estar em allowlist
  - URL deve ser segura (bloqueia localhost, .localhost e IPs não públicos)
  - toda tentativa bloqueada gera evidência no audit ledger (`audit_ledger_events`)

Configuração:

- `TOOL_EGRESS_ALLOW_HOSTS` (CSV ou JSON)
  - Ex.: `TOOL_EGRESS_ALLOW_HOSTS=example.com,docs.example.com`
  - Ex.: `TOOL_EGRESS_ALLOW_HOSTS=["example.com","docs.example.com"]`

### 2) Workers: allowlist por host + defaults internos

- Implementação: [enforce_worker_http_egress](file:///h:/repos/janus-completo/backend/app/core/security/egress_policy.py)
- Política:
  - permite apenas hosts em `WORKER_EGRESS_ALLOW_HOSTS` + defaults internos necessários (postgres/redis/rabbitmq/qdrant/neo4j/host.docker.internal)
  - adiciona automaticamente hosts externos mínimos conforme features configuradas (ex.: Google OAuth, OpenAI)
  - toda tentativa bloqueada gera evidência no audit ledger (`audit_ledger_events`)

Configuração:

- `WORKER_EGRESS_ALLOW_HOSTS` (CSV ou JSON), para ambientes que exigem allowlist explícita de terceiros.

## Evidência / Auditoria

- Bloqueios geram eventos no audit ledger com `endpoint=egress_policy` e `action=egress_blocked`.
- Modelo: [AuditLedgerEvent](file:///h:/repos/janus-completo/backend/app/models/audit_ledger_models.py#L9-L41)
