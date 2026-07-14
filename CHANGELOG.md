# CHANGELOG

## Ciclo 1 - Base documental da meta continua

### Adicionado

- Criado `META.md` com missao permanente, regras de evolucao e criterios de qualidade.
- Criado `ROADMAP.md` com fases tecnicas macro.
- Criado `NOTES.md` com observacoes do estado atual.
- Criado `DECISIONS.md` com a primeira decisao arquitetural/documental.
- Criado `TEST_LOG.md` com comandos executados e limitacoes.
- Criado `TODO_TECHNICAL_DEBT.md` com dividas iniciais priorizadas.

### Alterado

- Nenhum comportamento de backend ou frontend foi alterado neste ciclo.

### Validacao

- `Get-ChildItem` confirmou a existencia dos sete arquivos de memoria obrigatorios.
- `git diff --check` nao encontrou problemas de whitespace.
- `rg` confirmou referencias do ciclo, decisao e divida tecnica inicial nos arquivos criados.

## Ciclo 2 - Remocao da vulnerabilidade critica direta no Vitest

### Alterado

- Atualizado `frontend/package-lock.json` para resolver `vitest` de `3.2.4` para `3.2.6`.
- Atualizados pacotes internos `@vitest/*` associados para `3.2.6`.

### Nao Alterado

- `frontend/package.json` nao mudou porque o range existente `^3.1.1` ja permitia a versao corrigida.
- Dependencias Angular, DOMPurify, Firebase e transientes restantes nao foram atualizadas neste ciclo para manter escopo controlado.

### Validacao

- `npm audit --json`: antes tinha 1 critica; depois reportou 0 criticas.
- `npm run test -- --run src/app/core/services/system-status.spec.ts src/app/shared/components/ui/system-hud/system-hud.spec.ts`: 21 passed com Vitest 3.2.6.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.

## Ciclo 3 - Patches seguros da linha Angular 20

### Alterado

- Atualizado `frontend/package.json` para pins/ranges diretos:
  - `@angular/*` runtime principal para `^20.3.25`;
  - `@angular/compiler-cli` para `^20.3.25`;
  - `@angular/build` e `@angular/cli` para `^20.3.30`.
- Atualizado `frontend/package-lock.json` com as resolucoes correspondentes:
  - Angular runtime `20.3.25`;
  - Angular build/CLI/devkit `20.3.30`;
  - transientes de build como `@babel/core`, `esbuild`, `piscina` e `vite` para versoes corrigidas pela cadeia Angular.

### Validacao

- `npm audit --json`: reduziu de 30 para 19 vulnerabilidades totais; highs reduziram de 15 para 4; criticas permaneceram em 0.
- `npm run test`: 32 arquivos, 168 testes passed.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.

### Observacoes

- `npm update` reportou aviso de cleanup em `node_modules` por `esbuild.exe` bloqueado; o diff versionado ficou restrito a `frontend/package.json` e `frontend/package-lock.json`.
- `@angular/animations` e `@angular/platform-browser-dynamic` passaram a emitir avisos de deprecated no install; isso nao foi tratado neste ciclo para manter escopo de seguranca.

## Ciclo 4 - Atualizacao segura do DOMPurify

### Alterado

- Atualizado `dompurify` em `frontend/package.json` de `^3.4.2` para `^3.4.11`.
- Atualizado `frontend/package-lock.json` para resolver `node_modules/dompurify` em `3.4.11`.

### Nao Alterado

- O pipeline de Markdown e sanitizacao em `MarkdownService` nao foi refatorado.
- Nenhum `npm audit fix --force` foi executado.
- Scripts pendentes de `allow-scripts` nao foram aprovados neste ciclo.

### Validacao

- `npm audit --json`: reduziu de 19 para 18 vulnerabilidades; moderates reduziram de 10 para 9; highs permaneceram em 4; critical permaneceu em 0.
- `npm run test -- --run src/app/shared/services/markdown.service.spec.ts src/app/shared/pipes/markdown.pipe.spec.ts`: 2 arquivos, 5 testes passed.
- `npm run test`: 32 arquivos, 168 testes passed.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.
- `git diff --check`: passou.

## Ciclo 5 - Guardrail de Python suportado no tooling backend

### Alterado

- Adicionado guardrail em `tooling/dev.py` para bloquear `setup` e `qa` fora da faixa Python suportada pelo backend: `>=3.11,<3.13`.
- Adicionados testes em `qa/test_dev_cli_doctor.py` para validar a faixa suportada e a falha rapida de `cmd_qa`.
- Ajustado o teste de `cmd_doctor` para comparar caminho de forma portavel no Windows.
- Atualizados `README.md`, `backend/README.md` e `documentation/development-guide-backend.md` para declarar Python 3.11 ou 3.12 no setup/QA local do backend.

### Nao Alterado

- Nenhum contrato de API, chat, health, workers ou runtime de producao foi alterado.
- Nao houve tentativa de adicionar suporte a Python 3.13 neste ciclo.

### Validacao

- `python -m pytest -q qa/test_dev_cli_doctor.py`: 4 testes passed.
- `ruff check --config backend/pyproject.toml tooling/dev.py qa/test_dev_cli_doctor.py`: passou.
- `python tooling/dev.py qa`: falhou cedo conforme esperado em Python 3.13.13 com mensagem explicita de runtime nao suportado.
- `python tooling/dev.py setup`: falhou cedo conforme esperado em Python 3.13.13 antes de executar `pip install`.
- `git diff --check`: passou.

## Ciclo 6 - QA oficial funcionando em Python 3.12 no Windows

### Alterado

- Atualizado `tooling/dev.py` para resolver `npm` via `shutil.which("npm")` antes de chamar lint, test, build ou install do frontend.
- Atualizado `qa/test_api_visibility_endpoints.py` para que os contratos de `pending_actions` usem ator autenticado, header Bearer e pending actions com `user_id` persistido.
- Mantido o contrato de autorizacao atual de pending actions: acoes sem owner continuam bloqueadas.

### Validacao

- `py -3.12 -m pytest -q qa/test_health_endpoint_contract.py qa/test_workers_status_contract.py qa/test_chat_endpoint_contract.py`: 27 testes passed.
- `py -3.12 -m pytest -q qa/test_api_visibility_endpoints.py`: 15 testes passed.
- `py -3.12 -m pytest -q qa/test_dev_cli_doctor.py qa/test_api_visibility_endpoints.py`: 19 testes passed.
- `ruff check --config backend/pyproject.toml tooling/dev.py qa/test_dev_cli_doctor.py qa/test_api_visibility_endpoints.py`: passou.
- `py -3.12 tooling/dev.py qa`: passou completo; backend critico 64 testes, frontend lint, frontend tests 168 testes e build development.

## Ciclo 7 - Boot real PC2/PC1 pelo tooling oficial

### Alterado

- Atualizado `tooling/dev.py up` para:
  - subir PC1 com `docker compose up -d --build`, garantindo que a imagem executada seja a imagem recem-buildada pelo Compose;
  - aplicar overrides locais de conectividade PC2 via `host.docker.internal` para Neo4j, Qdrant e Ollama;
  - aplicar limites locais conservadores de memoria Neo4j no bootstrap de desenvolvimento.
- Atualizado `backend/app/config.py` para aceitar listas vindas de variaveis vazias do Compose sem erro de parsing em Pydantic Settings.
- Trocados imports de tools de `langchain.tools` para `langchain_core.tools`, evitando falha de import no conjunto atual `langchain/langgraph`.
- Ajustado `docker-compose.pc2.yml` para:
  - remover tunings Neo4j legados/incompativeis com Neo4j 5.19;
  - parametrizar heap/pagecache/memoria do Neo4j;
  - corrigir healthcheck do Qdrant sem depender de `curl`, ausente na imagem `qdrant/qdrant:v1.16.2`.
