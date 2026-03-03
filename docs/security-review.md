# Relatório de Revisão de Segurança - Janus

Data de criação: 2026-03-01
Objetivo: Auditar, documentar e expurgar as vulnerabilidades do sistema que podem ser exploradas, de acordo com o Threat Model.

## Vulnerabilidades Abertas

### 1. Header `X-User-Id` Exploit (Impersonation)
- **Caminho:** `backend/app/core/infrastructure/auth.py`
- **Gravidade:** Crítica
- **Descrição:** O sistema lê diretamente a injeção do cabeçalho `X-User-Id` se o parâmetro `AUTH_TRUST_X_USER_ID_HEADER` estiver em `True` (o que é o padrão atual em `config.py`), permitindo manipulação irrestrita da identidade do usuário ao passar um simples cabeçalho HTTP, bypassando a camada JWT real.
- **Ação Recomendada:** Configurar o flag como falso nos defaults de produção e validar robustamente a criptografia do token de acesso injetado em Headers customizados.

### 2. Bypass de Autenticação - Shared Workspaces
- **Caminho:** `backend/app/api/v1/endpoints/workspace.py`
- **Gravidade:** Alta
- **Descrição:** Requisições via API que injetam novos artefatos (`add_artifact`) ou até disparam eventos de Desligamento do Sistema (`shutdown_system`) estão usando as injeções simples de dependência do FastAPI como `Depends(get_collaboration_service)` sem qualquer validador de sessão na camada de roteamento (ex: `Depends(get_current_user)`).
- **Ação Recomendada:** Implementar checagem de Token/Access Control nas rotas do workspace, proibindo acessos anônimos para gerenciar estados do container ou memória de agentes.

### 3. Ausência de Rate-Limiter (DDoS/Brute-Force)
- **Caminho:** `backend/app/api/v1/endpoints/auth.py`
- **Gravidade:** Média/Alta
- **Descrição:** Endpoints críticos de Autenticação (`login`, `refresh_token`, etc) carecem do decorador de segurança de tráfego (`@limiter.limit`). Ataques de força bruta contra senhas podem ser realizados e gargalos de autenticação em bancos são fáceis de explorar, causando Denial of Service e vazamento de contas (Account Takeover).
- **Ação Recomendada:** Adicionar a notação e política de `limit` do Redis a nível de rota de login e senhas.

### 4. Default Secrets Hardcoded em Configurações
- **Caminho:** `backend/app/config.py`
- **Gravidade:** Alta
- **Descrição:** Variáveis de fallback como `NEO4J_PASSWORD`, `POSTGRES_PASSWORD` e `RABBITMQ_PASSWORD` expõem os ambientes base se provisionados inadvertidamente sem injeções customizadas na infraestrutura.
- **Ação Recomendada:** Forçar bloqueio com uma validadora "Strict" (`assert env != default_secret`) ou não estipular fallbacks arriscados, exigindo `.env` bem configurado.

### 5. `LocalResetResponse` Retornando Token
- **Caminho:** `backend/app/api/v1/endpoints/auth.py`
- **Gravidade:** Média
- **Descrição:** Configuração de flag (`AUTH_RESET_RETURN_TOKEN`) permite expor diretamente o Token em fluxos de Reset.
- **Ação Recomendada:** Remover ou restringir severamente o uso dessa flag a ambientes puros de teste, certificando a injeção de config em prod.
