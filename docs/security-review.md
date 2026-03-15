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

## Achados do dia (2026-03-08)

### Checklist executado
- [x] npm audit (frontend)
- [x] pip-audit (backend) - **Falhou** (limitação ambiental registrada)
- [x] Revisão manual de código (arquivos alterados / evidências levantadas)

### 8. Possível SQL Injection via F-Strings
- **Caminho:** `backend/app/services/dedupe_service.py`
- **Gravidade:** Alta (Bandit B608)
- **Descrição:** Uso de f-strings para injeção de nomes de tabela em comandos SQL brutos (`text(f"UPDATE {table}...")`), o que, embora mitigado se os nomes das tabelas forem estáticos/controlados, constitui um padrão inseguro e aponta vulnerabilidade de injeção.
- **Ação Recomendada:** Utilizar parametrização estrita ou abstrações seguras do SQLAlchemy em vez de formatação de string direta.

### 9. Endpoints Expostos Sem Autenticação
- **Caminho:** `backend/windows_agent.py`
- **Gravidade:** Crítica
- **Descrição:** O script expõe capacidades de interação com o SO (como `/screenshot`, TTS, notificações) via FastAPI na porta 5001 sem exigir nenhum tipo de autenticação/autorização, permitindo que qualquer um na rede do container acesse estas funcionalidades.
- **Ação Recomendada:** Implementar um mecanismo de autenticação robusto (ex: tokens ou mTLS) nos endpoints.

### 10. Uso de Pseudo-Random Generators Inseguros
- **Caminho:** `backend/app/api/v1/endpoints/auto_analysis.py`
- **Gravidade:** Baixa (Bandit B311)
- **Descrição:** Identificação prévia reiterada. Geradores pseudo-aleatórios da biblioteca padrão estão em uso.
- **Ação Recomendada:** Substituir a biblioteca `random` pela `secrets` para geração criptograficamente segura.

### 11. Vulnerabilidade em Dependência do Frontend (@hono/node-server)
- **Caminho:** `frontend/package.json` / `npm audit`
- **Gravidade:** Alta
- **Descrição:** A dependência `@hono/node-server` possui falha de autorização ('authorization bypass') via caminhos estáticos mal sanitizados (`GHSA-wc8c-qw6v-h7f6`).
- **Ação Recomendada:** Atualizar a dependência para uma versão corrigida utilizando `npm update @hono/node-server` e refazer a compilação do frontend.

### Limitação de Auditoria
- **Componente:** Dependências do Backend (`pip-audit`)
- **Evidência:** Execução de `pip-audit` falhou.
- **Descrição:** Ambiente restrito ou dependências conflitantes/faltantes impediram a varredura completa do `requirements.txt`.
- **Ação Recomendada:** Garantir pré-instalação de ambiente reprodutível (lockfile) para as varreduras do `pip-audit`.

## Achados do dia (2026-03-10)

### Checklist executado
- [x] npm audit (frontend)
- [x] pip-audit (backend) - **Falhou** (limitação ambiental registrada, requisitos python version não batem e falta de lockfile/dependência em sandbox sem network acesso total).
- [x] Revisão manual de código (arquivos alterados / evidências levantadas).

### 12. Vulnerabilidades em Dependências do Frontend
- **Caminho:** `frontend/package.json` / `npm audit`
- **Gravidade:** Alta / Moderada
- **Descrição:** Múltiplas dependências do frontend foram identificadas como vulneráveis pelo `npm audit`:
  - `dompurify` (Moderada) - Cross-site Scripting vulnerability
  - `express-rate-limit` (Alta) - Bypass de rate limiting em redes dual-stack
  - `hono` (Alta) - Vulnerabilidades de injeção em atributos de cookies e SSE, e acesso a arquivo arbitrário via serveStatic
  - `immutable` (Alta) - Prototype Pollution
  - `tar` (Alta) - Hardlink Path Traversal
- **Ação Recomendada:** Executar `npm audit fix` para atualizar as dependências e resolver as vulnerabilidades encontradas.

### 13. Vulnerabilidade de Code Injection e Execução Arbitrária (OS Command Injection / shell=True)
- **Caminho:** `backend/app/core/tools/launcher_tools.py`, `backend/app/core/infrastructure/python_sandbox.py`, e `backend/app/core/tools/faulty_tools.py`
- **Gravidade:** Crítica
- **Descrição:** Uso inseguro de `subprocess.Popen` com `shell=True` permitindo Command Injection e também uso de `exec`/`eval` sem sandboxing robusto permitindo Code Injection. Identificado pelo Bandit.
- **Ação Recomendada:** Remover `shell=True` e refatorar as chamadas para array/lista. Remover usos não-seguros de `exec`/`eval` em `faulty_tools.py` e `python_sandbox.py`.

### 14. Criação de Arquivos Temporários Insegura
- **Caminho:** `backend/app/core/memory/log_aware_reflector.py`
- **Gravidade:** Baixa / Média
- **Descrição:** Presença de criação de arquivo temporário insegura via diretórios com caminhos hardcoded `/tmp` ou manipulação manual, o que pode levar a um Time-of-check to time-of-use (TOCTOU) ou ataques de colisão. Identificado pelo Bandit.
- **Ação Recomendada:** Utilizar os módulos nativos do python como `tempfile.NamedTemporaryFile` ou o gerenciamento central do `filesystem_manager`.

### 15. URL Opening Inseguro com Arbitrary Schemes
- **Caminho:** `backend/app/core/infrastructure/message_broker.py` e `backend/app/core/tools/agent_tools.py`
- **Gravidade:** Alta
- **Descrição:** Uso de rotinas de abertura de URL (como `urllib.urlopen`) que permitem abrir esquemas arbitrários (como `file://`), propiciando leitura local de arquivos indesejados (SSRF / Arbitrary File Read). Identificado pelo Bandit.
- **Ação Recomendada:** Validar ativamente que as URLs começam com `http://` ou `https://` antes de permitir qualquer requisição externa.

### 16. Exposição de Segredos Hardcoded em Scripts de Testes/Tooling
- **Caminho:** `tooling/run_api_e2e_all.py`, `benchmark_complex_process.py`, `chaos_harness.py`
- **Gravidade:** Alta
- **Descrição:** Os scripts de testes explicitamente imprimem ou efetuam log de senhas hardcoded e secrets durante sua execução, correndo sérios riscos de vazamento (Credentials Leak) nos pipelines de CI/CD.
- **Ação Recomendada:** Modificar a execução dos testes e benchmarks para ofuscar, remover do standard out ou substituir senhas reais por mock-passwords seguras (ex: `SecretStr`).

## Achados do dia (2026-03-15)

### Checklist executado
- [x] npm audit (frontend)
- [x] pip-audit (backend) - **Falhou** (comando não encontrado no ambiente atual)
- [x] Revisão manual de código (arquivos alterados / evidências levantadas). Nenhuma nova vulnerabilidade direta no backend encontrada desde a última execução.

### 17. Novas Vulnerabilidades em Dependências do Frontend
- **Caminho:** `frontend/package.json` / `npm audit`
- **Gravidade:** Alta
- **Descrição:** Novas dependências do frontend foram identificadas como vulneráveis pelo `npm audit`:
  - `@angular/compiler` (Alta) - XSS in i18n attribute bindings (`GHSA-g93w-mfhg-p222`)
  - `flatted` (Alta) - Unbounded recursion DoS in parse() revive phase (`GHSA-25h7-pfq9-p65f`)
- **Ação Recomendada:** Executar `npm audit fix` para atualizar as dependências e resolver as vulnerabilidades encontradas.