- Adicionado teste de regressao em `qa/test_dev_cli_doctor.py` para o contrato de `cmd_up`.

### Validacao

- `py -3.12 tooling/dev.py up`: passou; API e frontend ficaram healthy.
- `docker compose ... ps`: todos os containers principais ficaram healthy: API, frontend, Neo4j, Qdrant, Ollama, Postgres, Redis e RabbitMQ.
- `py -3.12 tooling/dev.py qa`: passou completo; backend critico 64 testes, frontend lint, 168 testes frontend e build development.
- `docker compose -f docker-compose.pc2.yml --env-file .env.pc2 config --quiet`: passou.
- `ruff check --config backend/pyproject.toml tooling/dev.py qa/test_dev_cli_doctor.py backend/app/config.py`: passou.

### Risco Residual

- `tooling/dev.py doctor --host localhost ...` ainda reportou `overall_ok=false` porque seus checks HTTP de dependencias usam endpoints/hosts de diagnostico split que nao refletem completamente o modo local via `host.docker.internal`.
- Ollama esta healthy, mas `ollama list` ainda nao mostra modelos; o `ollama-model-init` continua tentando baixar `gpt-oss:20b`, portanto o caminho LLM local ainda nao esta funcional para inferencia real.

## Ciclo 8 - Diagnostico local coerente com o bootstrap

### Alterado

- Atualizado `tooling/quick_diagnostics.py` para distinguir topologia local e split pelo host alvo.
- Para hosts locais (`localhost`, `127.0.0.1`, `::1`, `host.docker.internal`), os checks de dependencias agora usam:
  - Neo4j em `http://<host>:7474/browser/`;
  - Qdrant em `http://<host>:6333/healthz`;
  - Ollama em `http://<host>:11434/api/tags`.
- Mantido o comportamento split existente para hosts remotos: Neo4j Tailscale fixo, Qdrant via gateway `9443` e Ollama na porta `11434`.
- Adicionado campo `topology` no relatorio do quick diagnostics.
- Atualizados testes de `qa/test_dx007_quick_diagnostics_cli.py` para cobrir topologia local e split.

### Validacao

- `py -3.12 -m pytest -q qa/test_dx007_quick_diagnostics_cli.py qa/test_dev_cli_doctor.py`: passou; 9 testes.
- `ruff check --config backend/pyproject.toml tooling/quick_diagnostics.py qa/test_dx007_quick_diagnostics_cli.py tooling/dev.py qa/test_dev_cli_doctor.py`: passou.

### Nao Validado

- Nao foi possivel reexecutar `tooling/dev.py doctor --host localhost` contra o stack real neste turno porque Docker Desktop nao estava acessivel.
- Nao foi validada uma chamada real de chat/LLM neste turno pelo mesmo motivo.

## Ciclo 9 - Chat real via API local

### Alterado

- Atualizado `backend/app/core/infrastructure/rate_limit_middleware.py` para usar fallback local tambem em `/api/v1/chat*` quando o rate limiter central estiver indisponivel em modo fail-closed.
- Atualizado `backend/app/services/chat/message_orchestration_service.py` para consultar secret memory somente quando `secret_memory_service.should_authorize_prompt_recall(message)` autorizar recall explicito.
- Adicionados/ajustados testes em:
  - `backend/tests/unit/test_core_infrastructure_rate_limit_middleware.py`;
  - `backend/tests/unit/test_message_orchestration_service.py`.

### Evidencia Runtime

- `py -3.12 tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.local.json`: passou com `overall_ok=true`.
- `/api/v1/llm/invoke` respondeu `JANUS_OK` via `provider=ollama`, `model=gpt-oss:20b`.
- Fluxo real de chat passou: registro local, token emitido pelo Janus, `/api/v1/chat/start`, `/api/v1/chat/message` e resposta `Janus: Dois mais dois e igual a quatro.` via `provider=ollama`, `model=gpt-oss:20b`.

### Observacoes

- O anexo de build antigo com `adduser: unrecognized option: m`, pacote Alpine `libasound` e erro `cuda-bindings`/`musllinux` foi confrontado com o estado atual: `backend/docker/Dockerfile` usa `python:3.11-slim`, `useradd/groupadd` e pacote Debian `libasound2`, portanto esses sintomas especificos nao existem no Dockerfile atual.
- O rebuild focado com Compose sem overrides locais deixou a API temporariamente unhealthy porque ela voltou a usar endpoints split de `.env.pc1`; a API foi recriada com `NEO4J_URI=bolt://host.docker.internal:7687`, `QDRANT_HOST=host.docker.internal` e `OLLAMA_HOST=http://host.docker.internal:11434`.

### Validacao

- `PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_message_orchestration_service.py backend/tests/unit/test_core_infrastructure_rate_limit_middleware.py`: passou; 25 testes.
- `ruff check --config backend/pyproject.toml backend/app/core/infrastructure/rate_limit_middleware.py backend/tests/unit/test_core_infrastructure_rate_limit_middleware.py backend/app/services/chat/message_orchestration_service.py backend/tests/unit/test_message_orchestration_service.py`: passou.

### Risco Residual

- O fallback local do rate limiter e por processo; durante indisponibilidade de Redis, ele preserva disponibilidade e limite basico, mas nao oferece limite distribuido entre replicas.
- O bootstrap manual focado exige os mesmos overrides locais do `tooling/dev.py up`; sem eles, o Compose puro usa a topologia split dos arquivos `.env`.

## Ciclo 10 - Audit ledger HMAC configurado

### Alterado

- Atualizado `docker-compose.pc1.yml` para exigir e repassar `AUDIT_LEDGER_HMAC_KEY` ao `janus-api`.
- Atualizado `tooling/quick_diagnostics.py` para tratar `AUDIT_LEDGER_HMAC_KEY` como chave obrigatoria em `.env.pc1`.
- Atualizado `backend/app/core/security/secret_validator.py` para validar `AUDIT_LEDGER_HMAC_KEY` contra defaults inseguros em producao.
- Atualizado `qa/test_dx007_quick_diagnostics_cli.py` para cobrir a chave obrigatoria.

### Configuracao Local

- Gerada e persistida uma chave local em `.env.pc1` sem imprimir o valor.
- Recriado `janus-api` com `AUDIT_LEDGER_HMAC_KEY` carregado e overrides locais de PC2.

### Validacao

- `py -3.12 -m pytest -q qa/test_dx007_quick_diagnostics_cli.py backend/tests/unit/test_core_infrastructure_rate_limit_middleware.py backend/tests/unit/test_message_orchestration_service.py`: passou; 29 testes.
- `docker compose -f docker-compose.pc1.yml --env-file .env.pc1 config --quiet`: falhou antes da chave ser persistida, como esperado; passou depois.
- `py -3.12 tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.local.json`: passou com `overall_ok=true`.
- Registro local via `/api/v1/auth/local/register` retornou 200.
- Logs desde a recriacao da API nao mostraram novo `audit_ledger_append_failed`.

### Risco Residual

- O valor real da chave deve ser gerenciado como segredo operacional, nao em documentacao ou logs.

## Ciclo 11 - Qdrant atualizado para versao compativel

### Alterado

- Atualizado `docker-compose.pc2.yml` de `qdrant/qdrant:v1.16.2` para `qdrant/qdrant:v1.18.2`.
- Mantidos volumes nomeados e configuracao operacional existente do Qdrant.

