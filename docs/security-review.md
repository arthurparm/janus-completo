# Relatório Semanal de Segurança e LGPD

**Data:** 2026-03-03
**Escopo:** Backend (`janus/`) e Frontend (`front/`)
**Autor:** Janus Security Agent (Automated Scan)

## Resumo Executivo

Esta varredura identificou vulnerabilidades críticas relacionadas à autenticação e controle de acesso, além de riscos significativos de vazamento de dados (PII) em logs e configurações inseguras por padrão. A ausência de varredura automatizada de dependências e a fragilidade no rate limiting também foram notadas. Por outro lado, a configuração de headers de segurança (HSTS, CSP) apresenta-se robusta.

## 1. Vulnerabilidades Críticas (P0)

### 1.1 Bypass de Autenticação via Header `X-User-Id`
**Arquivo:** `janus/app/core/infrastructure/auth.py`
**Descrição:** O sistema confia cegamente no header `X-User-Id` para definir a identidade do usuário (`actor_user_id`) caso o token Bearer não esteja presente ou falhe.
**Risco:** Um atacante pode forjar este header em qualquer requisição para se passar por qualquer usuário do sistema, acessando dados privados e executando ações em seu nome.
**Evidência:**
```python
xuid = request.headers.get("X-User-Id")
try:
    if xuid:
        return int(xuid) # Retorna ID sem validação
```

### 1.2 Endpoints Críticos Sem Autenticação (Remote Shutdown)
**Arquivo:** `janus/app/api/v1/endpoints/workspace.py`
**Descrição:** Diversos endpoints na rota `/workspace` e `/system` não possuem a dependência de autenticação (`Depends(get_current_user)` ou similar), confiando apenas na injeção do serviço `CollaborationService`.
**Risco:** Permite que qualquer usuário (ou atacante não autenticado) envie mensagens arbitrárias entre agentes, injete artefatos e, criticamente, desligue o sistema via `POST /system/shutdown`.
**Evidência:**
```python
@router.post("/system/shutdown", tags=["Collaboration - System"])
def shutdown_system(service: CollaborationService = Depends(get_collaboration_service)):
    # Sem verificação de permissão/auth
    service.shutdown_system()
```

## 2. Riscos Altos (P1)

### 2.1 Segredos Hardcoded em Configuração
**Arquivo:** `janus/app/config.py`
**Descrição:** Senhas padrão ("change_me_...") estão definidas no código fonte para serviços críticos (Neo4j, Postgres, RabbitMQ).
**Risco:** Se implantado sem sobrescrever as variáveis de ambiente, o sistema fica exposto com credenciais conhecidas publicamente.

### 2.2 Logging de PII (Metadados e Identificadores)
**Arquivos:** `janus/app/services/chat_service.py`, `janus/app/core/tools/productivity_tools.py`, diversos outros serviços.
**Descrição:**
- `productivity_tools.py`: Loga metadados de e-mail (destinatário, assunto) e User ID no nível INFO.
- `chat_service.py` e outros: Loga `user_id` em diversas etapas do processamento.
**Risco:** Violação do princípio de minimização de dados da LGPD. Em caso de vazamento de logs, há exposição de metadados de comunicação e identificadores de usuário.

### 2.3 Ausência de Scan de Dependências (SCA)
**Arquivos:** `.github/workflows/`
**Descrição:** Não foram encontrados workflows de CI/CD configurados para rodar ferramentas de auditoria de dependências (como `npm audit`, `pip-audit`, Snyk ou Dependabot).
**Risco:** Utilização silenciosa de bibliotecas com vulnerabilidades conhecidas (CVEs).

## 3. Riscos Médios (P2)

### 3.1 Rate Limiting Fragil (Fail-Open)
**Arquivo:** `janus/app/core/infrastructure/rate_limit_middleware.py`
**Descrição:** O middleware de rate limit falha "aberto" (permite a requisição) se o Redis estiver indisponível ou se houver erro no script Lua.
**Risco:** Em um ataque de Negação de Serviço (DoS) que sobrecarregue o Redis, o mecanismo de proteção é desativado justamente quando mais necessário.

### 3.2 Acúmulo de Estado Global em Memória
**Arquivo:** `janus/app/core/tools/productivity_tools.py`
**Descrição:** Variáveis globais `_notes` e `_calendar_events` acumulam dados de usuário em memória indefinidamente.
**Risco:** Vazamento de dados em caso de dump de memória e consumo excessivo de recursos (Memory Leak funcional) em ambientes de longa duração.

## 4. Pontos Positivos

- **Security Headers:** O middleware `SecurityHeadersMiddleware` implementa corretamente HSTS, CSP restritivo, X-Content-Type-Options e X-Frame-Options, mitigando classes inteiras de ataques web (XSS, Clickjacking, MIME sniffing).

## 5. Recomendações Imediatas

1.  **Corrigir Auth Bypass (P0):** Remover a lógica que confia no header `X-User-Id` em `auth.py`. O ID do usuário deve vir *apenas* do token JWT validado.
2.  **Proteger Endpoints (P0):** Adicionar `Depends(get_current_user)` (e verificação de role de admin para shutdown) em `workspace.py`.
3.  **Sanitizar Logs (P1):** Revisar chamadas de `logger` para remover PII ou aplicar mascaramento.
4.  **Audit de Dependências (P1):** Adicionar step de `pip-audit` e `npm audit` no workflow de CI.
