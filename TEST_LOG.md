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