### Evidencia Runtime

- `docker pull qdrant/qdrant:v1.18.2` passou.
- `docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d qdrant` recriou somente o servico Qdrant.
- API Qdrant local retornou `version=1.18.2`.
- Logs do Qdrant mostraram recuperacao das colecoes `global_docs`, `global_chat`, `global_secret`, `global_memory` e `janus_episodic_memory`.
- Apos restart do `janus-api`, logs nao mostraram novo warning de incompatibilidade entre `qdrant-client 1.18.0` e servidor Qdrant.

### Validacao

- `docker compose -f docker-compose.pc2.yml --env-file .env.pc2 config --quiet`: passou com aviso nao bloqueante de `version` obsoleto.
- `py -3.12 tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json`: passou com `overall_ok=true`.
- `/api/v1/llm/invoke` respondeu `JANUS_QDRANT_OK` via `provider=ollama`, `model=gpt-oss:20b`.

### Risco Residual

- O warning `Api key is used with an insecure connection` permanece porque o Qdrant local ainda usa HTTP sem TLS. Este ciclo corrigiu compatibilidade de versao, nao endurecimento de transporte.

## Ciclo 12 - Suporte explicito a TLS no Qdrant

### Alterado

- Adicionado `QDRANT_TLS_CA_CERT` em `backend/app/config.py`.
- Criado `backend/app/core/memory/qdrant_client_config.py` para centralizar os argumentos do `AsyncQdrantClient`.
- Atualizados `MemoryCore`, `vector_store` e `EnhancedQdrantClient` para usar o contrato central de Qdrant.
- Atualizado `docker-compose.pc1.yml` para repassar `QDRANT_HTTPS`, `QDRANT_TLS_CA_CERT` e montar `.secrets/qdrant`.
- Atualizado `docker-compose.pc2.yml` para aceitar `QDRANT_ENABLE_TLS`, `QDRANT_TLS_CERT`, `QDRANT_TLS_KEY` e montar `.secrets/qdrant`.
- Atualizados `.env.pc1.example`, `.env.pc2.example`, `.gitignore` e `documentation/deployment-split-pc1-pc2.md`.

### Validacao

- `PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_dev_cli_doctor.py`: passou; 8 testes.
- `ruff check --config backend/pyproject.toml backend/app/core/memory/qdrant_client_config.py backend/app/core/memory/memory_core.py backend/app/core/memory/enhanced_qdrant_client.py backend/app/db/vector_store.py backend/tests/unit/test_qdrant_client_config.py`: passou.
- `docker compose -f docker-compose.pc1.yml --env-file .env.pc1 config --quiet`: passou com aviso nao bloqueante de `version` obsoleto.
- `docker compose -f docker-compose.pc2.yml --env-file .env.pc2 config --quiet`: passou com aviso nao bloqueante de `version` obsoleto.
- `docker compose -f docker-compose.pc2.yml --env-file .env.pc2 up -d qdrant`: passou; Qdrant ficou healthy.
- `docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d janus-api`: passou com overrides locais; API ficou healthy.
- `python tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json`: passou com `overall_ok=true`.
- `/api/v1/llm/invoke` respondeu `JANUS_TLS_SUPPORT_OK` via `provider=ollama`, `model=gpt-oss:20b`.

### Risco Residual

- TLS ainda nao foi ativado no runtime local porque nao ha certificado provisionado neste ambiente. O warning de HTTP inseguro permanece ate `QDRANT_ENABLE_TLS=true`, `QDRANT_HTTPS=true` e `QDRANT_TLS_CA_CERT` apontarem para certificados validos.

## Ciclo 13 - TLS Qdrant ativado no runtime local

### Alterado

- Adicionado `tooling/generate_qdrant_tls_cert.py` para gerar CA local e certificado de servidor Qdrant com SANs explicitos.
- Atualizado `tooling/quick_diagnostics.py` para usar `https://localhost:6333/healthz` quando `QDRANT_HTTPS=true`.
- Atualizado `qa/test_dx007_quick_diagnostics_cli.py` para cobrir diagnostico local com Qdrant HTTPS.
- Gerado material TLS local em `.secrets/qdrant` sem versionar chave privada.
- Persistidas flags TLS locais em `.env.pc1` e `.env.pc2` sem alterar segredos:
  - PC2: `QDRANT_ENABLE_TLS=true`;
  - PC1: `QDRANT_HTTPS=true` e `QDRANT_TLS_CA_CERT=/run/secrets/janus/qdrant/ca.pem`.

### Evidencia Runtime

- Qdrant iniciou com TLS: logs mostram `TLS enabled for REST API`.
- `GET https://localhost:6333/` com `verify=.secrets/qdrant/ca.pem` retornou `version=1.18.2`.
- `/health` da API reportou `episodic_memory_qdrant` como `healthy`.
- `outputs/qa/quick_diagnostics_report.json` registrou `qdrant_health.url=https://localhost:6333/healthz` e `ok=true`.
- Logs novos do `janus-api` desde a recriacao TLS:
  - `qdrant_incompatibility_warning_count=0`;
  - `insecure_connection_warning_count=0`;
  - `tls_error_count=0`.

### Validacao

- `PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_dx007_quick_diagnostics_cli.py qa/test_dev_cli_doctor.py`: passou; 13 testes.
- `ruff check --config backend/pyproject.toml tooling/generate_qdrant_tls_cert.py tooling/quick_diagnostics.py qa/test_dx007_quick_diagnostics_cli.py backend/app/core/memory/qdrant_client_config.py backend/tests/unit/test_qdrant_client_config.py`: passou.
- `docker compose -f docker-compose.pc2.yml --env-file .env.pc2 config --quiet`: passou com aviso nao bloqueante de `version` obsoleto.
- `docker compose -f docker-compose.pc1.yml --env-file .env.pc1 config --quiet`: passou com aviso nao bloqueante de `version` obsoleto.
- `python tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json`: passou com `overall_ok=true`.
- `/api/v1/llm/invoke` respondeu `JANUS_QDRANT_TLS_OK` via `provider=ollama`, `model=gpt-oss:20b`.

### Risco Residual

- Certificados locais autoassinados resolvem o ambiente atual, mas producao/split definitivo precisa politica de rotacao e distribuicao de CA.

## Ciclo 14 - Snapshot Qdrant auditavel por TLS

### Alterado

- Atualizado `backend/scripts/data_plane_backup_restore.py` para aceitar `--qdrant-ca-cert` e validar TLS via CA em chamadas Qdrant.
- O manifest agora registra `source.qdrant.ca_cert_provided`.
- Corrigida a resolucao de colecao no restore Qdrant para preferir metadados do `manifest.json`, evitando parse fragil de nomes com hifen.
- Atualizado `backend/tests/unit/test_data_plane_backup_restore.py` para cobrir CA, precedencia de `--insecure` e resolucao de colecao por manifest.
- Atualizado `documentation/deployment-split-pc1-pc2.md` com comandos de backup/verify Qdrant por HTTPS validado.

### Evidencia Runtime

- Backup real Qdrant executado por `https://localhost:6333` com `--qdrant-ca-cert .secrets/qdrant/ca.pem`.
- Manifest gerado em `outputs/qa/data-plane-backups/qdrant-tls-smoke-20260713/manifest.json`.
- Foram baixados snapshots das colecoes:
  - `global_chat`;
  - `global_docs`;
  - `global_memory`;
  - `global_secret`;
  - `janus_episodic_memory`.
