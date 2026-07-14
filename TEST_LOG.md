# TEST_LOG

## Ciclo 1 - Base documental da meta continua

### Comandos Executados

```powershell
git status --short --branch
```

Resultado: passou; worktree iniciou limpo em `master...origin/master`.

```powershell
Get-ChildItem -LiteralPath 'H:\repos\janus-completo' -Force | Where-Object { $_.Name -in @('META.md','ROADMAP.md','NOTES.md','CHANGELOG.md','DECISIONS.md','TEST_LOG.md','TODO_TECHNICAL_DEBT.md','README.md','AGENTS.md') } | Select-Object Name,Length,LastWriteTime
```

Resultado: passou; confirmou ausencia dos sete arquivos de memoria obrigatorios antes da criacao.

```powershell
rg -n "TODO|FIXME|HACK|pass$|skip\(|xfail|type: ignore|any" backend/app qa frontend/src/app -S
```

Resultado: executado; encontrou candidatos amplos de divida tecnica, ainda nao triados individualmente.

```powershell
rg -n "pytest|ruff|mypy|npm run lint|npm run test|ng build|quality" README.md backend/README.md frontend/README.md pyproject.toml backend/pyproject.toml frontend/package.json .github/workflows -S
```

Resultado: executado com achados uteis, mas retornou erro para `pyproject.toml` inexistente no root. Evidencia suficiente para localizar gates em `backend/pyproject.toml`, `frontend/package.json` e `.github/workflows/quality-gates.yml`.

```powershell
Get-ChildItem -LiteralPath 'H:\repos\janus-completo' -Force | Where-Object { $_.Name -in @('META.md','ROADMAP.md','NOTES.md','CHANGELOG.md','DECISIONS.md','TEST_LOG.md','TODO_TECHNICAL_DEBT.md') } | Sort-Object Name | Select-Object Name,Length
```

Resultado: passou; confirmou a criacao dos sete arquivos obrigatorios.

```powershell
git diff --check
```

Resultado: passou; nenhum problema de whitespace reportado.

```powershell
rg -n "Ciclo 1|DEC-001|TD-001|meta continua|Base documental" META.md ROADMAP.md NOTES.md CHANGELOG.md DECISIONS.md TEST_LOG.md TODO_TECHNICAL_DEBT.md
```

Resultado: passou; confirmou registros centrais do ciclo, decisao e divida tecnica inicial.

### Validacao Nao Executada

- Testes backend/frontend completos nao foram executados neste ciclo porque a mudanca e documental e nao altera runtime.
- Build frontend nao foi executado pelo mesmo motivo.

### Risco Residual

- Baixo: arquivos Markdown podem divergir do estado real se ciclos futuros nao os mantiverem.

## Ciclo 2 - Remocao da vulnerabilidade critica direta no Vitest

### Comandos Executados

```powershell
npm audit --json
```

Diretorio: `frontend/`.

Resultado antes da correcao: reportou 26 vulnerabilidades, incluindo 1 critica em `vitest <3.2.6`.

```powershell
npm update vitest --save-dev
```

Diretorio: `frontend/`.

Resultado: passou; alterou 12 pacotes e atualizou o lockfile. Aviso observado: `npm warn allow-scripts` para pacotes com scripts de instalacao pendentes de aprovacao.

```powershell
node -p "require('./package-lock.json').packages['node_modules/vitest'].version"
```

Diretorio: `frontend/`.

Resultado: `3.2.6`.

```powershell
npm audit --json
```

Diretorio: `frontend/`.

Resultado depois da correcao: 0 criticas; 30 vulnerabilidades restantes, sendo 2 low, 13 moderate e 15 high.

```powershell
npm run test -- --run src/app/core/services/system-status.spec.ts src/app/shared/components/ui/system-hud/system-hud.spec.ts
```

Diretorio: `frontend/`.

Resultado: passou; 2 arquivos, 21 testes, Vitest `3.2.6`.

```powershell
npm run lint
```

Diretorio: `frontend/`.

Resultado: passou.

```powershell
npx ng build --configuration development
```

Diretorio: `frontend/`.

Resultado: passou; bundle gerado em `frontend/dist/janus-angular`.

### Validacao Nao Executada

- `npm run test` completo nao foi executado neste ciclo; validacao focada cobriu specs recentes de Health/HUD com o runner atualizado.
- `npm audit fix` nao foi executado para evitar atualizacao ampla sem analise.

### Risco Residual

- Restam 15 vulnerabilidades high e 13 moderate no audit frontend.
- Scripts de instalacao pendentes de aprovacao pelo mecanismo `allow-scripts` devem ser revisados em ciclo separado.

## Ciclo 3 - Patches seguros da linha Angular 20

### Comandos Executados

```powershell
npm audit --json
```

Diretorio: `frontend/`.

Resultado antes da correcao: 30 vulnerabilidades; 2 low, 13 moderate, 15 high, 0 critical.

```powershell
npm outdated --json @angular/core @angular/common @angular/compiler @angular/compiler-cli @angular/animations @angular/forms @angular/platform-browser @angular/platform-browser-dynamic @angular/router @angular/service-worker @angular/build @angular/cli
```

Diretorio: `frontend/`.

Resultado: patches disponiveis na major 20 para runtime `20.3.25` e build/CLI `20.3.30`.

```powershell
npm update @angular/animations @angular/common @angular/compiler @angular/compiler-cli @angular/core @angular/forms @angular/platform-browser @angular/platform-browser-dynamic @angular/router @angular/service-worker @angular/build @angular/cli --save
```

Diretorio: `frontend/`.

Resultado: passou; adicionou 17 pacotes, removeu 10 e alterou 46. Avisos: deprecacao de `@angular/animations` e `@angular/platform-browser-dynamic`; cleanup falhou em diretorio temporario de `node_modules` por `esbuild.exe` bloqueado; `allow-scripts` continua pendente para alguns pacotes.

```powershell
node -e "const p=require('./package-lock.json').packages; for (const n of ['@angular/core','@angular/common','@angular/compiler','@angular/compiler-cli','@angular/build','@angular/cli','@angular/router','@angular/service-worker','vitest']) console.log(n, p['node_modules/'+n]?.version)"
```

Diretorio: `frontend/`.

Resultado: confirmou `@angular/core/common/compiler/router/service-worker` em `20.3.25`, `@angular/build` e `@angular/cli` em `20.3.30`, `vitest` em `3.2.6`.

```powershell
npm audit --json
```

Diretorio: `frontend/`.

Resultado depois da correcao: 19 vulnerabilidades; 5 low, 10 moderate, 4 high, 0 critical.

```powershell
npm run test
```

Diretorio: `frontend/`.

Resultado: passou; 32 arquivos, 168 testes.

```powershell
npm run lint
```

Diretorio: `frontend/`.

Resultado: passou.

```powershell
npx ng build --configuration development
```

Diretorio: `frontend/`.

Resultado: passou; bundle gerado em `frontend/dist/janus-angular`.

### Risco Residual

- Restam 4 vulnerabilidades high no audit frontend.
- Restam vulnerabilidades low/moderate em `@angular/build`, `@angular/cli`, `DOMPurify`, `hono`, `protobufjs`, `ws` e transientes.
- Warnings de deprecacao Angular exigem ciclo separado porque podem implicar refatoracao de API.

## Ciclo 4 - Atualizacao segura do DOMPurify

### Comandos Executados

```powershell
npm audit --json
```

Diretorio: `frontend/`.

Resultado antes da correcao: 19 vulnerabilidades; 5 low, 10 moderate, 4 high, 0 critical. `dompurify <=3.4.10` aparecia como vulneravel.

```powershell
npm update dompurify --save
```

Diretorio: `frontend/`.

Resultado: passou; alterou 1 pacote. Aviso observado: `allow-scripts` ainda possui pacotes pendentes de aprovacao.

```powershell
node -e "const pkg=require('./package.json'); const lock=require('./package-lock.json'); console.log('package dompurify', pkg.dependencies.dompurify); console.log('lock dompurify', lock.packages['node_modules/dompurify'].version)"
```

Diretorio: `frontend/`.

Resultado: `package dompurify ^3.4.11`; `lock dompurify 3.4.11`.

```powershell
npm audit --json
```

Diretorio: `frontend/`.

Resultado depois da correcao: 18 vulnerabilidades; 5 low, 9 moderate, 4 high, 0 critical. `dompurify` nao apareceu mais no mapa de vulnerabilidades.

```powershell
npm run test -- --run src/app/shared/services/markdown.service.spec.ts src/app/shared/pipes/markdown.pipe.spec.ts
```

Diretorio: `frontend/`.

Resultado: passou; 2 arquivos, 5 testes.

```powershell
npm run test
```

Diretorio: `frontend/`.

Resultado: passou; 32 arquivos, 168 testes.

```powershell
npm run lint
```

