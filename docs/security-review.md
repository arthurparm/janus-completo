# Weekly Security Review

## Data da Revisão
2025-02-27

## Checklist de Segurança

### 1. Autenticação e Autorização (AuthZ/AuthN)
- [x] **Vulnerabilidade Crítica**: O header `X-User-Id` é confiado sem verificação (`AUTH_TRUST_X_USER_ID_HEADER=True`), permitindo bypass/impersonation.
  - *Recomendação*: Implementar validação criptográfica (ex: JWT verification) ou remover o bypass no ambiente de produção.
- [x] **Endpoints Desprotegidos**: Endpoints no `Workspace API` (`/workspace/artifacts/add`, `/shutdown_system`) dependem do `CollaborationService` que não valida o `get_current_user`.
  - *Recomendação*: Adicionar `Depends(get_current_user)` nos endpoints afetados no `backend/app/api/v1/endpoints/workspace.py`.

### 2. Gestão de Segredos
- [x] **Segredos Hardcoded**: O arquivo `backend/app/config.py` possui padrões (defaults) sensíveis em texto claro (ex: `NEO4J_PASSWORD`, `POSTGRES_PASSWORD`, `RABBITMQ_PASSWORD`).
  - *Recomendação*: Remover os defaults sensíveis ou forçar falha no startup se os valores padrão forem detectados em produção. A LocalResetResponse, por padrão (`AUTH_RESET_RETURN_TOKEN=False`), é segura, mas requer atenção.

### 3. Proteção Contra Abusos (Rate Limiting)
- [x] **Limitação Ausente**: Endpoints de `auth` (`/auth/login`, `/auth/refresh` em `backend/app/api/v1/endpoints/auth.py`) não possuem rate limiters (`@limiter.limit`), abrindo brecha para força bruta.
  - *Recomendação*: Adicionar `@limiter.limit` explicitamente nas rotas de login/token.
- [x] **Fail-Open Ausente**: O `RateLimitMiddleware` está configurado com `fail-closed` (retorna HTTP 503) em vez de `fail-open` quando o Redis cai.
  - *Recomendação*: Alterar a lógica para permitir a continuidade (com avisos) se o serviço de cache ficar indisponível, para não impactar a disponibilidade geral da aplicação indevidamente.

### 4. Dependências
- [x] **Broad Dependency Ranges**: O `backend/requirements.txt` especifica versões abertas e não possui lockfile, apresentando risco à estabilidade e a supply-chain attacks.
  - *Recomendação*: Implementar `pip-tools` (ex: `requirements.in` compilado para `requirements.txt` fixo) ou ferramentas como `Poetry`/`uv` para garantir lock de dependências reprodutíveis.

## Próximos Passos e Ações
Verifique `melhorias-possiveis.md` na seção "4) Ferramentas, Segurança e Governança" para os tickets rastreados a partir deste relatório.