- Cada artefato registrou `size_bytes`, `sha256`, `collection` e `snapshot_name`.
- Verify real Qdrant gerado em `outputs/qa/data-plane-backups/qdrant-tls-verify-20260713/manifest.json` com `status=ok` e versao `1.18.2`.

### Validacao

- `PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_data_plane_backup_restore.py backend/tests/unit/test_qdrant_client_config.py qa/test_dx007_quick_diagnostics_cli.py qa/test_dev_cli_doctor.py`: passou; 19 testes.
- `ruff check --config backend/pyproject.toml backend/scripts/data_plane_backup_restore.py backend/tests/unit/test_data_plane_backup_restore.py tooling/quick_diagnostics.py qa/test_dx007_quick_diagnostics_cli.py tooling/generate_qdrant_tls_cert.py`: passou.
- `python tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json`: passou com `overall_ok=true`.

### Risco Residual

- Restore destrutivo nao foi executado no ambiente atual; foi protegido por testes unitarios e manifest real de backup. Restore fim a fim deve ser validado em ambiente descartavel.

## Ciclo 15 - Restore Qdrant validado em ambiente descartavel

### Alterado

- Atualizado `docker-compose.pc2.yml` para repassar `QDRANT__TLS__CA_CERT`.
- Atualizado `.env.pc2.example` para documentar `QDRANT_TLS_CA_CERT=/qdrant/tls/ca.pem`.
- Persistido `QDRANT_TLS_CA_CERT=/qdrant/tls/ca.pem` em `.env.pc2` local.
- Atualizado `documentation/deployment-split-pc1-pc2.md` para incluir a CA do lado PC2.

### Evidencia Runtime

- Subido container temporario `janus_qdrant_restore_test` com `qdrant/qdrant:v1.18.2`, TLS e armazenamento efemero na porta `16333`.
- Restore real executado contra `https://localhost:16333` usando snapshots de `qdrant-tls-smoke-20260713`.
- Manifest de restore: `outputs/qa/data-plane-backups/qdrant-tls-restore-test-20260713-ca/manifest.json`.
- Verify real do restore: `outputs/qa/data-plane-backups/qdrant-tls-restore-verify-20260713-ca/manifest.json`.
- Verify restaurado retornou `status=ok`, Qdrant `version=1.18.2` e as colecoes `global_chat`, `global_docs`, `global_memory`, `global_secret`, `janus_episodic_memory`.
- Logs do Qdrant temporario apos `QDRANT__TLS__CA_CERT` reportaram `ca_warning_count=0`.
- Container temporario foi removido ao final.

### Validacao

- `PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_data_plane_backup_restore.py backend/tests/unit/test_qdrant_client_config.py qa/test_dx007_quick_diagnostics_cli.py qa/test_dev_cli_doctor.py`: passou; 19 testes.
- `ruff check --config backend/pyproject.toml backend/scripts/data_plane_backup_restore.py backend/tests/unit/test_data_plane_backup_restore.py tooling/quick_diagnostics.py qa/test_dx007_quick_diagnostics_cli.py tooling/generate_qdrant_tls_cert.py`: passou.
- `docker compose -f docker-compose.pc2.yml --env-file .env.pc2 config --quiet`: passou com aviso nao bloqueante de `version` obsoleto.
- Qdrant ativo foi recriado para carregar `QDRANT__TLS__CA_CERT`; ficou healthy.
- API `/health` passou com `episodic_memory_qdrant` healthy.
- `python tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json`: passou com `overall_ok=true`.

### Risco Residual

- Restore foi validado em container descartavel local, nao em ambiente remoto PC2 real com janela operacional e retencao/offsite.

## Ciclo 16 - Retencao auditavel de backups data-plane

### Alterado

- Adicionado modo `prune` em `backend/scripts/data_plane_backup_restore.py`.
- `prune` nao contata Postgres/Neo4j/Qdrant para capturar versoes; registra `versions.status=skipped`.
- Retencao padrao: `--retention-days 14` e `--retain-last 5`.
- Remocao real exige `--prune-apply`; sem essa flag, o script apenas registra candidatos com `status=would-delete`.
- Adicionados testes unitarios para dry-run e apply em `tmp_path`.
- Atualizado `documentation/deployment-split-pc1-pc2.md` com comandos de retencao auditavel.

### Evidencia Runtime

- `prune-dry-run-20260713` com politica agressiva de teste (`retention_days=0`, `retain_last=3`) reportou 3 candidatos e nao removeu nenhum diretorio.
- `prune-policy-default-20260713` com politica padrao reportou `candidate_count=0`.

### Validacao

- `PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_data_plane_backup_restore.py backend/tests/unit/test_qdrant_client_config.py qa/test_dx007_quick_diagnostics_cli.py qa/test_dev_cli_doctor.py`: passou; 21 testes.
- `ruff check --config backend/pyproject.toml backend/scripts/data_plane_backup_restore.py backend/tests/unit/test_data_plane_backup_restore.py tooling/quick_diagnostics.py qa/test_dx007_quick_diagnostics_cli.py tooling/generate_qdrant_tls_cert.py`: passou.
- `python tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json`: passou com `overall_ok=true`.

### Risco Residual

- Retencao local esta implementada; offsite, criptografia externa e agendamento ainda precisam politica operacional.

## Ciclo 17 - Integridade de artefatos antes de restore

### Alterado

- `backend/scripts/data_plane_backup_restore.py` agora valida SHA-256 de artefatos antes de restore quando `manifest.json` possui entrada correspondente.
- A verificacao roda para Postgres, Neo4j e Qdrant antes de carga/upload.
- Divergencia de checksum aborta o restore com erro explicito antes de alterar o destino.
- Ausencia de manifesto ou SHA-256 e registrada como `integrity-check` com `status=skipped`, preservando compatibilidade com backups legados.
- `documentation/deployment-split-pc1-pc2.md` documenta dry-run offline de integridade antes de restore.

### Evidencia Runtime

- Dry-run operacional em `outputs/qa/data-plane-backups/qdrant-tls-smoke-20260713` validou 5 snapshots Qdrant reais com `integrity-check=status ok`.
- Manifest gerado em `outputs/qa/data-plane-backups/qdrant-integrity-dry-run-20260713/manifest.json`.

### Validacao

- `PYTHONPATH=backend py -3.12 -m pytest -q backend/tests/unit/test_data_plane_backup_restore.py backend/tests/unit/test_qdrant_client_config.py qa/test_dx007_quick_diagnostics_cli.py qa/test_dev_cli_doctor.py`: passou; 23 testes.
- `ruff check --config backend/pyproject.toml backend/scripts/data_plane_backup_restore.py backend/tests/unit/test_data_plane_backup_restore.py tooling/quick_diagnostics.py qa/test_dx007_quick_diagnostics_cli.py tooling/generate_qdrant_tls_cert.py`: passou.
- `py -3.12 backend/scripts/data_plane_backup_restore.py restore --dry-run --components qdrant --restore-dir outputs/qa/data-plane-backups/qdrant-tls-smoke-20260713 --output-dir outputs/qa/data-plane-backups --run-id qdrant-integrity-dry-run-20260713`: passou; 5 checks ok.
- `py -3.12 tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json`: passou com `overall_ok=true`.
- `git diff --check -- backend/scripts/data_plane_backup_restore.py backend/tests/unit/test_data_plane_backup_restore.py documentation/deployment-split-pc1-pc2.md`: passou; apenas avisos de normalizacao LF/CRLF do Git.

### Risco Residual

- Backups legados sem `manifest.json` ou sem `sha256` ainda podem ser restaurados, mas ficam explicitamente registrados como integridade nao verificavel.
- Ainda falta politica offsite/criptografia externa/agendamento para backup e prune.