Diretorio: `frontend/`.

Resultado: passou.

```powershell
npx ng build --configuration development
```

Diretorio: `frontend/`.

Resultado: passou; bundle gerado em `frontend/dist/janus-angular`.

```powershell
git diff --check
```

Diretorio: root do repositorio.

Resultado: passou; nenhum problema de whitespace reportado.

### Validacao Nao Executada

- Nao foi executado teste manual em browser para todos os consumidores de Markdown; a cobertura automatizada focada e a suite frontend completa passaram.
- Nao foi executado `npm audit fix --force` por risco de upgrades major e mudancas fora do escopo.

### Risco Residual

- Restam 18 vulnerabilidades no audit frontend: 5 low, 9 moderate e 4 high.
- Highs transientes restantes envolvem `@grpc/grpc-js`, `hono`, `protobufjs` e `ws`; exigem triagem propria.
- `allow-scripts` continua pendente e deve ser tratado como decisao de supply chain, nao como detalhe automatico de instalacao.

## Ciclo 5 - Guardrail de Python suportado no tooling backend

### Baseline

```powershell
$env:PYTHONPATH='backend'; pytest -q qa/test_health_endpoint_contract.py qa/test_workers_status_contract.py qa/test_chat_endpoint_contract.py
```

Resultado antes da correcao: falhou durante coleta, antes de executar contratos funcionais, com `ModuleNotFoundError` para `aio_pika` e `msgpack`.

Evidencia contextual: o host usa Python `3.13.13`; `backend/pyproject.toml` exige `>=3.11,<3.13`; `backend/requirements.txt` contem dependencias essenciais com markers `python_version < "3.13"`.

### Comandos Executados

```powershell
python -m pytest -q qa/test_dev_cli_doctor.py
```

Resultado: passou; 4 testes.

```powershell
ruff check --config backend/pyproject.toml tooling/dev.py qa/test_dev_cli_doctor.py
```

Resultado: passou.

```powershell
python tooling/dev.py qa
```

Resultado: falhou cedo conforme esperado em Python `3.13.13`, com mensagem `Unsupported Python runtime for Janus backend`.

```powershell
python tooling/dev.py setup
```

Resultado: falhou cedo conforme esperado em Python `3.13.13`, antes de executar `pip install`.

```powershell
git diff --check
```

Resultado: passou; nenhum problema de whitespace reportado.

### Validacao Nao Executada

- Contratos backend reais de health/chat/workers nao foram executados com sucesso porque o host atual esta em Python 3.13, fora da faixa suportada.
- `python tooling/dev.py qa` completo deve ser executado em Python 3.11/3.12 ou no fluxo Docker oficial.

### Risco Residual

- O guardrail melhora a confiabilidade de operacao local, mas nao valida o comportamento funcional dos endpoints.
- A documentacao fora dos tres arquivos atualizados ainda pode conter mencoes genericas a `Python 3.11+`; essas ocorrencias devem ser revisadas em ciclo separado se continuarem causando ambiguidade.

## Ciclo 6 - QA oficial funcionando em Python 3.12 no Windows

### Baseline

```powershell
py -0p
```

Resultado: host possui Python 3.13 padrao e Python 3.12 disponivel em `C:\Users\arthu\AppData\Local\Programs\Python\Python312\python.exe`.

```powershell
py -3.12 -c "import sys; print(sys.executable); import aio_pika, msgpack, fastapi, pytest; print('deps-ok')"
```

Resultado: passou; dependencias backend essenciais disponiveis no Python 3.12.

```powershell
$env:PYTHONPATH='backend'; py -3.12 -m pytest -q qa/test_health_endpoint_contract.py qa/test_workers_status_contract.py qa/test_chat_endpoint_contract.py
```

Resultado: passou; 27 testes, 1 warning de dependencia LangGraph.

```powershell
py -3.12 tooling/dev.py qa
```

Resultado antes da correcao: backend critico passou com 64 testes, mas o comando falhou ao chamar `npm run lint` com `FileNotFoundError: [WinError 2]`.

### Comandos Executados Apos Correcao

```powershell
$env:PYTHONPATH='backend'; py -3.12 -m pytest -q qa/test_api_visibility_endpoints.py
```

Resultado: passou; 15 testes, 1 warning de dependencia LangGraph.

```powershell
py -3.12 -m pytest -q qa/test_dev_cli_doctor.py qa/test_api_visibility_endpoints.py
```

Resultado: passou; 19 testes, 1 warning de dependencia LangGraph.

```powershell
ruff check --config backend/pyproject.toml tooling/dev.py qa/test_dev_cli_doctor.py qa/test_api_visibility_endpoints.py
```

Resultado: passou.

```powershell
py -3.12 tooling/dev.py qa
```

Resultado: passou completo:

- backend critico: 64 testes passed;
- frontend lint: passou;
- frontend tests: 32 arquivos, 168 testes passed;
- frontend build development: passou.

### Validacao Nao Executada

- `python tooling/dev.py up` nao foi executado; nao houve boot real de PC2/PC1 via Docker neste ciclo.
- Nao houve teste browser manual contra backend rodando em `localhost:8000`.

### Risco Residual

- Ainda falta validacao full-stack com infraestrutura PC2/PC1 ativa.
- O warning `Browserslist: browsers data (caniuse-lite) is 6 months old` permanece e pode ser tratado em ciclo separado.

## Ciclo 7 - Boot real PC2/PC1 pelo tooling oficial

### Baseline

```powershell
docker --version
docker compose version
py -3.12 --version
```

Resultado: Docker `29.6.1`, Docker Compose `v5.1.4`, Python `3.12.10`.

```powershell
py -3.12 tooling/dev.py up
```

Resultado antes das correcoes: falhou com `janus_api_pc1 unhealthy`.

Evidencia de falhas observadas:

- logs do API: `SettingsError` ao parsear listas vazias do Compose;
- logs do API: `ImportError` em `langchain.tools`;
- logs do API: timeout de Qdrant via `100.88.71.49`;
- health do Qdrant: `/bin/sh: 1: curl: not found`;
- logs do Neo4j: multiplas settings invalidas e, depois, memoria fixa acima do limite local.

### Comandos Executados Apos Correcao

```powershell
ruff check --config backend/pyproject.toml tooling/dev.py qa/test_dev_cli_doctor.py backend/app/config.py
```

Resultado: passou.

```powershell
py -3.12 -m pytest -q qa/test_dev_cli_doctor.py
```

Resultado: passou; 5 testes.

```powershell
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 config --quiet
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 config --quiet
```

Resultado: passou; Compose emitiu apenas warning de atributo `version` obsoleto.

```powershell
py -3.12 -m pytest -q qa/test_tool_executor_policy_guards.py qa/test_api_visibility_endpoints.py qa/test_dev_cli_doctor.py
```

Resultado: passou; 36 testes, 1 warning de dependencia LangGraph.

```powershell
py -3.12 tooling/dev.py up
```

Resultado: passou; health checks do tooling passaram.

```powershell
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 ps
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 ps
```

Resultado final: API, frontend, Neo4j, Qdrant, Ollama, Postgres, Redis e RabbitMQ estavam `healthy`.

```powershell
py -3.12 tooling/dev.py qa
```

Resultado: passou completo:

- backend critico: 64 testes passed;
- frontend lint: passou;
- frontend tests: 32 arquivos, 168 testes passed;
- frontend build development: passou.

```powershell
py -3.12 tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.local.json
```

Resultado: falhou com `overall_ok=false`; `health_ok=true`, `deps_tcp_ok=true`, `config_ok=true`, `deps_http_ok=false`. O JSON foi gerado em `outputs/qa/quick_diagnostics_report.local.json`.

### Validacao Nao Executada

- Nao foi validada uma conversa real com resposta LLM porque `ollama list` retornou vazio e o init ainda baixava `gpt-oss:20b`.
- Nao foi feito teste browser manual do fluxo de chat.

### Risco Residual

- Janus sobe e passa health/QA, mas o caminho de inferencia local ainda nao esta funcional sem modelo Ollama instalado.
- `tooling/dev.py doctor` precisa distinguir diagnostico local de diagnostico split PC1/PC2.

## Ciclo 8 - Validacao do diagnostico local vs split

### Comandos Executados

```powershell
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 ps
docker exec janus_ollama_pc2 ollama list
docker logs janus_api_pc1 --tail 80
```

Resultado: falhou nesta retomada porque Docker Desktop nao estava acessivel pelo pipe `npipe:////./pipe/dockerDesktopLinuxEngine`.

```powershell
py -3.12 -m pytest -q qa/test_dx007_quick_diagnostics_cli.py qa/test_dev_cli_doctor.py
```

Resultado: passou; 9 testes.

```powershell
ruff check --config backend/pyproject.toml tooling/quick_diagnostics.py qa/test_dx007_quick_diagnostics_cli.py tooling/dev.py qa/test_dev_cli_doctor.py
```

