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

## Achados do dia (2026-03-09)

### Checklist executado
- [x] npm audit (frontend) - **Limpo / Sem novas dependências críticas**
- [x] pip-audit (backend) - **Falhou** (limitação ambiental registrada)
- [x] Revisão manual de código (arquivos alterados / evidências levantadas por Bandit e Auditoria Técnica)

### 12. Vulnerabilidades de Code Injection e Execução de Comandos (OS Command Injection e Eval)
- **Caminho:** `backend/app/core/tools/launcher_tools.py`, `backend/app/core/infrastructure/python_sandbox.py`, `backend/app/core/tools/faulty_tools.py`
- **Gravidade:** Alta (Bandit B602, B603, B102, B307)
- **Descrição:** Múltiplas instâncias de execução de comandos inseguros, incluindo uso de `shell=True` no `launcher_tools.py`, `exec` no `python_sandbox.py` e `eval` em `faulty_tools.py`.
- **Ação Recomendada:** Refatorar a execução de comandos usando sintaxes de array/lista e desativar `shell=True`. Substituir `eval` e `exec` por bibliotecas seguras ou AST parsing se essencial.

### 13. Criação de Arquivos Temporários Inseguros
- **Caminho:** `backend/app/core/memory/log_aware_reflector.py`
- **Gravidade:** Média (Bandit B108)
- **Descrição:** O arquivo usa caminhos temporários estáticos em `/tmp/janus.log`, o que pode causar colisão de nomes ou ataques de manipulação de logs entre usuários no host ou contêiner.
- **Ação Recomendada:** Utilizar módulos built-in seguros (`tempfile.NamedTemporaryFile` ou semelhante) com permissões isoladas.

### 14. Unsafe URL Opening Practices
- **Caminho:** `backend/app/core/infrastructure/message_broker.py`, `backend/app/core/tools/agent_tools.py`
- **Gravidade:** Média (Bandit B310)
- **Descrição:** Uso de `urllib.urlopen` com URLs não estritamente controladas pode permitir exploração com schemes arbitrários (como `file:/`), possibilitando leitura local não autorizada (Local File Inclusion / SSRF).
- **Ação Recomendada:** Adicionar validação de payload estrita que aceite somente schemes `http` ou `https`.