## Ciclo 18 - Contrato de versao Qdrant no runbook operacional

### Alterado

- Atualizado `OPS_QA.md` para documentar Qdrant `v1.18.2`, alinhado ao `docker-compose.pc2.yml`.
- Adicionado `qa/test_ops_qa_runtime_contract.py` para comparar a versao Qdrant documentada no runbook com a imagem pinada no Compose PC2.

### Evidencia

- Fonte externa consultada em 2026-07-13: changelog Qdrant Private Cloud indicou `Latest validated Qdrant version: 1.18.2`.
- Fonte externa consultada em 2026-07-13: chart publico Qdrant listou `qdrant (1.18.2@v1.18.2)`.
- Fato observado local: `docker-compose.pc2.yml` usa `qdrant/qdrant:v1.18.2`.

### Validacao

- `PYTHONPATH=backend py -3.12 -m pytest -q qa/test_ops_qa_runtime_contract.py qa/test_dx007_quick_diagnostics_cli.py qa/test_dev_cli_doctor.py backend/tests/unit/test_qdrant_client_config.py`: passou; 14 testes.
- `ruff check --config backend/pyproject.toml qa/test_ops_qa_runtime_contract.py`: passou.
- `py -3.12 tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json`: passou com `overall_ok=true`.
- `git diff --check -- OPS_QA.md qa/test_ops_qa_runtime_contract.py`: passou; apenas aviso de normalizacao LF/CRLF do Git para `OPS_QA.md`.

### Risco Residual

- O teste impede drift entre runbook e Compose local, mas nao verifica automaticamente se existe uma release Qdrant mais nova na internet.

## Ciclo 19 - QA E2E real do frontend em Docker

### Alterado

- Corrigido o restore de sessao do frontend: o `/auth/local/me` inicial agora usa `SKIP_AUTH_SESSION` para evitar dependencia circular entre `AuthService` e `authSessionInterceptor`.
- Exportado `SKIP_AUTH_SESSION` no interceptor de sessao e adicionado teste de bypass sem `AuthService`.
- Adicionados asserts nos testes de `AuthService` para garantir que o request de restore carrega o contexto correto.
- Ajustado `frontend/docker/server.mjs` para suportar proxy HTTP e HTTPS conforme `JANUS_API_URL`.

### Evidencia Runtime

- Smoke E2E Playwright contra `http://localhost:4300` criou usuario real, registrou, limpou storage, logou, validou reload de sessao, acessou `/conversations`, `/tools`, `/observability`, validou redirect seguro de non-admin em `/admin/autonomia` e enviou uma mensagem de chat.
- Todas as chamadas API observadas no smoke responderam 200; os requests protegidos carregaram `Authorization`.
- Screenshots do smoke: `C:\Users\arthu\AppData\Local\Temp\janus-frontend-qa-final-1783967523264`.

### Validacao

- `npm run lint`: passou.
- `npm run test`: passou; 32 arquivos, 169 testes.
- `npx ng build --configuration development`: passou.
- `node --check frontend/docker/server.mjs`: passou.
- `docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d --build janus-frontend`: passou; `janus-api` e `janus-frontend` healthy.
- `Invoke-WebRequest http://localhost:4300/api/v1/system/status`: retornou API real com `status=OPERATIONAL`.
- `Invoke-WebRequest http://localhost:8000/health`: retornou `status=healthy`.
- `py -3.12 tooling/dev.py doctor --host localhost --backend-port 8000 --frontend-port 4300 --json-out outputs/qa/quick_diagnostics_report.json`: passou com `overall_ok=true`.

### Risco Residual

- O smoke E2E foi executado por script temporario, ainda nao versionado como suite oficial.
- O primeiro envio de chat carregou modelo cross-encoder no backend e teve latencia de cold start; isso nao quebrou o frontend, mas deve ser medido separadamente.

## Ciclo 20 - Chat real sem bloqueio indevido no streaming

### Alterado

- `/api/v1/chat/message` deixou de coletar citacoes opcionais em conversa geral; citacoes agora sao buscadas no caminho sincrono apenas quando a mensagem exige codigo/documento/anexo.
- O caminho "light chat" passa perfil explicito `general_task/low` e timeout configuravel por `CHAT_LIGHT_TIMEOUT_SECONDS`, preservando uso real do LLM sem resposta estatica.
- `/api/v1/chat/stream/{conversation_id}` recebeu paridade com o endpoint classico: conversa leve nao aciona grounding documental nem retrieval RAG/cross-encoder antes do LLM.
- Streaming tambem pula coleta de citacoes opcionais para chat geral, mantendo `citation_status=not_applicable`.
- Frontend do chat nao adiciona eventos vazios ao thought stream e exibe `Fonte nao exigida` quando o backend informa `not_applicable`, removendo o ruido de `Fontes: 0`.

### Evidencia Runtime

- Conversa 16 falhou operacionalmente por latencia: mensagem `Ola` entrou as 19:11:15 e a resposta so persistiu as 19:13:39, com `provider=ollama`, `model=gpt-oss:20b`, `delivery_status=completed` e `citation_status=not_applicable`.
- Logs do ID 16 mostraram `retrieve_context` em SSE levando 14748 ms antes do modelo para uma mensagem geral.
- Apos a correcao, smoke SSE real em conversa 18 retornou `event: token` e `event: done` em 10503 ms, sem `event: error`.
- Smoke HTTP classico real retornou `Ola` via `ollama/gpt-oss:20b` em 5864 ms com `citation_status=not_applicable`.

### Validacao

- `ruff check --config backend/pyproject.toml backend/app/services/chat/streaming_service.py backend/app/services/chat/message_orchestration_service.py backend/app/api/v1/endpoints/chat/chat_message.py qa/test_chat_endpoint_contract.py`: passou.
- `python -m py_compile backend/app/services/chat/streaming_service.py`: passou.
- `npm run lint`: passou.
- `npm run test -- --run`: passou; 33 arquivos, 177 testes.
- `npx ng build --configuration development`: passou.
- `docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d --build janus-api`: passou; API healthy.
- `docker compose -f docker-compose.pc1.yml --env-file .env.pc1 up -d --build janus-frontend`: passou; frontend healthy.

### Risco Residual

- O LLM local ainda pode levar cerca de 6-10s em mensagens leves; isso e tempo de modelo real, nao resposta estatica.
- `pytest -q qa/test_chat_endpoint_contract.py` no host segue bloqueado por dependencia ausente `aio_pika` no Python 3.13 local; a validacao de contrato ficou coberta por ruff/py_compile e smoke operacional em Docker.

### Atualizacao do Ciclo

- Adicionado teste unitario para garantir que `StreamingService` em light chat nao chama RAG, grounding documental nem citacoes opcionais.
- Corrigida fragilidade de import no pacote `app.services.chat` e em citacoes para permitir testes direcionados sem carregar workers/broker desnecessarios.
- `qa/test_chat_endpoint_contract.py` passou a cobrir que chat geral nao coleta citacoes opcionais e que pergunta de codigo mantem contrato de fonte clicavel.
- Centralizado `QDRANT_CHECK_COMPATIBILITY` no builder do client Qdrant; o checker interno foi desligado por padrao porque o runtime ja pinou/verificou server `1.18.2` e client `1.18.0`.
- Smoke SSE real equivalente ao ID 16 (`Ola`) retornou `event: token` e `event: done` em 5845 ms, sem `event: error`, usando `ollama/gpt-oss:20b` e `citation_status=not_applicable`.