Resultado: passou.

### Validacao Nao Executada

- `py -3.12 tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.local.json` nao foi reexecutado porque Docker Desktop estava indisponivel.
- Nao foi validado fluxo real de chat/LLM via API nesta sessao pelo mesmo bloqueio operacional.

### Risco Residual

- A correcao do diagnostico esta coberta por testes de contrato, mas ainda precisa ser comprovada contra containers reais.
- O caminho funcional de inferencia continua pendente ate uma chamada real retornar resposta LLM atraves do Janus.

## Ciclo 9 - Validacao runtime de LLM e chat

### Comandos Executados

```powershell
docker version
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 ps
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 ps
docker exec janus_ollama_pc2 ollama list
```

Resultado: Docker voltou a responder; containers principais estavam healthy; Ollama tinha `deepseek-coder:6.7b` e `gpt-oss:20b`.

```powershell
py -3.12 tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.local.json
```

Resultado: passou; `overall_ok=true`, `health_ok=true`, `deps_http_ok=true`, `deps_tcp_ok=true`, `config_ok=true`.

```powershell
Invoke-RestMethod -Uri http://localhost:8000/api/v1/llm/invoke -Method Post ...
```

Payload: `prompt="Responda apenas: JANUS_OK"`, `role=orchestrator`, `priority=local_only`.

Resultado: passou; resposta `JANUS_OK`, `provider=ollama`, `model=gpt-oss:20b`.

```powershell
PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_message_orchestration_service.py backend/tests/unit/test_core_infrastructure_rate_limit_middleware.py
```

Resultado: passou; 25 testes.

```powershell
ruff check --config backend/pyproject.toml backend/app/core/infrastructure/rate_limit_middleware.py backend/tests/unit/test_core_infrastructure_rate_limit_middleware.py backend/app/services/chat/message_orchestration_service.py backend/tests/unit/test_message_orchestration_service.py
```

Resultado: passou.

```powershell
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d --build janus-api
```

Resultado: build passou, mas a API ficou unhealthy porque o comando focado nao aplicou os overrides locais de PC2; logs mostraram timeout em Qdrant e tentativa de Neo4j em `100.88.71.49`.

```powershell
$env:NEO4J_URI='bolt://host.docker.internal:7687'
$env:QDRANT_HOST='host.docker.internal'
$env:OLLAMA_HOST='http://host.docker.internal:11434'
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d janus-api
```

Resultado: API recriada e ficou healthy.

```powershell
# Registro local, chat/start e chat/message via API real
POST /api/v1/auth/local/register
POST /api/v1/chat/start
POST /api/v1/chat/message
```

Resultado final: passou; usuario `4`, conversa `7`, resposta `Janus: Dois mais dois e igual a quatro.`, `provider=ollama`, `model=gpt-oss:20b`.

### Falhas Observadas no Caminho

- `/api/v1/chat/start` retornou 503 `Rate limiter unavailable` antes do fallback local de chat.
- Token manual com usuario inexistente gerou violacao de FK em `sessions.user_id`; a validacao final usou auth local real.
- Mensagens comuns cairam em `secret_memory` antes da checagem explicita de recall.

### Validacao Nao Executada

- `py -3.12 tooling/dev.py qa` completo nao foi reexecutado apos o ciclo por custo de tempo.

### Risco Residual

- Fallback local do rate limiter nao substitui Redis para limite distribuido.
- Compose focado manual precisa dos mesmos overrides locais do `tooling/dev.py up`; caso contrario a API tenta topologia split.

## Ciclo 10 - Validacao do audit ledger HMAC

### Comandos Executados

```powershell
docker exec janus_api_pc1 python -c "from app.config import settings; print(bool(getattr(settings,'AUDIT_LEDGER_HMAC_KEY',None)))"
```

Resultado inicial: `False`.

```powershell
py -3.12 -m pytest -q qa/test_dx007_quick_diagnostics_cli.py backend/tests/unit/test_core_infrastructure_rate_limit_middleware.py backend/tests/unit/test_message_orchestration_service.py
```

Resultado: passou; 29 testes.

```powershell
ruff check --config backend/pyproject.toml tooling/quick_diagnostics.py qa/test_dx007_quick_diagnostics_cli.py backend/app/core/security/secret_validator.py backend/app/core/infrastructure/rate_limit_middleware.py backend/app/services/chat/message_orchestration_service.py backend/tests/unit/test_core_infrastructure_rate_limit_middleware.py backend/tests/unit/test_message_orchestration_service.py
```

Resultado: passou apos `ruff --fix` organizar imports em `secret_validator.py`.

```powershell
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 config --quiet
```

Resultado antes da chave: falhou com `required variable AUDIT_LEDGER_HMAC_KEY is missing a value`.

Resultado apos persistir a chave local: passou.

```powershell
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d janus-api
```

Resultado: API recriada e ficou healthy.

```powershell
py -3.12 tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.local.json
```

Resultado: passou; `overall_ok=true`.

```powershell
POST /api/v1/auth/local/register
docker logs janus_api_pc1 --since <ultimos 3 minutos> | Select-String 'audit_ledger_append_failed|AUDIT_LEDGER_HMAC_KEY|POST /api/v1/auth/local/register'
```

Resultado: registro retornou 200; logs mostraram o POST e nao mostraram novo `audit_ledger_append_failed`.

### Risco Residual

- O valor da chave nao foi impresso nem registrado; precisa ser tratado como segredo local.

## Ciclo 11 - Validacao do upgrade Qdrant

### Comandos Executados

```powershell
docker pull qdrant/qdrant:v1.18.2
```

Resultado: passou; imagem baixada com digest `sha256:75eab8c4ba42096724fdcfde8b4de0b5713d529dde32f285a1f86fdcb2c9e50c`.

```powershell
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 config --quiet
```

Resultado: passou; Docker Compose emitiu apenas aviso nao bloqueante de atributo `version` obsoleto.

```powershell
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d qdrant
```

Resultado: passou; `janus_qdrant_pc2` recriado com `qdrant/qdrant:v1.18.2` e status `healthy`.

```powershell
GET http://localhost:6333/
```

Resultado: passou; Qdrant retornou `version=1.18.2`.

```powershell
GET http://localhost:6333/collections
```

Resultado: passou; colecoes `global_chat`, `global_docs`, `global_memory`, `global_secret` e `janus_episodic_memory` listadas.

```powershell
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 restart janus-api
docker logs janus_api_pc1 --since '2026-07-13T17:17:34Z' | Select-String 'Qdrant client version|incompatible|Api key is used with an insecure connection|audit_ledger_append_failed'
```

Resultado: nao houve warning de incompatibilidade Qdrant nem `audit_ledger_append_failed`; permaneceram warnings de API key sobre conexao insegura HTTP.

```powershell
py -3.12 tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json
```

Resultado: passou; `overall_ok=true`.

```powershell
POST /api/v1/llm/invoke
```

Resultado: passou; resposta `JANUS_QDRANT_OK`, `provider=ollama`, `model=gpt-oss:20b`.

### Risco Residual

- O warning de transporte inseguro do Qdrant permanece. O proximo ciclo deve decidir entre TLS local/split, rede privada estrita ou supressao documentada somente se o risco for aceito formalmente.

## Ciclo 12 - Validacao do suporte TLS Qdrant

### Comandos Executados

```powershell
PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_dev_cli_doctor.py
```

Resultado: passou; 8 testes.

```powershell
ruff check --config backend/pyproject.toml backend/app/core/memory/qdrant_client_config.py backend/app/core/memory/memory_core.py backend/app/core/memory/enhanced_qdrant_client.py backend/app/db/vector_store.py backend/tests/unit/test_qdrant_client_config.py
```

Resultado: passou.

```powershell
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 config --quiet
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 config --quiet
```

Resultado: ambos passaram; Compose emitiu apenas aviso nao bloqueante de atributo `version` obsoleto.

```powershell
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d qdrant
```

Resultado: passou; `janus_qdrant_pc2` ficou healthy com TLS desativado por default.

```powershell
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d janus-api
```

Resultado: passou com overrides locais de PC2; `janus_api_pc1` ficou healthy.

```powershell
python tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json
```

Resultado: passou; `overall_ok=true`.

```powershell
POST /api/v1/llm/invoke
```

Resultado: passou; resposta `JANUS_TLS_SUPPORT_OK`, `provider=ollama`, `model=gpt-oss:20b`.

### Falhas Observadas no Caminho

- Primeira execucao de teste falhou sem `PYTHONPATH=backend`; reexecutado com o contrato correto do monorepo.
- Testes detectaram conversao indevida de caminho Linux para barras invertidas no Windows; corrigido preservando `QDRANT_TLS_CA_CERT` como string literal.
- Primeira chamada `/health` ocorreu enquanto o container ainda estava em `health: starting`; apos aguardar, API ficou healthy.

