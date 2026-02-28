# Weekly Security Review

## Data de Revisão
*Automated Review*

## Checklist
- [x] PII/tokens em logs
- [x] Falta de validação
- [x] Permissões frouxas
- [x] Endpoints sem authZ
- [x] Segredos hardcoded
- [x] Ausência de rate limit
- [x] Dependências vulneráveis

## Gaps Encontrados

1. **Segredos hardcoded em configuração (backend/app/config.py)**
   - Valores padrão sensíveis estão fixados no código-fonte, como `NEO4J_PASSWORD`, `POSTGRES_PASSWORD` e `RABBITMQ_PASSWORD`.
   - **Risco:** Exposição de credenciais se as variáveis de ambiente não forem configuradas no ambiente de produção.

2. **Ausência de rate limiting em Endpoints Críticos (backend/app/api/v1/endpoints/auth.py)**
   - Os endpoints de login e refresh não contêm decoradores `@limiter.limit`.
   - **Risco:** Vulnerabilidade a ataques de força bruta (brute-force).

3. **Endpoints sem Autorização - AuthZ (backend/app/api/v1/endpoints/workspace.py)**
   - O uso de `Depends(get_collaboration_service)` não impõe autenticação, o que deixa endpoints como `add_artifact` ou `shutdown_system` desprotegidos contra acessos não autorizados.
   - **Risco:** Controle de acesso ineficaz, permitindo leitura e escrita arbitrária por agentes não autenticados.

4. **Autenticação Insegura - Trust de Header X-User-Id (backend/app/core/infrastructure/auth.py)**
   - `AUTH_TRUST_X_USER_ID_HEADER=True` habilitado por padrão em desenvolvimento permite que cabeçalhos arbitrários autentiquem usuários.
   - **Risco:** Bypass de autenticação e personificação de usuários (impersonation risk).

5. **Riscos de Logging de PII (Diversos Serviços)**
   - O `ChatEventPublisher` loga `content_preview`, o `ChatService` loga informações de mensagem sem filtro explícito e ferramentas de produtividade como o `send_email` (`productivity_tools.py`) logam endereço de e-mail e assunto. O `CollaborationService` também loga conteúdos submetidos e trocas entre agentes, o que configura alto risco de PII vazada.
   - **Risco:** Comprometimento de privacidade dos dados de usuários/clientes de forma irrestrita.

6. **Dependências Vulneráveis ou Desprotegidas (backend/requirements.txt)**
   - Ausência de arquivo lock e utilização de faixas de versões amplas para as dependências.
   - **Risco:** Riscos de supply chain attacks, incompatibilidade sistêmica e perda de estabilidade do ambiente.

## Recomendações Acionáveis
1. Eliminar valores de fallback hardcoded do `config.py` ou obrigar falha se não fornecidos via env vars em produção.
2. Adicionar limite de taxa (`rate limit`) aos endpoints de `/api/v1/auth`.
3. Injetar verificação de usuário autenticado nas rotas de `workspace`.
4. Restringir rigorosamente o recebimento de `X-User-Id` apenas a origens confiáveis (ex. API Gateway reescrevendo o header).
5. Implementar classes ou mixins de "Sanitized Logger" para garantir redação automática de PII (`email`, `telefone`, `CPF`, `senhas`) antes do print final.
6. Fixar dependências utilizando ferramentas como `pip-tools` (gerando `requirements.txt` / `requirements.lock` exato) ou `Poetry`.
