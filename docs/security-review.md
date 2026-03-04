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

### 6. Vulnerabilidade de Execução Arbitrária de Comandos (OS Command Injection)
- **Caminho:** `backend/app/core/tools/launcher_tools.py`
- **Gravidade:** Crítica
- **Descrição:** O uso de `subprocess.Popen(f'start "" "{app_name}"', shell=True)` permite injeção de comandos arbitrários no sistema host caso `app_name` venha mal sanitizado (ex: `"calc.exe" & del *.*`). Detectado pelo linter Bandit (B602).
- **Ação Recomendada:** Remover `shell=True` e usar uma lista de argumentos para chamar o processo, ex: `subprocess.Popen(["start", '""', app_name])` ou alternativas mais seguras na stdlib de execução.

### 7. Uso de Pseudo-Random Generators Inseguros
- **Caminho:** `backend/app/api/v1/endpoints/auto_analysis.py`
- **Gravidade:** Baixa
- **Descrição:** A biblioteca padrão `random` é usada com `random.choice`, o que não é adequado para usos onde imprevisibilidade criptográfica seja necessária, embora neste contexto específico pareça gerar fatos aleatórios.
- **Ação Recomendada:** Substituir pela biblioteca `secrets` se houver possibilidade de uso em cenários seguros, ou adicionar uma exceção documentada/inline para o linter.

### 8. Acesso Não Autenticado a Endpoints de Sistema Operacional
- **Caminho:** `backend/windows_agent.py`
- **Gravidade:** Alta
- **Descrição:** O script do agente Windows inicia um servidor FastAPI expondo rotas sensíveis como `/screenshot`, `/notify` e TTS (`/speak`) totalmente sem verificação de autenticação ou chaves da API, permitindo que qualquer elemento da LAN execute ações arbitrárias na interface do host.
- **Ação Recomendada:** Proteger os endpoints com verificação via Header `X-API-Key` ou Bearer token simétrico acordado com o Container cliente, e fazer o binding preferencial via localhost seguro.

## Checklist e Gaps de Segurança

* [ ] **AuthZ em Workspaces**: Bloquear acessos anônimos para endpoints críticos em `workspace.py` (adicionar `Depends(get_current_user)`).
* [ ] **Proteção contra Brute Force**: Habilitar `@limiter.limit` em `backend/app/api/v1/endpoints/auth.py` (login/refresh).
* [ ] **Hardcoded Secrets Defaults**: Garantir bloqueio estrito de valores fallback em `config.py` (ex: `NEO4J_PASSWORD`, `POSTGRES_PASSWORD`).
* [ ] **Remoção de PII**: Evitar logar payloads integrais de requests e prever sanitização em todos os logs críticos de domínio.
* [ ] **Lock de Dependências**: Implementar geração de arquivo de lock file na etapa de CI.
* [ ] **Proteção Agent Windows**: Aplicar checagem básica de AuthN nas rotas em `windows_agent.py`.
