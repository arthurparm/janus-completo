# Runbook de Prontidão de Produção

## Objetivo

Estabelecer um baseline auditável mínimo para validar identidade, segredos, rollout por host e sequência de release antes de promover o Janus para produção.

## Escopo

Este runbook cobre o que é executável no repositório sem acesso direto ao ambiente produtivo:

- baseline de hosts, segredos críticos e ordem de rollout;
- gate operacional de identidade;
- validação local de `.env` contra placeholders/hosts indevidos;
- pacote mínimo de evidências para revisão final.

## Artefatos canônicos

- Baseline: `documentation/operations/production-readiness.baseline.json`
- Checklist de release: `documentation/operations/release-sequence-checklist.md`
- Verificador: `python tooling/dev.py readiness`
- Diagnóstico rápido por host: `python tooling/dev.py doctor --host <host>`

## Gate de identidade

Um ambiente só pode ser considerado apto quando todos os itens abaixo forem verdadeiros:

- `OIDC_ISSUER`, `OIDC_JWKS_URL`, `OIDC_AUTHORIZATION_ENDPOINT`, `OIDC_SERVICE_ISSUER`, `OIDC_SERVICE_JWKS_URL` e `OIDC_SERVICE_TOKEN_URL` usam `https://`.
- Nenhum endpoint OIDC usa `localhost`, `127.0.0.1`, `host.docker.internal` ou domínios placeholder.
- `OIDC_USER_AUDIENCE` e `OIDC_SERVICE_AUDIENCE` estão preenchidos e distintos.
- `OIDC_ADMIN_GROUP`, `ADMIN_FACADE_CLIENT_ID` e `ADMIN_FACADE_CLIENT_SECRET` estão presentes.
- O IdP principal não depende do contêiner OIDC efêmero de evidência.
- Existe evidência por host para login OIDC, token de serviço e rollback.

## Hosts e ondas de rollout

### Wave 1: `pc2-stateful`

- Serviços: `neo4j`, `qdrant`, `ollama`
- Verificações mínimas:
  - conectividade Tailscale
  - autenticação Neo4j
  - `QDRANT_API_KEY` válida e `/healthz`
  - `ollama/api/tags`
- Critério de rollback:
  - restaurar snapshots/compose homologado anterior do PC2

### Wave 2: `pc1-control-plane`

- Serviços: `janus-api`, `janus-frontend`, `postgres`, `redis`, `rabbitmq`
- Verificações mínimas:
  - login OIDC emitido pelo IdP real
  - token de serviço do admin facade
  - `health`, `healthz` e status da API
  - health do frontend
  - `AUDIT_LEDGER_HMAC_KEY` presente
- Critério de rollback:
  - voltar imagens/configuração homologada anterior e repetir `doctor`/`readiness`

## Segredos críticos mínimos

- `ADMIN_FACADE_CLIENT_SECRET`
- `AUDIT_LEDGER_HMAC_KEY`
- `POSTGRES_PASSWORD`
- `RABBITMQ_PASSWORD`
- `NEO4J_PASSWORD`
- `QDRANT_API_KEY`

Todos devem vir de secret manager/cofre equivalente, nunca de placeholders, segredos efêmeros ou valores default.

## Execução mínima no repositório

### 1. Validar o baseline

```bash
python tooling/dev.py readiness
```

### 2. Validar o baseline junto com templates/envs locais

```bash
python tooling/dev.py readiness --env-file .env.pc1.example --env-file .env.pc2.example --format markdown --out outputs/qa/production_readiness_report.md
```

Observação: os templates de exemplo devem falhar no gate de produção enquanto contiverem placeholders. Isso é esperado e serve para impedir promoção acidental.

### 3. Rodar diagnóstico por host alvo

```bash
python tooling/dev.py doctor --host <host> --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json
```

## Pacote mínimo de evidências

Antes de qualquer versionamento/deploy, consolidar pelo menos:

- resultado do `readiness`;
- resultado do `doctor`;
- identificação dos hosts e ondas;
- plano de rollback por host;
- referência à triagem de blockers ainda aceitos para release.

## Bloqueios explícitos

Promover para produção continua bloqueado quando existir qualquer um dos itens abaixo:

- IdP OIDC RS256 efêmero em Docker como identidade principal;
- endpoint OIDC local/placeholder;
- segredo crítico em `__REQUIRED__`, vazio ou efêmero;
- ausência de validação por host;
- ausência de pacote de evidências;
- pendências críticas abertas em dados, mypy ou `npm audit` sem aceite formal.