## Ciclo 21 - Smoke SSE real versionado

### Alterado

- Adicionado `frontend/e2e/chat-sse-runtime.smoke.spec.ts` como smoke Playwright opt-in para o contrato real de SSE do chat.
- O teste registra usuario sintetico pela API, inicia conversa, chama `/api/v1/chat/stream/{conversation_id}` com `Ola`, parseia os eventos SSE e exige `token`, `done`, ausencia de `error`, provider/model reais e `citation_status=not_applicable`.
- O teste fica protegido por `JANUS_RUN_REAL_CHAT_E2E=true` para nao quebrar ambientes sem backend/Ollama, mas pode ser executado contra `E2E_BASE_URL=http://localhost:4300`.

### Evidencia Runtime

- `npx playwright test e2e/chat-sse-runtime.smoke.spec.ts --project=chromium --reporter=line` passou contra `http://localhost:4300` com `JANUS_RUN_REAL_CHAT_E2E=true`.
- O smoke rodou pelo frontend/proxy real e concluiu em 1 teste Playwright aprovado.

### Validacao

- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.
- `$env:PYTHONPATH='backend'; py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py`: passou; 29 testes.

### Risco Residual

- O smoke e versionado, mas ainda opt-in. Falta decidir em qual ambiente de CI/runtime ele deve ser obrigatório, porque depende de backend, Ollama e proxy funcionais.

## Ciclo 22 - Comando oficial para smoke SSE real

### Alterado

- Adicionados scripts `npm run e2e` e `npm run e2e:chat-sse` em `frontend/package.json`.
- Documentado em `documentation/development-guide-frontend.md` o smoke real do chat SSE, incluindo variaveis `E2E_BASE_URL` e `JANUS_RUN_REAL_CHAT_E2E`, pre-requisitos PC1/PC2 e comando PowerShell.

### Evidencia Runtime

- `npm run e2e:chat-sse` passou contra `http://localhost:4300` com `JANUS_RUN_REAL_CHAT_E2E=true`.

### Validacao

- `node -e "JSON.parse(require('fs').readFileSync('package.json','utf8')); console.log('package.json ok')"`: passou.
- `npm run e2e:chat-sse`: passou; 1 teste Playwright.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.
- `$env:PYTHONPATH='backend'; py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py`: passou; 29 testes.

### Risco Residual

- O smoke ficou descobrivel por npm/docs, mas continua opt-in para nao exigir runtime completo em toda execucao local. Falta decidir a esteira obrigatoria adequada.

## Ciclo 23 - Smoke SSE no workflow E2E real

### Alterado

- `.github/workflows/frontend-e2e-real.yml` agora executa `npm run e2e:chat-sse` como etapa obrigatoria do workflow manual real, com `JANUS_RUN_REAL_CHAT_E2E=true` e timeout de 60s.
- `documentation/qa/api-test-playbook.md` passou a listar o smoke SSE leve no checklist de release e nos smokes executados pelo workflow.

### Evidencia Runtime

- O workflow YAML foi parseado localmente com PyYAML e manteve a estrutura esperada.
- `npm run e2e:chat-sse` passou contra `http://localhost:4300` com `JANUS_RUN_REAL_CHAT_E2E=true`.

### Validacao

- Parser YAML local: passou; `workflow yaml ok`.
- `npm run e2e:chat-sse`: passou; 1 teste Playwright.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.
- `$env:PYTHONPATH='backend'; py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py`: passou; 29 testes.

### Risco Residual

- O gate agora existe no workflow manual real, mas ainda falta evidencia de execucao no GitHub Actions remoto neste ciclo.

## Ciclo 24 - Precondicao LLM real no workflow E2E

### Alterado

- `.github/workflows/frontend-e2e-real.yml` passou a validar `OPENAI_API_KEY` junto com `E2E_USER_EMAIL` e `E2E_USER_PASSWORD`.
- `documentation/qa/api-test-playbook.md` documenta `OPENAI_API_KEY` como segredo obrigatorio do workflow E2E real e explicita que o runner remoto nao deve assumir Ollama local.

### Evidencia

- Fato observado: o workflow ja injetava `OPENAI_API_KEY` em `.env.e2e.ci`, mas nao falhava cedo quando o segredo estava ausente.
- Inferencia: sem Ollama local no runner remoto, a falta de `OPENAI_API_KEY` poderia transformar o smoke SSE real em falha tardia de LLM.

### Validacao

- Parser YAML local: passou; `workflow yaml ok; openai secret required`.
- `npm run e2e:chat-sse`: passou; 1 teste Playwright.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.
- `$env:PYTHONPATH='backend'; py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py`: passou; 29 testes.

### Risco Residual

- O workflow remoto ainda precisa ser executado no GitHub Actions para provar o ambiente completo com segredos reais.

## Ciclo 25 - Evidencia JSON do smoke SSE

### Alterado

- `frontend/e2e/chat-sse-runtime.smoke.spec.ts` agora escreve e anexa `chat-sse-runtime-evidence.json` ao resultado Playwright.
- O artefato registra `conversation_id`, `elapsed_ms`, HTTP status, contagem de eventos `token/done/error`, `provider`, `model`, `citation_status`, `agent_state` e timestamp, sem token de autenticacao.
- `documentation/qa/api-test-playbook.md` documenta o anexo de evidencia SSE em `frontend/test-results`.

### Evidencia Runtime

- `npm run e2e:chat-sse` passou e gerou JSON local com `conversation_id=26`, `elapsed_ms=2327`, `provider=ollama`, `model=gpt-oss:20b`, `error_event_count=0` e `citation_status.status=not_applicable`.

### Validacao

- `npm run e2e:chat-sse`: passou; 1 teste Playwright.
- Leitura do `chat-sse-runtime-evidence.json`: passou; conteudo sem segredo e com metricas do SSE.
- Parser YAML local: passou; `workflow yaml ok`.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.
- `$env:PYTHONPATH='backend'; py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py`: passou; 29 testes.

### Risco Residual

- O JSON local prova o smoke no runtime atual; ainda falta artefato remoto do GitHub Actions.

## Ciclo 26 - Artefato dedicado para evidencia SSE

### Alterado

- `.github/workflows/frontend-e2e-real.yml` agora faz upload dedicado do artefato `frontend-chat-sse-evidence`.
- O upload captura `frontend/test-results/**/chat-sse-runtime-evidence.json` separadamente do pacote amplo `frontend-e2e-real-artifacts`.
- `documentation/qa/api-test-playbook.md` passou a apontar para o artefato dedicado.

### Evidencia

- Parser YAML confirmou a etapa `Upload chat SSE evidence`, com nome `frontend-chat-sse-evidence` e path contendo `chat-sse-runtime-evidence.json`.

### Validacao

- Parser YAML local: passou; `workflow yaml ok; sse evidence artifact configured`.
- `npm run e2e:chat-sse`: passou; 1 teste Playwright.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.
- `$env:PYTHONPATH='backend'; py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py`: passou; 29 testes.

### Risco Residual

- Ainda falta execucao remota do workflow para confirmar que o artefato dedicado aparece no GitHub Actions.

## Ciclo 27 - Sincronizacao de memoria macro

### Alterado

- `META.md` atualizado do estado antigo de Ciclo 6 para Ciclo 26, incluindo foco recente em chat real/SSE, gate runtime `npm run e2e:chat-sse` e risco residual de execucao remota.
- `ROADMAP.md` atualizado com marco explicito de Chat/SSE, workflow E2E real e artefato `frontend-chat-sse-evidence`.

### Validacao