### Risco Residual

- TLS nao foi ativado fim a fim porque o ambiente ainda nao tem certificado/chave/CA provisionados.

## Ciclo 13 - Validacao TLS Qdrant fim a fim

### Comandos Executados

```powershell
PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_dx007_quick_diagnostics_cli.py qa/test_dev_cli_doctor.py
```

Resultado: passou; 13 testes.

```powershell
ruff check --config backend/pyproject.toml tooling/generate_qdrant_tls_cert.py tooling/quick_diagnostics.py qa/test_dx007_quick_diagnostics_cli.py backend/app/core/memory/qdrant_client_config.py backend/tests/unit/test_qdrant_client_config.py
```

Resultado: passou.

```powershell
py -3.12 tooling/generate_qdrant_tls_cert.py --include-env-hosts
```

Resultado: passou; gerou `ca.pem`, `cert.pem`, `key.pem` e `SAN.txt` em `.secrets/qdrant`.

```powershell
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d qdrant
```

Resultado: passou; Qdrant ficou healthy com TLS ativo. Logs mostraram `TLS enabled for REST API`.

```powershell
py -3.12 -c "requests.get('https://localhost:6333/', verify='.secrets/qdrant/ca.pem')"
```

Resultado: passou; HTTP 200 e `version=1.18.2`.

```powershell
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d janus-api
```

Resultado: passou com overrides locais de host; API ficou healthy com `QDRANT_HTTPS=true` e CA montada.

```powershell
python tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json
```

Resultado: passou; `overall_ok=true`; `qdrant_health.url=https://localhost:6333/healthz`.

```powershell
docker logs janus_api_pc1 --since '2026-07-13T17:35:23Z'
```

Resultado: `qdrant_incompatibility_warning_count=0`, `insecure_connection_warning_count=0`, `tls_error_count=0`.

```powershell
POST /api/v1/llm/invoke
```

Resultado: passou; resposta `JANUS_QDRANT_TLS_OK`, `provider=ollama`, `model=gpt-oss:20b`.

### Falhas Observadas no Caminho

- A primeira tentativa de persistir flags TLS nos `.env` locais falhou ao adicionar chaves novas por lista fixa do PowerShell; repetido com lista mutavel e concluido.
- A primeira chamada direta a `/collections` via Python falhou porque a chave Qdrant nao foi exportada para o subprocesso; repetida sem imprimir segredo e retornou as colecoes esperadas.
- A validacao final inicialmente encontrou teste dependente do `.env.pc1` local com `QDRANT_HTTPS=true`; `build_report` passou a aceitar override explicito `qdrant_https` para manter testes deterministicos.

### Risco Residual

- Material TLS local e adequado para desenvolvimento/ambiente controlado, mas nao define rotacao nem distribuicao de CA para producao.

## Ciclo 14 - Validacao de snapshot Qdrant por TLS

### Comandos Executados

```powershell
PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_data_plane_backup_restore.py backend/tests/unit/test_qdrant_client_config.py qa/test_dx007_quick_diagnostics_cli.py qa/test_dev_cli_doctor.py
```

Resultado: passou; 19 testes.

```powershell
ruff check --config backend/pyproject.toml backend/scripts/data_plane_backup_restore.py backend/tests/unit/test_data_plane_backup_restore.py tooling/quick_diagnostics.py qa/test_dx007_quick_diagnostics_cli.py tooling/generate_qdrant_tls_cert.py
```

Resultado: passou.

```powershell
python tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json
```

Resultado: passou; `overall_ok=true`.

```powershell
py -3.12 backend/scripts/data_plane_backup_restore.py backup --components qdrant --qdrant-url https://localhost:6333 --qdrant-api-key <redacted> --qdrant-ca-cert .secrets/qdrant/ca.pem --output-dir outputs/qa/data-plane-backups --run-id qdrant-tls-smoke-20260713
```

Resultado: passou; manifest em `outputs/qa/data-plane-backups/qdrant-tls-smoke-20260713/manifest.json`; snapshots baixados para `global_chat`, `global_docs`, `global_memory`, `global_secret` e `janus_episodic_memory`, todos com SHA-256 registrado.

```powershell
py -3.12 backend/scripts/data_plane_backup_restore.py verify --components qdrant --qdrant-url https://localhost:6333 --qdrant-api-key <redacted> --qdrant-ca-cert .secrets/qdrant/ca.pem --output-dir outputs/qa/data-plane-backups --run-id qdrant-tls-verify-20260713
```

Resultado: passou; Qdrant `version=1.18.2`, `status=ok`; `global_chat.points_count=5`, demais colecoes com `points_count=0` neste momento.

### Risco Residual

- Restore real nao foi executado no Qdrant ativo; deve ser validado em ambiente descartavel com snapshot recente.

## Ciclo 15 - Validacao de restore Qdrant descartavel

### Comandos Executados

```powershell
docker run --rm -d --name janus_qdrant_restore_test -p 16333:6333 \
  -e QDRANT__SERVICE__API_KEY=<redacted> \
  -e QDRANT__SERVICE__ENABLE_TLS=true \
  -e QDRANT__TLS__CERT=/qdrant/tls/cert.pem \
  -e QDRANT__TLS__KEY=/qdrant/tls/key.pem \
  -e QDRANT__TLS__CA_CERT=/qdrant/tls/ca.pem \
  -v ./.secrets/qdrant:/qdrant/tls:ro \
  qdrant/qdrant:v1.18.2
```

Resultado: passou; Qdrant temporario respondeu em `https://localhost:16333`.

```powershell
py -3.12 backend/scripts/data_plane_backup_restore.py restore --components qdrant --qdrant-url https://localhost:16333 --qdrant-api-key <redacted> --qdrant-ca-cert .secrets/qdrant/ca.pem --restore-dir outputs/qa/data-plane-backups/qdrant-tls-smoke-20260713 --output-dir outputs/qa/data-plane-backups --run-id qdrant-tls-restore-test-20260713-ca
```

Resultado: passou; 5 etapas de restore completas.

```powershell
py -3.12 backend/scripts/data_plane_backup_restore.py verify --components qdrant --qdrant-url https://localhost:16333 --qdrant-api-key <redacted> --qdrant-ca-cert .secrets/qdrant/ca.pem --output-dir outputs/qa/data-plane-backups --run-id qdrant-tls-restore-verify-20260713-ca
```

Resultado: passou; Qdrant `version=1.18.2`, `status=ok`, 5 colecoes verificadas.

```powershell
docker logs janus_qdrant_restore_test | Select-String 'Failed to load CA certificate|cacert.pem|No such file'
```

Resultado: `ca_warning_count=0` apos configurar `QDRANT__TLS__CA_CERT`.

```powershell
docker rm -f janus_qdrant_restore_test
```

Resultado: container temporario removido.

```powershell
PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_data_plane_backup_restore.py backend/tests/unit/test_qdrant_client_config.py qa/test_dx007_quick_diagnostics_cli.py qa/test_dev_cli_doctor.py
```

Resultado: passou; 19 testes.

```powershell
ruff check --config backend/pyproject.toml backend/scripts/data_plane_backup_restore.py backend/tests/unit/test_data_plane_backup_restore.py tooling/quick_diagnostics.py qa/test_dx007_quick_diagnostics_cli.py tooling/generate_qdrant_tls_cert.py
```

Resultado: passou.

```powershell
docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d qdrant
Invoke-RestMethod http://localhost:8000/health
python tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json
```

Resultado: Qdrant ativo healthy, API healthy, doctor `overall_ok=true`.

### Falhas Observadas no Caminho

- Primeira execucao de restore temporario passou, mas logs mostraram warning interno de CA do Qdrant. A configuracao foi corrigida com `QDRANT__TLS__CA_CERT=/qdrant/tls/ca.pem` e o restore foi repetido com `ca_warning_count=0`.
- Um comando `ruff` incluiu `docker-compose.pc2.yml` por engano; `ruff` tentou parsear YAML como Python. Reexecutado com escopo correto e passou.

### Risco Residual

- Ainda falta testar rotina completa em host remoto/PC2 com politica de retencao/offsite.

## Ciclo 16 - Validacao de retencao de backups

### Comandos Executados

```powershell
PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_data_plane_backup_restore.py
```

Resultado inicial: falhou porque `prune` herdava captura de versoes de Postgres/Neo4j/Qdrant e tentava acessar `janus_postgres`; corrigido para `prune` usar `versions.status=skipped`.

```powershell
PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_data_plane_backup_restore.py
```

Resultado apos correcao: passou; 8 testes.

```powershell
py -3.12 backend/scripts/data_plane_backup_restore.py prune --output-dir outputs/qa/data-plane-backups --run-id prune-dry-run-20260713 --retention-days 0 --retain-last 3
```

Resultado: passou; `candidate_count=3`, todos `status=would-delete`, nenhuma remocao executada.

