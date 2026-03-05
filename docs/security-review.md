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

## Achados do dia (2026-03-05)

### Checklist executado
- [x] Verificação de PII/tokens em logs de serviços (Chat, Tools, Daemon).
- [x] Análise estática com Bandit no backend (`app/`).
- [x] Verificação de dependências com `npm audit` e `pip-audit`.
- [x] Revisão dos endpoints expostos sem autenticação (Workspace e Windows Agent).

### 8. Possível Injeção de SQL (Hardcoded SQL)
- **Caminho:** `backend/app/services/dedupe_service.py` (linhas 101, 137)
- **Gravidade:** Alta
- **Descrição:** O Bandit (B608) detectou a construção de queries SQL manipulando strings diretamente através de f-strings, o que pode abrir vetor para SQL Injection caso os parâmetros `{table}` ou outros inputs não sejam estritamente controlados ou sanitizados pela ORM.
- **Ação Recomendada:** Utilizar parâmetros nomeados padrão do SQLAlchemy (`:param`) ou construtores de `Table` e objetos `update()` para evitar formatação manual de texto.

### 9. Vulnerabilidade a Ataques XML (Billion Laughs / XXE)
- **Caminho:** `backend/app/services/document_parser_service.py` (linha 111)
- **Gravidade:** Média
- **Descrição:** O parser de documentos utiliza `xml.etree.ElementTree.fromstring` para analisar dados XML não confiáveis, sendo vulnerável a ataques de expansão de entidades. Detectado pelo Bandit (B314 e B405).
- **Ação Recomendada:** Substituir o uso do pacote padrão `xml.etree` pelo pacote `defusedxml` ou desativar a resolução de entidades externas.

### 10. Risco de Execução de Subprocessos com Untrusted Input
- **Caminho:** `backend/app/services/semantic_commit_service.py` (linhas 58, 94)
- **Gravidade:** Baixa/Média
- **Descrição:** Uso de `subprocess.run` (Bandit B603) sem validação explícita ou sanitização da variável de entrada `cmd`, que executa comandos do Git no shell do sistema. Se os caminhos ou parâmetros do repositório forem controláveis externamente, pode resultar em injeção de comandos.
- **Ação Recomendada:** Assegurar que os argumentos do comando Git estejam restritos a listas seguras de strings e não possam ser manipulados através da API.

### 11. Dependências do Frontend Vulneráveis (npm audit)
- **Escopo:** `frontend/`
- **Gravidade:** Alta
- **Descrição:** O `npm audit` revelou 5 vulnerabilidades (4 High, 1 Moderate). Os pacotes impactados incluem `@hono/node-server` (Bypass de autorização), `dompurify` (Cross-site Scripting XSS), `hono` (Cookie/SSE Injection), `immutable` (Prototype Pollution) e `tar` (Path Traversal).
- **Ação Recomendada:** Executar `npm audit fix` para atualizar as versões secundárias dos pacotes vulneráveis para as versões mitigadas.

### 12. Dependência do Backend Vulnerável (pip-audit)
- **Escopo:** `backend/`
- **Gravidade:** Alta
- **Descrição:** O `pip-audit` identificou que a versão instalada do pacote `pip` (25.3) está vulnerável à CVE-2026-1703.
- **Ação Recomendada:** Atualizar a versão do `pip` para a versão recomendada (26.0) dentro do ambiente do container e CI/CD.

### 13. Exposição do Windows Agent OS Endpoints
- **Caminho:** `backend/windows_agent.py`
- **Gravidade:** Crítica
- **Descrição:** O script expõe endpoints de interação com o SO Windows (captura de tela, notificações, e TTS) pela porta 5001 usando FastAPI sem nenhum mecanismo de autenticação ou autorização.
- **Ação Recomendada:** Implementar um token ou mecanismo de autenticação baseado em cabeçalhos neste serviço auxiliar para garantir que apenas o Janus container autorizado possa invocá-lo.
