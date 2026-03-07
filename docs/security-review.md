# Relatório de Revisão de Segurança - Janus

Data de criação: 2026-03-01
Objetivo: Auditar, documentar e expurgar as vulnerabilidades do sistema que podem ser exploradas, de acordo com o Threat Model.

## Achados do dia (2026-03-07)

**Checklist Executado:**
- [x] Varredura incremental de commits (24h/última execução).
- [x] Checagem de ausência de validação de entrada/Auth.
- [x] Auditoria de AppSec (`npm audit` e `pip-audit`).
- [x] Análise de logs em busca de metadados sensíveis e vazamentos PII.
- [x] Triagem de dependências físicas em ambientes restritos.

### 1. Vulnerabilidade no Windows Agent (OS Capabilities Expostas)
- **Caminho:** `backend/windows_agent.py`
- **Gravidade:** Crítica
- **Descrição:** O script standalone FastAPI `windows_agent.py` expõe endpoints críticos do sistema operacional (como `/screenshot`, TTS e notificações) na porta 5001 (`0.0.0.0`) sem nenhum mecanismo de Autenticação (AuthN) ou Autorização (AuthZ).
- **Ação Recomendada:** Adicionar mecanismo de autenticação via token (ex: validação de um `X-Agent-Token`) antes de liberar acesso aos recursos do host e fechar o CORS para origens específicas, se possível.

### 2. SQL Injection Risk (Bandit B608)
- **Caminho:** `backend/app/services/dedupe_service.py`
- **Gravidade:** Alta
- **Descrição:** Potencial vulnerabilidade de SQL Injection devido ao uso de f-strings dinâmicas para a construção de nomes de tabelas nas queries SQLAlchemy.
- **Ação Recomendada:** Refatorar o SQLAlchemy para sanitizar estritamente a entrada e mapeamento da tabela ou usar identificadores parametrizados seguros da própria ORM.

### 3. Falha/Limitação na Auditoria de Dependências (AppSec)
- **Caminho:** `backend/requirements.txt`
- **Gravidade:** Baixa
- **Descrição:** O `pip-audit` falhou (Exception) devido à dependência `tflite-runtime` possuir constraints restritas de versões do Python incompatíveis com o ambiente padrão de CI/Auditoria, ofuscando a análise contínua das demais dependências.
- **Ação Recomendada:** Documentar a limitação e executar auditorias em ambientes com o python estritamente compatível para garantir cobertura completa.

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