```powershell
py -3.12 backend/scripts/data_plane_backup_restore.py prune --output-dir outputs/qa/data-plane-backups --run-id prune-policy-default-20260713
```

Resultado: passou; politica padrao `retention_days=14`, `retain_last=5`, `candidate_count=0`.

```powershell
PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_data_plane_backup_restore.py backend/tests/unit/test_qdrant_client_config.py qa/test_dx007_quick_diagnostics_cli.py qa/test_dev_cli_doctor.py
```

Resultado: passou; 21 testes.

```powershell
ruff check --config backend/pyproject.toml backend/scripts/data_plane_backup_restore.py backend/tests/unit/test_data_plane_backup_restore.py tooling/quick_diagnostics.py qa/test_dx007_quick_diagnostics_cli.py tooling/generate_qdrant_tls_cert.py
```

Resultado: passou.

```powershell
python tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json
```

Resultado: passou; `overall_ok=true`.

### Risco Residual

- Nao foi executado `--prune-apply` no diretorio real de `outputs/qa`; remocao real deve depender de aprovacao operacional.

## Ciclo 17 - Validacao de integridade antes de restore

### Comandos Executados

```powershell
PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_data_plane_backup_restore.py backend/tests/unit/test_qdrant_client_config.py qa/test_dx007_quick_diagnostics_cli.py qa/test_dev_cli_doctor.py
```

Resultado inicial apos implementacao: passou; 23 testes.

```powershell
ruff check --config backend/pyproject.toml backend/scripts/data_plane_backup_restore.py backend/tests/unit/test_data_plane_backup_restore.py tooling/quick_diagnostics.py qa/test_dx007_quick_diagnostics_cli.py tooling/generate_qdrant_tls_cert.py
```

Resultado: passou.

```powershell
py -3.12 backend/scripts/data_plane_backup_restore.py restore --dry-run --components qdrant --restore-dir outputs/qa/data-plane-backups/qdrant-tls-smoke-20260713 --output-dir outputs/qa/data-plane-backups --run-id qdrant-integrity-dry-run-20260713
```

Resultado: passou; 5 artefatos Qdrant reais com `integrity-check=status ok`.

```powershell
PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_data_plane_backup_restore.py backend/tests/unit/test_qdrant_client_config.py qa/test_dx007_quick_diagnostics_cli.py qa/test_dev_cli_doctor.py
```

Resultado final: passou; 23 testes.

```powershell
ruff check --config backend/pyproject.toml backend/scripts/data_plane_backup_restore.py backend/tests/unit/test_data_plane_backup_restore.py tooling/quick_diagnostics.py qa/test_dx007_quick_diagnostics_cli.py tooling/generate_qdrant_tls_cert.py
```

Resultado final: passou.

```powershell
py -3.12 tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json
```

Resultado: passou; `overall_ok=true`.

```powershell
git diff --check -- backend/scripts/data_plane_backup_restore.py backend/tests/unit/test_data_plane_backup_restore.py documentation/deployment-split-pc1-pc2.md
```

Resultado: passou; Git reportou apenas avisos de normalizacao LF/CRLF.

### Risco Residual

- Restore real nao foi executado neste ciclo porque a mudanca e uma validacao previa; restore fim a fim ja foi coberto no Ciclo 15 e deve ser repetido quando a politica offsite/agendada existir.

## Ciclo 19 - Validacao E2E real do frontend

### Comandos Executados

```powershell
npm run lint
```

Resultado: passou.

```powershell
npm run test
```

Resultado: passou; 32 arquivos, 169 testes.

```powershell
npx ng build --configuration development
```

Resultado: passou; bundle gerado em `frontend/dist/janus-angular`.

```powershell
node --check frontend/docker/server.mjs
```

Resultado: passou.

```powershell
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d --build janus-frontend
```

Resultado: passou; `janus-api` e `janus-frontend` foram recriados e ficaram healthy.

```powershell
Invoke-WebRequest -UseBasicParsing -Uri http://localhost:4300/api/v1/system/status
Invoke-WebRequest -UseBasicParsing -Uri http://localhost:8000/health
```

Resultado: passou; frontend proxy retornou API real `status=OPERATIONAL` e backend retornou `status=healthy`.

```powershell
py -3.12 tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json
```

Resultado: passou; `overall_ok=true`.

```powershell
node <smoke Playwright temporario>
```

Resultado final: passou. Cobertura do smoke:

- registro local com usuario real;
- login local apos limpar storage;
- persistencia de sessao apos reload;
- acesso a `/conversations`, `/tools`, `/observability`;
- redirect seguro de non-admin em `/admin/autonomia`;
- inicio de conversa e chamada `/api/v1/chat/stream/{id}` com 200;
- eventos de console `error`/`warning`: nenhum no smoke final.

Validacao adicional de chat apos o smoke:

```powershell
Invoke-RestMethod -Method Get -Uri http://localhost:4300/api/v1/chat/8/history/paginated?limit=80
```

Resultado: passou; historico retornou 2 mensagens, incluindo resposta assistant `OK smoke frontend` com `delivery_status=completed`, `provider=ollama` e `model=gpt-oss:20b`.

### Falhas Encontradas Durante o Ciclo

- Falha inicial: runtime Docker do frontend nao proxyava `/api/*`; o fallback SPA retornava HTML com HTTP 200 para chamadas de API.
- Falha intermediaria: sessao autenticada nao sobrevivia a reload por dependencia circular no request inicial de restore.

### Evidencias

- Screenshots e sumario Playwright: `C:\Users\arthu\AppData\Local\Temp\janus-frontend-qa-final-1783967523264`.
- `outputs/qa/quick_diagnostics_report.json` atualizado pelo doctor.

### Risco Residual

- O smoke deve ser promovido para suite versionada para evitar regressao manual.
- O chat real funcionou, mas a screenshot foi capturada antes da resposta final; a confirmacao final veio por API de historico. Cold start de modelo no backend gerou latencia e requer metrica propria de backend.

## Ciclo 20 - Validacao do chat real e streaming

### Comandos Executados

```powershell
ruff check --config backend/pyproject.toml backend/app/services/chat/streaming_service.py backend/app/services/chat/message_orchestration_service.py backend/app/api/v1/endpoints/chat/chat_message.py qa/test_chat_endpoint_contract.py
```

Resultado: passou.

```powershell
python -m py_compile backend/app/services/chat/streaming_service.py
```

Resultado: passou.

```powershell
npm run lint
npm run test -- --run
npx ng build --configuration development
```

Resultado: passaram; Vitest reportou 33 arquivos e 177 testes.

```powershell
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d --build janus-api
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d --build janus-frontend
```

