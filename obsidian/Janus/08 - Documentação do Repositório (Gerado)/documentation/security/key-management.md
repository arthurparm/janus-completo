---
gerado: true
origem: "documentation/security/key-management.md"
ultima_geracao: "2026-05-22T18:03:31.345032+00:00"
---

# Gerenciamento de Chaves (Sem KMS) e Rotação de Secret Memory

Classificação: internal-only (referência técnica)  
Objetivo: criptografia em repouso da secret memory com rotação mensal, sem depender de KMS.

## 1) Keyring via variáveis de ambiente

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

Implementação: [security.py](file:///h:/repos/janus-completo/backend/app/core/memory/security.py)

## 2) Metadados de criptografia por registro

Cada segredo persiste:

- `metadata.enc = "fernet"`
- `metadata.kid = "<key_id>"`

Assim a decriptação continua funcionando após rotação, mantendo compatibilidade com chaves antigas.

Implementação: [secret_memory_service.py](file:///h:/repos/janus-completo/backend/app/services/secret_memory_service.py)

## 3) Rotação mensal (processo operacional)

Passos:

1. Gerar novo `key_id` (ex.: `2026-06`) e material (segredo de 32+ bytes).
2. Atualizar `MEMORY_KEYRING` para incluir a nova chave, mantendo as antigas.
3. Atualizar `MEMORY_ACTIVE_KEY_ID` para o novo `key_id`.
4. Fazer deploy/restart do serviço.
5. A recriptografia gradual roda automaticamente em background via scheduler.

## 4) Recriptografia gradual sem downtime

O scheduler executa um job periódico que:

- busca segredos ativos
- decripta com a chave antiga (metadata.kid ou fallback)
- recripta com a chave ativa
- atualiza o payload no Qdrant sem interromper leituras

Implementação:

- Serviço: [secret_key_rotation_service.py](file:///h:/repos/janus-completo/backend/app/services/secret_key_rotation_service.py)
- Job: [scheduler_service.py](file:///h:/repos/janus-completo/backend/app/services/scheduler_service.py)

Configuração:

- `SECRET_REENCRYPT_INTERVAL_SECONDS` (default: 600)
- `SECRET_REENCRYPT_BATCH_SIZE` (default: 100)

## 5) Auditoria de acesso a segredos

Todo acesso relevante gera eventos em `audit_events`:

- `secret_write` (criação/atualização)
- `secret_read` (revelação autorizada)
- `secret_reencrypt_batch` (lote de recriptografia)

Modelo: [AuditEvent](file:///h:/repos/janus-completo/backend/app/models/user_models.py#L135-L153)