- Verificacao de presenca dos arquivos obrigatorios de memoria: passou.
- Busca textual em `META.md` e `ROADMAP.md` confirmou referencias a Ciclo 26, `e2e:chat-sse`, `frontend-chat-sse-evidence` e GitHub Actions.
- `git diff --check -- META.md ROADMAP.md`: passou; apenas avisos LF/CRLF.

### Risco Residual

- A memoria macro esta sincronizada localmente, mas o risco operacional principal permanece: executar o workflow remoto e coletar artefatos reais.

## Ciclo 28 - Resumo GitHub do smoke SSE

### Alterado

- `.github/workflows/frontend-e2e-real.yml` recebeu a etapa `Summarize chat SSE evidence`.
- A etapa le `frontend/test-results/**/chat-sse-runtime-evidence.json` e publica uma tabela no `GITHUB_STEP_SUMMARY` com conversa, latencia, status HTTP, contagem de eventos, provider, model, citacao e estado do agente.

### Evidencia Local

- O script de resumo foi executado localmente contra o JSON gerado e produziu tabela com `conversation_id=27`, `elapsed_ms=5930`, `provider=ollama`, `model=gpt-oss:20b`, `error_event_count=0` e `citation_status=not_applicable`.

### Validacao

- Parser YAML local: passou; `workflow yaml ok; sse summary configured`.
- `npm run e2e:chat-sse`: passou; 1 teste Playwright.
- Script de resumo com `GITHUB_STEP_SUMMARY` temporario: passou.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.
- `$env:PYTHONPATH='backend'; py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py`: passou; 29 testes.

### Risco Residual

- Ainda falta execucao remota para confirmar o Step Summary no GitHub Actions.

## Ciclo 29 - Retencao auditavel da evidencia SSE

### Alterado

- `.github/workflows/frontend-e2e-real.yml` agora define `retention-days: 30` no upload `frontend-chat-sse-evidence`.
- `documentation/qa/api-test-playbook.md` documenta que o JSON dedicado `chat-sse-runtime-evidence.json` fica retido por 30 dias.
- `META.md`, `ROADMAP.md` e `TODO_TECHNICAL_DEBT.md` foram sincronizados com o novo estado da evidencia SSE.

### Validacao

- Parser YAML local: passou; confirmou `retention-days=30`, nome e path do artefato SSE.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.
- `$env:PYTHONPATH='backend'; py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py`: passou; 29 testes.

### Limitacao

- `npm run e2e:chat-sse` nao conseguiu validar runtime nesta rodada porque `http://localhost:4300`, `http://127.0.0.1:4300` e `http://127.0.0.1:8000/health` recusaram conexao, e Docker Desktop nao estava acessivel.

### Risco Residual

- Ainda falta executar o workflow remoto com segredos reais para provar coleta, upload, summary e retencao em GitHub Actions.

## Ciclo 30 - Preflight operacional do smoke SSE

### Alterado

- `frontend/e2e/chat-sse-runtime.smoke.spec.ts` agora executa `GET /healthz` antes de registrar usuario e iniciar conversa.
- A falha de preflight informa explicitamente que o runtime Janus esta indisponivel para o smoke SSE, separando problema de ambiente de regressao no chat.
- `documentation/qa/api-test-playbook.md`, `META.md`, `ROADMAP.md` e `TODO_TECHNICAL_DEBT.md` foram atualizados com a preflight e a nova evidencia local.

### Evidencia Local

- Com Docker ajustado e PC1/PC2 ativos, `/health` retornou `status=healthy` com dependencias `llm_router`, `message_broker`, `episodic_memory_qdrant`, `neo4j`, `postgres` e `redis` saudaveis.
- `npm run e2e:chat-sse` passou e gerou `chat-sse-runtime-evidence.json` com `conversation_id=31`, `elapsed_ms=2137`, `http_status=200`, `token_event_count=1`, `done_event_count=1`, `error_event_count=0`, `provider=ollama`, `model=gpt-oss:20b`, `citation_status=not_applicable` e `agent_state=completed`.

### Validacao

- Caminho saudavel: `npm run e2e:chat-sse` passou apos a preflight.
- Caminho de falha: smoke contra `http://127.0.0.1:4399` falhou com diagnostico esperado `Janus runtime indisponivel para smoke SSE: GET /healthz falhou`.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.
- `$env:PYTHONPATH='backend'; py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py`: passou; 29 testes.

### Risco Residual

- A evidencia local prova o fluxo real no ambiente Docker atual; ainda falta execucao remota do workflow GitHub Actions com segredos reais.

## Ciclo 31 - Evidencia SSE com preflight registrada

### Alterado

- `frontend/e2e/chat-sse-runtime.smoke.spec.ts` agora inclui `runtime_preflight` no `chat-sse-runtime-evidence.json`.
- `.github/workflows/frontend-e2e-real.yml` passa a publicar `runtime_preflight.http_status`, `runtime_preflight.status` e `runtime_preflight.kernel_state` no Step Summary.
- `documentation/qa/api-test-playbook.md`, `META.md`, `ROADMAP.md` e `TODO_TECHNICAL_DEBT.md` foram atualizados para refletir a evidencia enriquecida.

### Evidencia Local

- `npm run e2e:chat-sse` passou com `conversation_id=32`, `elapsed_ms=2216`, `http_status=200`, `error_event_count=0`, `provider=ollama`, `model=gpt-oss:20b`, `runtime_preflight.http_status=200` e `runtime_preflight.status=ok`.
- `runtime_preflight.kernel_state` ficou `null` porque `/healthz` via frontend/proxy nao expos esse campo; o teste registra a ausencia sem inventar valor.

### Validacao

- Parser YAML local: passou; confirmou campos `runtime_preflight.*` no Step Summary.
- Verificador local do JSON: passou; confirmou `runtime_preflight.http_status=200`, `runtime_preflight.status=ok` e `error_event_count=0`.
- `npm run e2e:chat-sse`: passou.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.
- `$env:PYTHONPATH='backend'; py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py`: passou; 29 testes.

### Risco Residual

- Falta executar o workflow remoto para confirmar os novos campos no Step Summary do GitHub Actions.

## Ciclo 32 - Contrato obrigatorio da preflight SSE

### Alterado

- `frontend/e2e/chat-sse-runtime.smoke.spec.ts` agora extrai `dependencies.kernel_state` de `/healthz`.
- O smoke passa a exigir `runtime_preflight.http_status=200`, `runtime_preflight.status=ok` e `runtime_preflight.kernel_state=healthy` antes de criar usuario/conversa.
- `documentation/qa/api-test-playbook.md`, `META.md`, `ROADMAP.md` e `TODO_TECHNICAL_DEBT.md` foram atualizados para refletir o contrato obrigatorio.

### Evidencia Local

- `GET http://127.0.0.1:4300/healthz` retornou HTTP 200 e payload com `status=ok` e `dependencies.kernel_state=healthy`.
- `npm run e2e:chat-sse` passou com `conversation_id=33`, `elapsed_ms=1947`, `error_event_count=0`, `agent_state=completed`, `runtime_preflight.status=ok` e `runtime_preflight.kernel_state=healthy`.

### Validacao

- `npm run e2e:chat-sse`: passou.
- Verificador local do JSON: passou; `evidence contract ok; conversation_id=33; elapsed_ms=1947; kernel_state=healthy`.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.
- `$env:PYTHONPATH='backend'; py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py`: passou; 29 testes.

### Risco Residual

- O contrato agora falha se `/healthz` degradar, mesmo antes do chat. Isso e desejado para gate E2E real, mas precisa ser considerado ao diagnosticar falhas remotas.

