# Relatório de Revisão de Segurança - Janus

Data de criação: 2026-03-07
Objetivo: Auditar, documentar e expurgar as vulnerabilidades do sistema que podem ser exploradas, de acordo com o Threat Model.

## Checklist de Segurança Semanal
- [ ] Executar `npm audit` no frontend para identificar vulnerabilidades de dependências.
- [ ] Executar `pip-audit` no backend para identificar vulnerabilidades em pacotes Python.
- [ ] Revisar logs de sistema para segredos ou tokens expostos inadvertidamente.
- [ ] Validar a presença de rate limiting em todos os endpoints sensíveis (ex: Autenticação).
- [ ] Verificar permissões e controles de AuthZ em rotas novas ou críticas.
- [ ] Executar análise estática (ex: Bandit) para identificar injeção de SQL ou comandos OS.

## Vulnerabilidades Abertas

### 8. Vulnerabilidade de Bypass de Autorização no `@hono/node-server` e outras dependências npm
- **Caminho:** `frontend/package.json`
- **Gravidade:** Alta
- **Descrição:** O `npm audit` detectou diversas vulnerabilidades nas dependências, incluindo o pacote `@hono/node-server` e `hono` com brechas de bypass de autorização e XSS (DOMPurify).
- **Ação Recomendada:** Atualizar dependências afetadas usando `npm audit fix` ou fixar versões seguras no `package.json`.

### 9. Risco de Injeção de SQL em Tabelas Dinâmicas
- **Caminho:** `backend/app/services/dedupe_service.py`
- **Gravidade:** Alta
- **Descrição:** Uso de f-strings para construção de nomes de tabelas dinâmicas em consultas SQL cria um potencial de injeção de SQL (alertado pelo Bandit B608).
- **Ação Recomendada:** Refatorar a construção das queries para usar parâmetros ou sanitização robusta nos nomes das tabelas (identificadores).

### 10. Ausência de Autenticação em Endpoints do Agente Windows
- **Caminho:** `backend/windows_agent.py`
- **Gravidade:** Crítica
- **Descrição:** O script expõe endpoints de interação nativa do sistema operacional (ex: `/screenshot`) via FastAPI sem qualquer mecanismo de autenticação ou autorização.
- **Ação Recomendada:** Implementar um mecanismo de autenticação de tokens ou restringir o acesso apenas a origens confiáveis (localhost/containers específicos).

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