Resultado: passou; containers `janus_api_pc1` e `janus_frontend_pc1` ficaram healthy.

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/v1/chat/health
```

Resultado: passou; `health=healthy`, `chat=healthy`, `repository_accessible=True`.

```powershell
POST /api/v1/chat/message com usuario sintetico, mensagem "Ola"
```

Resultado: passou; `elapsed_ms=5864`, `provider=ollama`, `model=gpt-oss:20b`, `citation_status=not_applicable`.

```powershell
curl.exe -sS -N --max-time 35 -X POST http://localhost:8000/api/v1/chat/stream/{conversation_id}
```

Resultado: passou apos correcao; conversa 18 retornou `event: token` e `event: done` em 10503 ms, sem `event: error`.

### Falhas Encontradas Durante o Ciclo

- `pytest -q qa/test_chat_endpoint_contract.py` falhou na coleta por `ModuleNotFoundError: aio_pika` no Python 3.13 do host.
- Primeira tentativa de smoke SSE com `curl --data-binary` falhou com `json_invalid` por encoding/quoting do PowerShell; repetida com arquivo UTF-8 sem BOM passou.

### Evidencias

- Consulta ao Postgres confirmou conversa 16 com user `Ola` e assistant persistido 144s depois.
- Logs antes da correcao mostraram `retrieve_context` em SSE com `latency_ms=14748` para conversa geral.

### Risco Residual

- Falta suite automatizada de streaming leve no backend.
- Latencia do modelo local real ainda precisa ser acompanhada por metricas de p95/p99 separadas de retrieval.

## Ciclo 20 - Atualizacao: regressao automatizada e Qdrant runtime

### Comandos Executados

```powershell
$env:PYTHONPATH='backend'; py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py
```

Resultado: passou; 29 testes.

```powershell
ruff check --config backend/pyproject.toml backend/app/config.py backend/app/core/memory/qdrant_client_config.py backend/app/api/v1/endpoints/chat/chat_message.py backend/app/services/chat/message_orchestration_service.py backend/app/services/chat/streaming_service.py backend/app/services/chat/chat_citation_service.py backend/app/services/chat/__init__.py backend/tests/unit/test_chat_streaming_service.py backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py
```

Resultado: passou.

```powershell
docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d --build janus-api
Invoke-RestMethod http://localhost:8000/health
```

Resultado: passou; `janus-api` healthy.

```powershell
curl.exe -skS -H "api-key: ***" https://localhost:6333/
docker exec janus_api_pc1 python -c "import importlib.metadata as m; print(m.version('qdrant-client'))"
```

Resultado: Qdrant server `1.18.2`; client Python `1.18.0`.

```powershell
POST /api/v1/chat/stream/{conversation_id} com mensagem "Ola"
```

Resultado: passou; conversa 21 retornou `event: token` e `event: done` em 5845 ms, sem `event: error`, com `provider=ollama`, `model=gpt-oss:20b`, `citation_status=not_applicable`.

### Falhas Encontradas Durante o Ciclo

- Teste de contrato de citacoes tentou Qdrant real no host e falhou por DNS antes de chegar no fallback de memoria fake; corrigido com monkeypatch do coletor no teste de contrato do endpoint.
- Smoke SSE com texto contendo "rebuild" foi classificado como `action_request` e acionou `retrieve_context` em 11634 ms; isso nao representa o caso do ID 16, mas confirma que mensagens fora do perfil light ainda usam contexto real.

### Risco Residual

- O smoke SSE real ainda nao esta versionado como E2E oficial.
- `QDRANT_CHECK_COMPATIBILITY=False` exige que upgrades de Qdrant continuem acompanhados de verificacao explicita de versao e smoke operacional.

## Ciclo 21 - Smoke SSE real versionado

### Comandos Executados

```powershell
$env:E2E_BASE_URL='http://localhost:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
npx playwright test e2e/chat-sse-runtime.smoke.spec.ts --project=chromium --reporter=line
```

Resultado: passou; 1 teste Playwright.

```powershell
npm run lint
```

Resultado: passou.

```powershell
npx ng build --configuration development
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py
```

Resultado: passou; 29 testes.

### Evidencias

- O novo smoke `frontend/e2e/chat-sse-runtime.smoke.spec.ts` executa registro real, `chat/start` real e `chat/stream` real pelo proxy do frontend.
- O teste valida eventos SSE parseados, nao apenas HTTP 200.

### Risco Residual

- O teste e opt-in por `JANUS_RUN_REAL_CHAT_E2E=true`; ainda falta decidir quando ele sera obrigatorio em pipeline/runtime.

## Ciclo 22 - Comando oficial para smoke SSE real

### Comandos Executados

```powershell
node -e "JSON.parse(require('fs').readFileSync('package.json','utf8')); console.log('package.json ok')"
```

Resultado: passou.

```powershell
$env:E2E_BASE_URL='http://localhost:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
npm run e2e:chat-sse
```

Resultado: passou; 1 teste Playwright.

```powershell
npm run lint
```

Resultado: passou.

```powershell
npx ng build --configuration development
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py
```

Resultado: passou; 29 testes.

### Evidencias

- `frontend/package.json` agora expoe `e2e` e `e2e:chat-sse`.
- `documentation/development-guide-frontend.md` documenta objetivo, pre-requisitos e comandos do smoke SSE real.

### Risco Residual

- O comando oficial ainda depende de o operador habilitar `JANUS_RUN_REAL_CHAT_E2E=true` e ter runtime completo ativo.

## Ciclo 23 - Smoke SSE no workflow E2E real

### Comandos Executados

```powershell
@'
from pathlib import Path
import yaml
path = Path('.github/workflows/frontend-e2e-real.yml')
with path.open('r', encoding='utf-8') as fh:
    data = yaml.safe_load(fh)
assert data['jobs']['frontend-e2e-real']['steps']
print('workflow yaml ok')
'@ | py -3.12 -
```

Resultado: passou; `workflow yaml ok`.

```powershell
$env:E2E_BASE_URL='http://localhost:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
$env:JANUS_LIGHT_CHAT_E2E_MAX_MS='60000'
npm run e2e:chat-sse
```

Resultado: passou; 1 teste Playwright.

```powershell
npm run lint
```

Resultado: passou.

```powershell
npx ng build --configuration development
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py
```

Resultado: passou; 29 testes.

### Evidencias

- `.github/workflows/frontend-e2e-real.yml` contem etapa `Run real chat SSE smoke`.
- `documentation/qa/api-test-playbook.md` lista o smoke SSE leve no checklist de release.

### Risco Residual

- Nao houve execucao remota do workflow no GitHub Actions neste ciclo.

## Ciclo 24 - Precondicao LLM real no workflow E2E

### Comandos Executados

```powershell
@'
from pathlib import Path
import yaml
path = Path('.github/workflows/frontend-e2e-real.yml')
with path.open('r', encoding='utf-8') as fh:
    data = yaml.safe_load(fh)
steps = data['jobs']['frontend-e2e-real']['steps']
validate = next(step for step in steps if step.get('name') == 'Validate required secrets')
assert 'OPENAI_API_KEY' in validate['env']
assert 'OPENAI_API_KEY' in validate['run']
print('workflow yaml ok; openai secret required')
'@ | py -3.12 -
```

Resultado: passou; `workflow yaml ok; openai secret required`.

```powershell
$env:E2E_BASE_URL='http://localhost:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
$env:JANUS_LIGHT_CHAT_E2E_MAX_MS='60000'
npm run e2e:chat-sse
```

Resultado: passou; 1 teste Playwright.

```powershell
npm run lint
```

Resultado: passou.

```powershell
npx ng build --configuration development
```

Resultado: passou.

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py
```

Resultado: passou; 29 testes.

### Evidencias

- `.github/workflows/frontend-e2e-real.yml` agora falha cedo se `OPENAI_API_KEY` estiver ausente.
- `documentation/qa/api-test-playbook.md` lista `OPENAI_API_KEY` como segredo obrigatorio para o workflow E2E real.

### Risco Residual

- A validacao local prova sintaxe e contrato, mas nao substitui execucao remota do workflow com segredos reais.

## Ciclo 25 - Evidencia JSON do smoke SSE

### Comandos Executados

```powershell
$env:E2E_BASE_URL='http://localhost:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
$env:JANUS_LIGHT_CHAT_E2E_MAX_MS='60000'
npm run e2e:chat-sse
```

Resultado: passou; 1 teste Playwright.

```powershell
Get-ChildItem -Path 'frontend/test-results' -Recurse -Filter 'chat-sse-runtime-evidence.json'
Get-Content <arquivo-gerado> -Raw
```

Resultado: passou; JSON gerado com `conversation_id=26`, `elapsed_ms=2327`, `http_status=200`, `token_event_count=1`, `done_event_count=1`, `error_event_count=0`, `provider=ollama`, `model=gpt-oss:20b`, `citation_status.status=not_applicable`.

```powershell
@'
from pathlib import Path
import yaml
path = Path('.github/workflows/frontend-e2e-real.yml')
with path.open('r', encoding='utf-8') as fh:
    data = yaml.safe_load(fh)
steps = data['jobs']['frontend-e2e-real']['steps']
assert any(step.get('name') == 'Run real chat SSE smoke' for step in steps)
print('workflow yaml ok')
'@ | py -3.12 -
```

Resultado: passou.

```powershell
npm run lint
npx ng build --configuration development
```

Resultado: passaram.

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py
```

Resultado: passou; 29 testes.

### Evidencias

- `frontend/e2e/chat-sse-runtime.smoke.spec.ts` agora anexa `chat-sse-runtime-evidence` como JSON no Playwright.
- O artefato local nao contem token de autenticacao.

### Risco Residual

- Falta artefato equivalente gerado por execucao remota do workflow.

## Ciclo 26 - Artefato dedicado para evidencia SSE

### Comandos Executados

```powershell
@'
from pathlib import Path
import yaml
path = Path('.github/workflows/frontend-e2e-real.yml')
with path.open('r', encoding='utf-8') as fh:
    data = yaml.safe_load(fh)
steps = data['jobs']['frontend-e2e-real']['steps']
upload = next(step for step in steps if step.get('name') == 'Upload chat SSE evidence')
assert upload['with']['name'] == 'frontend-chat-sse-evidence'
assert 'chat-sse-runtime-evidence.json' in upload['with']['path']
print('workflow yaml ok; sse evidence artifact configured')
'@ | py -3.12 -
```

Resultado: passou; `workflow yaml ok; sse evidence artifact configured`.

```powershell
$env:E2E_BASE_URL='http://localhost:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
$env:JANUS_LIGHT_CHAT_E2E_MAX_MS='60000'
npm run e2e:chat-sse
```

Resultado: passou; 1 teste Playwright.

```powershell
npm run lint
npx ng build --configuration development
```

Resultado: passaram.

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py
```

Resultado: passou; 29 testes.

### Evidencias

- `.github/workflows/frontend-e2e-real.yml` tem etapa `Upload chat SSE evidence`.
- O artefato dedicado usa nome `frontend-chat-sse-evidence`.

