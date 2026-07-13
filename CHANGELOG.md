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
