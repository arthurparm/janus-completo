# Auditoria de Segurança - Relatório Semanal

**Data:** 2026-02-23
**Status:** Crítico
**Auditor:** Agente de Segurança Janus (Automático + Manual)

## Resumo Executivo

A varredura desta semana identificou vulnerabilidades críticas relacionadas à autorização (AuthZ) em endpoints de colaboração e confiança indevida em headers de requisição. Também foram notadas ausências de rate limiting em endpoints de autenticação e vazamento potencial de tokens de reset de senha.

## Vulnerabilidades Críticas (P0)

### 1. Ausência de Autorização em Endpoints de Workspace
- **Local:** `backend/app/api/v1/endpoints/workspace.py`
- **Descrição:** Os endpoints `add_artifact`, `get_artifact`, `send_message`, `get_messages_for` e `shutdown_system` dependem de `get_collaboration_service`, que apenas injeta o serviço sem verificar autenticação ou permissões. Qualquer usuário (ou até bots externos se a rede permitir) pode invocar estes endpoints sem token JWT.
- **Risco:** Execução remota de comandos (shutdown), injeção de dados falsos, vazamento de mensagens entre agentes.
- **Recomendação:** Adicionar `Depends(get_current_user)` e verificação de escopo/role em todos os endpoints.

### 2. Confiança Indevida no Header `X-User-Id`
- **Local:** `backend/app/api/v1/endpoints/auth.py` (função `issue_token`)
- **Descrição:** O endpoint `/auth/token` confia no valor de `request.headers.get("X-User-Id")` para determinar o `actor_user_id`.
- **Risco:** Um atacante pode forjar este header para se passar por outro usuário ou administrador, obtendo tokens válidos para qualquer conta.
- **Recomendação:** Remover a leitura direta do header. O `actor_user_id` deve ser extraído exclusivamente do token JWT validado pelo middleware de autenticação ou `Depends(get_current_user)`.

## Riscos Altos (P1)

### 3. Ausência de Rate Limiting em Autenticação
- **Local:** `backend/app/api/v1/endpoints/auth.py`
- **Descrição:** Endpoints críticos como `/local/login`, `/local/register` e `/local/request-reset` não possuem decoradores `@limiter.limit`.
- **Risco:** Ataques de força bruta (brute-force) para descobrir senhas e enumeração de usuários.
- **Recomendação:** Implementar rate limiting estrito (ex: 5 req/min para login, 3 req/hora para reset).

### 4. Vazamento de Token de Reset de Senha
- **Local:** `backend/app/api/v1/endpoints/auth.py` (função `local_request_reset`)
- **Descrição:** O endpoint retorna o `reset_token` no corpo da resposta JSON caso a configuração permita (padrão em dev, mas arriscado se mal configurado).
- **Risco:** Se interceptado ou se a configuração vazar para produção, permite reset de senha imediato sem acesso ao email do usuário.
- **Recomendação:** Remover o token do retorno da API. O token deve ser enviado **apenas** por e-mail/log seguro.

### 5. Logging de PII (Dados Sensíveis)
- **Local:** `backend/app/services/collaboration_service.py`
- **Descrição:** O serviço loga argumentos de funções como `add_artifact` (chave, valor) e `send_message` (conteúdo).
- **Risco:** Se um usuário enviar dados sensíveis (senhas, chaves de API, dados pessoais) via chat/ferramentas, estes ficarão gravados nos logs do sistema em texto claro.
- **Recomendação:** Sanitizar logs. Não logar o `content` ou `value` de artefatos, apenas metadados (tamanho, tipo).

## Riscos Médios (P2)

### 6. Gerenciamento de Dependências
- **Local:** `backend/requirements.txt`
- **Descrição:** Uso de versões amplas e ausência de arquivo de lock (`poetry.lock` ou `pip-tools`).
- **Risco:** Instalação de versões com vulnerabilidades conhecidas (supply chain attack) ou quebra de compatibilidade em deploys futuros.
- **Recomendação:** Adotar ferramenta de lock (Poetry/uv) e scan automático de vulnerabilidades (Trivy/Safety).