## Ciclo 33 - Evidencia SSE com degradacao operacional zero

### Alterado

- `frontend/e2e/chat-sse-runtime.smoke.spec.ts` agora registra `runtime_preflight.degraded_dependency_count` e `runtime_preflight.degraded_dependencies`.
- O smoke exige `degraded_dependency_count=0` e `degraded_dependencies=[]` antes de executar o fluxo de chat.
- `.github/workflows/frontend-e2e-real.yml` exibe os campos de degradacao operacional no Step Summary.
- `documentation/qa/api-test-playbook.md`, `META.md`, `ROADMAP.md` e `TODO_TECHNICAL_DEBT.md` foram atualizados com o contrato ampliado.

### Evidencia Local

- `/healthz` retornou `degraded_dependencies={}`.
- `npm run e2e:chat-sse` passou com `conversation_id=34`, `elapsed_ms=2170`, `error_event_count=0`, `agent_state=completed`, `runtime_preflight.kernel_state=healthy` e `runtime_preflight.degraded_dependency_count=0`.

### Validacao

- Parser YAML local: passou; confirmou campos de degradacao no Step Summary.
- `npm run e2e:chat-sse`: passou.
- Verificador local do JSON: passou; `evidence contract ok; conversation_id=34; degraded_dependency_count=0`.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.
- `$env:PYTHONPATH='backend'; py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py`: passou; 29 testes.

### Risco Residual

- O gate agora falha quando o ambiente esta degradado, mesmo se o stream de chat pudesse responder. Isso e uma decisao deliberada para smoke E2E real, mas deve ser interpretado como falha operacional, nao necessariamente bug de chat.

## Ciclo 34 - Timeout alinhado do smoke SSE

### Alterado

- `frontend/e2e/chat-sse-runtime.smoke.spec.ts` agora define `TEST_TIMEOUT_MS = Math.max(60_000, MAX_LIGHT_CHAT_MS + 15_000)`.
- O timeout total do Playwright passou a usar `TEST_TIMEOUT_MS`, evitando desalinhamento quando `JANUS_LIGHT_CHAT_E2E_MAX_MS` for ajustado.
- `documentation/development-guide-frontend.md` documenta a margem operacional de 15s.
- `META.md`, `ROADMAP.md` e `TODO_TECHNICAL_DEBT.md` foram atualizados com o novo estado do gate.

### Evidencia Local

- Com `JANUS_LIGHT_CHAT_E2E_MAX_MS=60000`, `npm run e2e:chat-sse` passou com `conversation_id=35`, `elapsed_ms=2089`, `error_event_count=0` e `degraded_dependency_count=0`.

### Validacao

- `npm run e2e:chat-sse`: passou.
- Verificador local do JSON: passou; `timeout-aligned smoke evidence ok; conversation_id=35; elapsed_ms=2089`.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.
- `$env:PYTHONPATH='backend'; py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py`: passou; 29 testes.

### Risco Residual

- A execucao remota ainda precisa validar o comportamento com latencia real do provider cloud.

## Ciclo 35 - Step Summary SSE com escape Markdown

### Alterado

- `.github/workflows/frontend-e2e-real.yml` recebeu a funcao `table_value` no script `Summarize chat SSE evidence`.
- Valores do Step Summary agora tratam `None` como `-`, escapam `|`, preservam barra invertida e normalizam quebras de linha para espaco.
- `META.md`, `ROADMAP.md` e `TODO_TECHNICAL_DEBT.md` foram atualizados com o estado do gate remoto.

### Evidencia Local

- O script real extraido do workflow foi executado em diretorio temporario contra JSON sintetico com `|`, barra invertida e quebra de linha; a tabela gerada manteve `x\|y`, `ollama\|local`, `line1 line2` e `dep\|one`.
- `npm run e2e:chat-sse` passou com `conversation_id=36`, `elapsed_ms=5065`, `error_event_count=0` e `degraded_dependency_count=0`.

### Validacao

- Parser YAML local: passou; confirmou `table_value`.
- Execucao local do script do Step Summary com JSON sintetico: passou; `workflow summary escaping ok`.
- `npm run e2e:chat-sse`: passou.
- `npm run lint`: passou.
- `npx ng build --configuration development`: passou.
- `$env:PYTHONPATH='backend'; py -3.12 -m pytest -q backend/tests/unit/test_qdrant_client_config.py qa/test_chat_endpoint_contract.py backend/tests/unit/test_chat_streaming_service.py`: passou; 29 testes.

### Risco Residual

- Falta confirmar a renderizacao visual no Step Summary real do GitHub Actions.

## Ciclo 36 - Chat autenticado sem 403/429

### Alterado

- CORS local agora permite `localhost:4300` e `127.0.0.1:4300` no ambiente, template e fallback do Compose.
- O rate limiter HTTP usa bucket por usuario JWT verificado; trafego anonimo permanece por IP.
- `e2e:chat-runtime` valida sessao, stream, persistencia, metadados, latencia e falhas de API/console.
- Evidencias de chat autenticado e SSE usam diretorios separados e artefatos dedicados no workflow manual.
- Evidencia SSE registra os limites `max_light_chat_ms` e `test_timeout_ms`.

### Evidencia Local

- Baseline: stream da conversa `37` retornou 403 por origem; depois, uma jornada de 59 chamadas atingiu 429 por IP.
- Final: conversa `42`, `chat_elapsed_ms=2898`, stream 200, `ollama/gpt-oss:20b`, persistida apos reload, 55 eventos de API, zero falhas de console e nenhum 429 recente.
- SSE independente: conversa `43`, `elapsed_ms=2295`, token/done presentes, zero error events e health sem degradacao.

### Risco Residual

- Smoke admin local nao foi concluido porque `AUTH_ADMIN_CPF_ALLOWLIST` nao esta configurada; o workflow remoto injeta a allowlist, mas ainda precisa ser executado.
- Operacoes mutantes de documentos, memoria e RAG permanecem fora deste ciclo.

## Ciclo 37 - Memoria real no chat e lifecycle do stream

### Alterado

- A recuperacao de memoria generativa agora aceita `user_id` e aplica filtros simultaneos de usuario e conversa no Qdrant.
- O teste de timeline foi alinhado ao contrato autenticado e verifica o ator usado na consulta.
- O smoke autenticado adiciona uma memoria semantica pela UI, busca pelo marcador exclusivo e confirma persistencia apos reload.
- O stream de eventos do agente e abortado em `pagehide`, evitando erro falso de consumo quando a pagina e recarregada.

### Evidencia Local

- Baseline: `POST /memory/generative` retornou 200, mas `GET /memory/generative` retornou 500 por argumento `user_id` incompativel.
- Final: conversa `47`, chat em `16881ms`, memoria em `1374ms`, POST/GET 200, persistencia verdadeira, 76 eventos de API e zero falhas de console.
- SSE final: conversa `49`, `2115ms`, token/done presentes, zero eventos de erro e preflight sem degradacao.
- Outlier observado: conversa `48` concluiu no backend em `64726ms` depois de o cliente expirar em 35s.

### Validacao

- Backend: 38 testes direcionados passaram; `ruff` passou.
- Frontend: lint passou; 178 testes passaram; build development passou.
- Playwright autenticado e Playwright SSE real passaram.
- `tooling/dev.py doctor` passou com `overall_ok=True`.

### Risco Residual

- Uma execucao fria excedeu 60s; ainda faltam amostras suficientes para p95/p99 e diagnostico da variancia do Ollama.
- Upload/indexacao de documentos e RAG mutante continuam pendentes no smoke autenticado.