### Risco Residual

- Falta confirmar o upload dedicado em execucao remota do GitHub Actions.

## Ciclo 27 - Sincronizacao de memoria macro

### Comandos Executados

```powershell
$required = 'META.md','ROADMAP.md','NOTES.md','CHANGELOG.md','DECISIONS.md','TEST_LOG.md','TODO_TECHNICAL_DEBT.md'
foreach ($f in $required) { if (!(Test-Path $f)) { throw "missing $f" } }
```

Resultado: passou; arquivos obrigatorios presentes.

```powershell
Select-String -Path 'META.md','ROADMAP.md' -Pattern 'Ciclo 26|frontend-chat-sse-evidence|e2e:chat-sse|GitHub Actions|chat/SSE'
```

Resultado: passou; referencias encontradas em `META.md` e `ROADMAP.md`.

```powershell
git diff --check -- META.md ROADMAP.md
```

Resultado: passou; apenas avisos de normalizacao LF/CRLF.

### Evidencias

- `META.md` agora registra Ciclo 26 como estado atual e menciona o gate `npm run e2e:chat-sse`.
- `ROADMAP.md` agora contem `Fase 4.1 - Status de Chat/SSE`.

### Risco Residual

- Nao houve execucao de build/test neste ciclo porque a mudanca foi documental/memoria macro; o risco de runtime permanece coberto pelos ciclos anteriores.

## Ciclo 28 - Resumo GitHub do smoke SSE

### Comandos Executados

```powershell
@'
from pathlib import Path
import yaml
path = Path('.github/workflows/frontend-e2e-real.yml')
with path.open('r', encoding='utf-8') as fh:
    data = yaml.safe_load(fh)
steps = data['jobs']['frontend-e2e-real']['steps']
summary = next(step for step in steps if step.get('name') == 'Summarize chat SSE evidence')
assert 'GITHUB_STEP_SUMMARY' in summary['run']
assert 'chat-sse-runtime-evidence.json' in summary['run']
print('workflow yaml ok; sse summary configured')
'@ | py -3.12 -
```

Resultado: passou.

```powershell
$env:E2E_BASE_URL='http://localhost:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
$env:JANUS_LIGHT_CHAT_E2E_MAX_MS='60000'
npm run e2e:chat-sse
```

Resultado: passou; 1 teste Playwright.

```powershell
$env:GITHUB_STEP_SUMMARY=<arquivo temporario>
py -3.12 - <script de resumo do workflow>
```

Resultado: passou; summary local gerou tabela com `conversation_id=27`, `elapsed_ms=5930`, `http_status=200`, `token_event_count=1`, `done_event_count=1`, `error_event_count=0`, `provider=ollama`, `model=gpt-oss:20b`, `citation_status=not_applicable`, `agent_state=completed`.

```powershell
npm run lint
npx ng build --configuration development
```

Resultado: passaram.

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py
```

Resultado: passou; 29 testes.

### Evidencias

- `.github/workflows/frontend-e2e-real.yml` contem etapa `Summarize chat SSE evidence`.
- Summary local foi gerado a partir de `chat-sse-runtime-evidence.json`.

### Risco Residual

- Falta confirmar renderizacao do Step Summary no GitHub Actions remoto.

## Ciclo 29 - Retencao auditavel da evidencia SSE

### Comandos Executados

```powershell
py -3.12 - <parser YAML do workflow>
```

Resultado: passou; confirmou `workflow yaml ok; chat SSE evidence retention configured for 30 days`.

```powershell
$env:E2E_BASE_URL='http://localhost:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
$env:JANUS_LIGHT_CHAT_E2E_MAX_MS='60000'
npm run e2e:chat-sse
```

Resultado: falhou antes do fluxo de chat; `apiRequestContext.post` recebeu `ECONNREFUSED ::1:4300`.

```powershell
$env:E2E_BASE_URL='http://127.0.0.1:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
$env:JANUS_LIGHT_CHAT_E2E_MAX_MS='60000'
npm run e2e:chat-sse
```

Resultado: falhou antes do fluxo de chat; `apiRequestContext.post` recebeu `ECONNREFUSED 127.0.0.1:4300`.

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
Get-NetTCPConnection -LocalPort 4300,8000 -ErrorAction SilentlyContinue
Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:4300/' -TimeoutSec 3
Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 3
```

Resultado: Docker Desktop inacessivel; nenhuma conexao TCP em `4300`/`8000`; ambos endpoints recusaram conexao.

```powershell
npm run lint
npx ng build --configuration development
```

Resultado: passaram.

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py
```

Resultado: passou; 29 testes em 72.35s.

### Evidencias

- `.github/workflows/frontend-e2e-real.yml` contem `retention-days: 30` no upload `frontend-chat-sse-evidence`.
- `documentation/qa/api-test-playbook.md` documenta retencao de 30 dias para `chat-sse-runtime-evidence.json`.

### Risco Residual

- Smoke real local ficou bloqueado por ambiente desligado; falta repetir com PC2/PC1 ativos ou executar o workflow remoto.

## Ciclo 30 - Preflight operacional do smoke SSE

### Comandos Executados

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:4300/' -TimeoutSec 5
Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:8000/health' -TimeoutSec 5
```

Resultado: frontend respondeu HTTP 200; API ficou saudavel apos readiness curto.

```powershell
$env:E2E_BASE_URL='http://127.0.0.1:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
$env:JANUS_LIGHT_CHAT_E2E_MAX_MS='60000'
npm run e2e:chat-sse
```

Resultado: passou apos preflight; execucao final passou em 3.5s.

Evidencia final:

```json
{
  "conversation_id": "31",
  "elapsed_ms": 2137,
  "http_status": 200,
  "token_event_count": 1,
  "done_event_count": 1,
  "error_event_count": 0,
  "provider": "ollama",
  "model": "gpt-oss:20b",
  "citation_status": {
    "mode": "optional",
    "status": "not_applicable",
    "count": 0,
    "reason": null
  },
  "agent_state": {
    "state": "completed",
    "requires_confirmation": false
  }
}
```

```powershell
$env:E2E_BASE_URL='http://127.0.0.1:4399'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
$env:JANUS_LIGHT_CHAT_E2E_MAX_MS='60000'
npm run e2e:chat-sse
```

Resultado esperado: falhou; wrapper validou a mensagem `Janus runtime indisponivel para smoke SSE: GET /healthz falhou`.

```powershell
npm run lint
npx ng build --configuration development
```

Resultado: passaram.

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py
```

Resultado: passou; 29 testes em 40.66s.

### Risco Residual

- O smoke local validou Ollama; o workflow remoto pode usar outro provider via `OPENAI_API_KEY`, entao ainda precisa execucao em GitHub Actions.

## Ciclo 31 - Evidencia SSE com preflight registrada

### Comandos Executados

```powershell
py -3.12 - <parser YAML do workflow>
```

Resultado: passou; confirmou `workflow yaml ok; runtime preflight summary configured`.

```powershell
$env:E2E_BASE_URL='http://127.0.0.1:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
$env:JANUS_LIGHT_CHAT_E2E_MAX_MS='60000'
npm run e2e:chat-sse
```

Resultado: passou; 1 teste Playwright em 3.5s.

Evidencia final:

```json
{
  "conversation_id": "32",
  "elapsed_ms": 2216,
  "http_status": 200,
  "token_event_count": 1,
  "done_event_count": 1,
  "error_event_count": 0,
  "provider": "ollama",
  "model": "gpt-oss:20b",
  "runtime_preflight": {
    "http_status": 200,
    "status": "ok",
    "kernel_state": null
  }
}
```

```powershell
py -3.12 - <verificador local do JSON>
```

Resultado: passou; `evidence ok; conversation_id=32; elapsed_ms=2216; preflight_status=ok`.

```powershell
npm run lint
npx ng build --configuration development
```

Resultado: passaram.

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py
```

Resultado: passou; 29 testes em 38.86s.

### Risco Residual

- Falta execucao remota do workflow para confirmar Step Summary e artefato no GitHub Actions.

## Ciclo 32 - Contrato obrigatorio da preflight SSE

### Comandos Executados

```powershell
Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:4300/healthz' -TimeoutSec 5
```

Resultado: HTTP 200; payload com `status=ok` e `dependencies.kernel_state=healthy`.

```powershell
$env:E2E_BASE_URL='http://127.0.0.1:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
$env:JANUS_LIGHT_CHAT_E2E_MAX_MS='60000'
npm run e2e:chat-sse
```

Resultado: passou; 1 teste Playwright em 3.2s.

Evidencia final:

```json
{
  "conversation_id": "33",
  "elapsed_ms": 1947,
  "http_status": 200,
  "token_event_count": 1,
  "done_event_count": 1,
  "error_event_count": 0,
  "provider": "ollama",
  "model": "gpt-oss:20b",
  "runtime_preflight": {
    "http_status": 200,
    "status": "ok",
    "kernel_state": "healthy"
  },
  "agent_state": {
    "state": "completed",
    "requires_confirmation": false
  }
}
```

