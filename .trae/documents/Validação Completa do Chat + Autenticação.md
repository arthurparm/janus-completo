## Objetivo
Validar end-to-end o processo de chat e sua integração com autenticação, segurança, logs e permissões. Documentar achados e implementar correções e testes para cobrir cenários críticos.

## Resumo do que foi verificado
- Fluxo de autenticação existente: token HMAC com expiração e middleware de binding de ator.
  - Criação/verificação de token: `janus/app/core/infrastructure/auth.py:16-37`.
  - Emissão de token com checagem de ator/admin: `janus/app/api/v1/endpoints/auth.py:18-28`.
  - Binding de ator em todas as requisições: `janus/app/main.py:249-255`.
- Protocolos de segurança:
  - CORS global e validação extra em SSE: `janus/app/main.py:223-229`, `janus/app/api/v1/endpoints/chat.py:229-247`.
  - Rate limit global por IP/API key: `janus/app/core/infrastructure/rate_limit_middleware.py:31-87`.
  - Sem TLS/proxy; serviços expostos em HTTP: `docker-compose.yml (janus-api)`.
  - Headers de correlação e redaction de segredos em logs: `janus/app/core/infrastructure/correlation_middleware.py:16-87`, `janus/app/core/infrastructure/logging_config.py:62-76, 93-123`.
- Integração chat + auth:
  - Endpoints extraem `actor_user_id` e propagam em serviço/repositório: `janus/app/api/v1/endpoints/chat.py:76-85, 96-110, 153-160, 177-187, 195-205`.
  - RBAC por posse (user_id/project_id) em rename/delete/list: `janus/app/repositories/chat_repository.py:120-141, 102-119`.
  - Streaming SSE com eventos e métricas/erros: `janus/app/services/chat_service.py:601-671, 770-906`.
- Logs e auditoria:
  - Handlers de exceção padronizam 4xx/5xx com logs estruturados: `janus/app/api/exception_handlers.py:55-84, 89-111`.
  - Auditoria forte em OAuth/Productivity; chat sem auditoria dedicada.
- Testes existentes:
  - Chat SSE (integração/unidade): `janus/tests/integration/test_chat_sse.py:11-38`, `janus/tests/unit/test_chat_service_stream.py:14-36`.
  - Lacunas: sem testes de `/auth/token`, expiração/assinatura, cenários negativos de RBAC no chat.

## Problemas encontrados
- Envio de mensagem e histórico de conversa não validam posse do recurso; qualquer usuário com `conversation_id` válido pode enviar/montar histórico.
  - `send_message` não verifica `user_id` do dono da conversa: `janus/app/api/v1/endpoints/chat.py:88-139`.
  - `history` não checa propriedade: `janus/app/api/v1/endpoints/chat.py:141-151`.
- Fallback para `X-User-Id` (sem Bearer) permite forjar identidade em produção sem proxy confiável: `janus/app/core/infrastructure/auth.py:46-52`.
- CORS default aberto; falta endurecimento de headers de segurança (CSP, HSTS, X-Frame-Options, etc.).
- Sem TLS/terminação HTTPS no Compose, inclusive Prometheus/Grafana/OTEL.
- Chat sem trilha de auditoria dedicada (apenas métricas), reduz visibilidade de ações.

## Recomendações técnicas
1) Autorização por posse no chat
- Enforçar match de `user_id`/`project_id` do ator com a conversa em `send_message` e `history`.
- No SSE `stream_message`, validar propriedade antes de iniciar o stream.

2) Endurecer autenticação
- Tornar o uso de `X-User-Id` configurável e desativado por padrão em produção (`ALLOW_INSECURE_USER_ID_HEADER=false`).
- Exigir sempre `Authorization: Bearer` ou API Key válida.

3) Segurança de transporte e headers
- Introduzir proxy/TLS (nginx/traefik) com HTTPS; configurar HSTS.
- Adicionar middleware de headers seguros (CSP, X-Frame-Options, Referrer-Policy, Permissions-Policy, TrustedHostMiddleware).
- Restringir `CORS_ALLOW_ORIGINS` por ambiente; remover `[*]` como default.

4) Auditoria de chat
- Registrar eventos de chat (start/message/stream_error/done) em `ObservabilityService`.

5) Testes
- Backend: adicionar testes para `/auth/token` (sucesso/admin/negações), verificação de expiração/assinatura, RBAC negativo/positivo em chat (send/history/rename/delete/stream).
- Frontend: testes para `ChatStreamService` (reconexão, timeouts, parse errors) e fluxo com token.

## Plano de execução (após aprovação)
- Implementar checagens de posse:
  - `janus/app/api/v1/endpoints/chat.py` e `janus/app/services/chat_service.py` validar que `actor_user_id` ou `payload.user_id` correspondem ao dono da conversa.
- Introduzir flag de segurança para `X-User-Id` e ajustar `get_actor_user_id`.
- Adicionar middleware de headers de segurança e restringir CORS por configuração.
- Incluir auditoria dos eventos de chat em `ObservabilityService`.
- Criar suíte de testes:
  - Auth: emitir token para si/terceiros (admin), invalidar token expirado/assinado errado.
  - Chat RBAC: negar acesso de outro usuário a `send_message`, `history` e `stream`.
  - SSE: cenários `CircuitOpen`, `TTFTTimeout`, `MessageTooLarge` e reconexão.
- Documentar configurações de produção (TLS, CORS, rate limit) e aplicar templates `.env` seguros.

## Saídas esperadas
- Validação documentada com evidências (caminhos/linhas).
- Correções aplicadas e verificadas por testes automatizados.
- Guia de implantação segura atualizado para produção.

Confirma prosseguir com as implementações e criação dos testes?