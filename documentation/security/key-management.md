# Gerenciamento de Chaves e Rotação de Secret Memory (Keyring ou Vault Transit)

Classificação: internal-only (referência técnica)  
Objetivo: criptografia em repouso da secret memory com rotação, com opção de keyring local ou Vault Transit.

## 1) Provedores de criptografia

O Janus suporta:

- `MEMORY_ENCRYPTION_PROVIDER=keyring` (default): Fernet via keyring em variáveis de ambiente.
- `MEMORY_ENCRYPTION_PROVIDER=vault_transit`: envelope encryption via HashiCorp Vault Transit.

Implementação: [security.py](file:///h:/repos/janus-completo/backend/app/core/memory/security.py)

## 2) Keyring via variáveis de ambiente (Fernet)

O Janus suporta um keyring em memória de processo, configurado por variáveis de ambiente.

Variáveis:

- `MEMORY_KEYRING`
  - JSON: `{"2026-05":"<material>","2026-06":"<material>"}`  
  - ou CSV: `2026-05:<material>,2026-06:<material>`
- `MEMORY_ACTIVE_KEY_ID`
  - define qual `key_id` do keyring é usada para novas gravações
- `MEMORY_KEY_ROTATION_DAYS` (default: 30)
  - parâmetro de governança para periodicidade (a rotação em si ocorre por atualização de env + deploy)

Observação:

- `MEMORY_ENCRYPTION_KEY` permanece como compatibilidade legada, mas **secret memory exige keyring/legacy key configurada**.

## 3) Vault Transit (KMS)

Variáveis:

- `VAULT_ADDR`
- `VAULT_NAMESPACE` (opcional)
- `VAULT_AUTH_METHOD=approle` (default) ou `VAULT_TOKEN` (opcional)
- `VAULT_APPROLE_ROLE_ID` e `VAULT_APPROLE_SECRET_ID`
- `VAULT_TRANSIT_MOUNT` (default: `transit`)
- `VAULT_TRANSIT_KEY_NAME` (default: `janus-secret-memory`)
- `VAULT_TRANSIT_ROTATE_INTERVAL_SECONDS` (default: 2592000)

Implementação:

- Cliente: [vault_client.py](file:///h:/repos/janus-completo/backend/app/core/infrastructure/vault_client.py)
- Rotação (job): [scheduler_service.py](file:///h:/repos/janus-completo/backend/app/services/scheduler_service.py)

## 4) Metadados de criptografia por registro

Cadastra em `metadata`:

- `metadata.enc = "fernet"`
- `metadata.kid = "<key_id>"`

Assim a decriptação continua funcionando após rotação, mantendo compatibilidade com chaves antigas.

Implementação: [secret_memory_service.py](file:///h:/repos/janus-completo/backend/app/services/secret_memory_service.py)

## 5) Rotação mensal (processo operacional)

Passos:

1. Gerar novo `key_id` (ex.: `2026-06`) e material (segredo de 32+ bytes).
2. Atualizar `MEMORY_KEYRING` para incluir a nova chave, mantendo as antigas.
3. Atualizar `MEMORY_ACTIVE_KEY_ID` para o novo `key_id`.
4. Fazer deploy/restart do serviço.
5. A recriptografia gradual roda automaticamente em background via scheduler.

## 6) Recriptografia gradual sem downtime (keyring)

O scheduler executa um job periódico que:

- busca segredos ativos
- decripta com a chave antiga (metadata.kid ou fallback)
- recripta com a chave ativa
- atualiza o payload no Qdrant sem interromper leituras

Observação: quando `MEMORY_ENCRYPTION_PROVIDER=vault_transit`, a rotação ocorre no Vault e a recriptografia em lote é dispensada.

Implementação (keyring):

- Serviço: [secret_key_rotation_service.py](file:///h:/repos/janus-completo/backend/app/services/secret_key_rotation_service.py)
- Job: [scheduler_service.py](file:///h:/repos/janus-completo/backend/app/services/scheduler_service.py)

Configuração:

- `SECRET_REENCRYPT_INTERVAL_SECONDS` (default: 600)
- `SECRET_REENCRYPT_BATCH_SIZE` (default: 100)

## 7) Auditoria de acesso a segredos

Todo acesso relevante gera eventos no audit ledger (`audit_ledger_events`):

- `secret_write` (criação/atualização)
- `secret_read` (revelação autorizada)
- `secret_reencrypt_batch` (lote de recriptografia)

Modelo: [AuditLedgerEvent](file:///h:/repos/janus-completo/backend/app/models/audit_ledger_models.py)