```powershell
py -3.12 - <verificador local do JSON>
```

Resultado: passou; `evidence contract ok; conversation_id=33; elapsed_ms=1947; kernel_state=healthy`.

```powershell
npm run lint
npx ng build --configuration development
```

Resultado: passaram.

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py
```

Resultado: passou; 29 testes em 41.16s.

### Risco Residual

- Falta executar o workflow remoto para validar o contrato de preflight no ambiente GitHub Actions.

## Ciclo 33 - Evidencia SSE com degradacao operacional zero

### Comandos Executados

```powershell
(Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:4300/healthz' -TimeoutSec 5).Content
```

Resultado: HTTP 200; payload com `status=ok`, `dependencies.kernel_state=healthy` e `dependencies.degraded_dependencies={}`.

```powershell
py -3.12 - <parser YAML do workflow>
```

Resultado: passou; `workflow yaml ok; degraded dependency summary configured`.

```powershell
$env:E2E_BASE_URL='http://127.0.0.1:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
$env:JANUS_LIGHT_CHAT_E2E_MAX_MS='60000'
npm run e2e:chat-sse
```

Resultado: passou; 1 teste Playwright em 3.3s.

Evidencia final:

```json
{
  "conversation_id": "34",
  "elapsed_ms": 2170,
  "http_status": 200,
  "error_event_count": 0,
  "provider": "ollama",
  "model": "gpt-oss:20b",
  "runtime_preflight": {
    "http_status": 200,
    "status": "ok",
    "kernel_state": "healthy",
    "degraded_dependency_count": 0,
    "degraded_dependencies": []
  },
  "agent_state": {
    "state": "completed",
    "requires_confirmation": false
  }
}
```

```powershell
py -3.12 - <verificador local do JSON>
```

Resultado: passou; `evidence contract ok; conversation_id=34; degraded_dependency_count=0`.

```powershell
npm run lint
npx ng build --configuration development
```

Resultado: passaram.

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py
```

Resultado: passou; 29 testes em 43.09s.

### Risco Residual

- Falta execucao remota para confirmar artifact/summary com o novo contrato no GitHub Actions.

## Ciclo 34 - Timeout alinhado do smoke SSE

### Comandos Executados

```powershell
$env:E2E_BASE_URL='http://127.0.0.1:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
$env:JANUS_LIGHT_CHAT_E2E_MAX_MS='60000'
npm run e2e:chat-sse
```

Resultado: passou; 1 teste Playwright em 3.3s.

Evidencia final:

```json
{
  "conversation_id": "35",
  "elapsed_ms": 2089,
  "http_status": 200,
  "error_event_count": 0,
  "provider": "ollama",
  "model": "gpt-oss:20b",
  "runtime_preflight": {
    "http_status": 200,
    "status": "ok",
    "kernel_state": "healthy",
    "degraded_dependency_count": 0,
    "degraded_dependencies": []
  },
  "agent_state": {
    "state": "completed",
    "requires_confirmation": false
  }
}
```

```powershell
py -3.12 - <verificador local do JSON>
```

Resultado: passou; `timeout-aligned smoke evidence ok; conversation_id=35; elapsed_ms=2089`.

```powershell
npm run lint
npx ng build --configuration development
```

Resultado: passaram.

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py
```

Resultado: passou; 29 testes em 38.37s.

### Risco Residual

- Falta validar no GitHub Actions remoto com `OPENAI_API_KEY` e latencia externa.

## Ciclo 35 - Step Summary SSE com escape Markdown

### Comandos Executados

```powershell
py -3.12 - <parser YAML do workflow>
```

Resultado: passou; `workflow yaml ok; table_value configured`.

```powershell
py -3.12 - <execucao do script real do Step Summary contra JSON sintetico>
```

Resultado: passou; `workflow summary escaping ok`.

```powershell
$env:E2E_BASE_URL='http://127.0.0.1:4300'
$env:JANUS_RUN_REAL_CHAT_E2E='true'
$env:JANUS_LIGHT_CHAT_E2E_MAX_MS='60000'
npm run e2e:chat-sse
```

Resultado: passou; 1 teste Playwright em 6.4s.

Evidencia final:

```json
{
  "conversation_id": "36",
  "elapsed_ms": 5065,
  "http_status": 200,
  "error_event_count": 0,
  "provider": "ollama",
  "model": "gpt-oss:20b",
  "runtime_preflight": {
    "http_status": 200,
    "status": "ok",
    "kernel_state": "healthy",
    "degraded_dependency_count": 0,
    "degraded_dependencies": []
  },
  "agent_state": {
    "state": "completed",
    "requires_confirmation": false
  }
}
```

```powershell
npm run lint
npx ng build --configuration development
```

Resultado: passaram.

```powershell
$env:PYTHONPATH='backend'
py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py
```

Resultado: passou; 29 testes em 40.17s.

### Risco Residual

- Falta validar o Step Summary renderizado em execucao remota real.

## Ciclo 36 - Chat autenticado sem 403/429

### Baseline

- `e2e/auth-session-runtime.smoke.spec.ts`: falhou; `/api/v1/chat/stream/37` retornou 403 por origem `127.0.0.1:4300`.
- Segunda execucao apos CORS: chat concluiu, mas o gate encontrou 429 em `/tools/`, `/autonomy/goals` e `/system/health/services` apos 59 chamadas.

### Validacao Final

- `ruff check ...rate_limit_middleware.py ...test_core_infrastructure_rate_limit_middleware.py`: passou.
- Pytest direcionado inicial: 34 testes passaram; suite ampliada de chat/rate limit: 37 testes passaram.
- `npm run lint`: passou.
- `npm run test`: 177 testes passaram em 33 arquivos.
- `npx ng build --configuration development`: passou; bundle gerado em 5.370s.
- `npm run e2e:chat-runtime`: passou; conversa `42`, 2898ms, stream 200, persistencia verdadeira, zero falhas de console.
- `npm run e2e:chat-sse`: passou; conversa `43`, 2295ms, zero eventos de erro e preflight saudavel.
- `python tooling/dev.py doctor --host 127.0.0.1 ...`: passou com `overall_ok=True`.
- Build e recriacao da imagem `janus-api:0.5.44`: passaram.

### Limitacoes

- O comando `npm run build -- --configuration development` foi interpretado incorretamente pelo npm local; o gate foi executado com `npx ng build --configuration development`.
- Smoke admin falhou na precondicao `Modo Admin` porque a allowlist local nao esta configurada; nenhuma conclusao foi tirada sobre aprovar/rejeitar.

## Ciclo 37 - Memoria real e stream limpo no reload

### Baseline

- `npm run e2e:chat-runtime`: falhou com GET `/api/v1/memory/generative` 500; POST havia retornado 200.
- Log backend: `retrieve_memories() got an unexpected keyword argument 'user_id'`.

### Validacao Final

- `$env:PYTHONPATH='backend'; py -3.12 -m pytest -q ...`: 38 testes direcionados passaram em 55.03s.
- `ruff check --config backend/pyproject.toml ...`: passou.
- `npm run test -- --run src/app/core/services/agent-events.service.spec.ts`: 4 testes passaram.
- `npm run lint`: passou.
- `npm run test`: 178 testes passaram em 33 arquivos.
- `npx ng build --configuration=development`: passou.
- `npm run e2e:chat-runtime`: passou; conversa `47`, chat `16881ms`, memoria `1374ms`, POST/GET 200, persistencia verdadeira, zero falhas de console.
- `JANUS_RUN_REAL_CHAT_E2E=true` e `JANUS_LIGHT_CHAT_E2E_MAX_MS=60000`; `npm run e2e:chat-sse`: passou; conversa `49`, `2115ms`, token=1, done=1, error=0.
- `py -3.12 tooling/dev.py doctor --host 127.0.0.1 ...`: passou; `overall_ok=True`.
- Builds e recriacao das imagens `janus-api:0.5.44` e `janus-frontend:0.5.44`: passaram.

### Falhas Intermediarias Explicadas

- Dois testes de timeline retornaram 401 porque a fixture era anonima; foram alinhados ao contrato autenticado e passaram.
- O primeiro rerun frontend ainda usava o bundle antigo; apos rebuild, o erro de `AgentEvents` no reload desapareceu.
- Um smoke SSE com limite default de 35s expirou; o backend concluiu em `64726ms`. Repeticao aquecida concluiu em `2115ms`.

### Limitacoes

- O outlier de 64.7s impede afirmar estabilidade de latencia; falta serie de amostras e p95/p99.
- O comando `npm run build -- --configuration development` continua incompativel com o npm local; `npx ng build --configuration=development` e o comando validado.
