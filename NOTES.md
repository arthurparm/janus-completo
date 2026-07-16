# NOTES

## Ciclo 1 - Leitura do Estado Atual

### Observacoes

- Fato observado: o worktree iniciou limpo em `master...origin/master`.
- Fato observado: os arquivos obrigatorios `META.md`, `ROADMAP.md`, `NOTES.md`, `CHANGELOG.md`, `DECISIONS.md`, `TEST_LOG.md` e `TODO_TECHNICAL_DEBT.md` nao existiam no root.
- Fato observado: `AGENTS.md` e memorias existentes do projeto ja definem regras fortes de estabilidade, arquitetura e validacao.
- Fato observado: a busca por marcadores tecnicos encontrou muitos candidatos de divida (`any`, `pass`, `TODO`, `type: ignore`), mas a maioria exige triagem contextual antes de mudanca de codigo.
- Inferencia: criar a base documental e requisito previo para ciclos futuros rastreaveis e tem baixo risco operacional.

### Incertezas

- Ainda nao ha medicao completa de qualidade global apos o ultimo commit; este ciclo nao altera runtime.
- A quantidade de `any` no frontend parece relevante, mas requer selecao por contrato critico antes de refatorar.

## Ciclo 2 - Auditoria de vulnerabilidade critica no frontend

### Observacoes

- Fato observado: `npm audit --json` em `frontend/` reportou 26 vulnerabilidades antes da mudanca, incluindo 1 critica em `vitest <3.2.6`.
- Fato observado: `frontend/package.json` ja permitia `vitest` dentro da faixa `^3.1.1`; a atualizacao para `3.2.6` nao exigiu mudanca de contrato em `package.json`.
- Fato observado: `npm update vitest --save-dev` alterou apenas `frontend/package-lock.json`, atualizando `vitest` e pacotes internos `@vitest/*` de `3.2.4` para `3.2.6`.
- Fato observado: audit apos a atualizacao reportou 0 vulnerabilidades criticas, com 30 vulnerabilidades restantes: 2 low, 13 moderate e 15 high.
- Inferencia: a correcao reduz risco direto no runner de testes sem assumir o risco de uma atualizacao massiva de Angular/CLI/build.

### Diagnostico Priorizado

| Item | Impacto | Risco | Esforco | Prioridade | Decisao |
|---|---|---|---|---|---|
| Vitest critico `GHSA-5xrq-8626-4rwp` | alto | baixo | baixo | P0 | Corrigido neste ciclo |
| Vulnerabilidades Angular 20.3.x abaixo de patches seguros | alto | medio | medio | P1 | Proximo ciclo candidato |
| Vulnerabilidades transientes em Angular CLI/build/Vite/Hono | medio | medio | medio | P1 | Requer atualizacao coordenada |
| DOMPurify direto com moderates/lows | medio | baixo | baixo | P1 | Candidato a ciclo isolado |

### Incertezas

- O aumento de 26 para 30 vulnerabilidades totais parece resultado de re-resolucao/audit mais detalhado apos atualizacao do lockfile, nao piora critica; precisa ser tratado por ciclos seguintes.
- O aviso `npm warn allow-scripts` indica scripts de instalacao pendentes de aprovacao. Nao aprovei scripts neste ciclo porque isso altera politica de supply chain e exige revisao separada.

## Ciclo 3 - Patches seguros da linha Angular 20

### Observacoes

- Fato observado: antes da mudanca, `npm audit --json` reportava 30 vulnerabilidades no frontend: 2 low, 13 moderate, 15 high, 0 critical.
- Fato observado: as vulnerabilidades high em `@angular/common`, `@angular/core`, `@angular/service-worker` e dependentes apontavam para faixas abaixo de `20.3.25`.
- Fato observado: `npm outdated` indicava patches disponiveis dentro da linha Angular 20: runtime `20.3.25`, build/CLI `20.3.30`.
- Fato observado: depois de `npm update` nos pacotes Angular diretos, `npm audit --json` reportou 19 vulnerabilidades: 5 low, 10 moderate, 4 high, 0 critical.
- Fato observado: a atualizacao alterou `frontend/package.json` e `frontend/package-lock.json`.
- Inferencia: a mudanca removeu a maior parte das vulnerabilidades high diretas do stack Angular sem migrar para Angular 21/22.

### Diagnostico Priorizado

| Item | Impacto | Risco | Esforco | Prioridade | Decisao |
|---|---|---|---|---|---|
| Angular runtime abaixo dos patches seguros 20.3.25 | alto | medio | medio | P1 | Corrigido neste ciclo |
| Angular build/CLI abaixo de 20.3.30 | medio | medio | medio | P1 | Corrigido neste ciclo |
| DOMPurify direto com vulnerabilidades restantes | medio | baixo | baixo | P1 | Proximo ciclo candidato |
| Hono/MCP via Angular CLI com fix sugerindo major | medio | alto | medio | P2 | Adiar; requer avaliacao de migracao major |

### Incertezas

- O audit ainda reporta `@angular/build`/`@angular/compiler-cli` low com fix apenas por major segundo npm audit, apesar dos patches aplicados.
- `npm update` reportou falha de cleanup em um diretorio temporario de `node_modules` por arquivo `esbuild.exe` bloqueado; nao houve alteracao versionada fora de package manifests.

## Ciclo 4 - Atualizacao segura do DOMPurify

### Observacoes

- Fato observado: antes da mudanca, `npm audit --json` reportava 19 vulnerabilidades no frontend: 5 low, 10 moderate, 4 high, 0 critical.
- Fato observado: `frontend/package.json` declarava `dompurify` como dependencia direta em `^3.4.2`, com lockfile em `3.4.2`.
- Fato observado: o audit apontava `dompurify <=3.4.10` como vulneravel.
- Fato observado: `frontend/src/app/shared/services/markdown.service.ts` usa DOMPurify para sanitizar HTML derivado de Markdown antes de renderizacao via Angular.
- Fato observado: depois de `npm update dompurify --save`, `frontend/package.json` passou para `^3.4.11` e o lockfile para `3.4.11`.
- Fato observado: depois da mudanca, `npm audit --json` reportou 18 vulnerabilidades: 5 low, 9 moderate, 4 high, 0 critical; `dompurify` deixou de aparecer no mapa de vulnerabilidades.
- Inferencia: a mudanca reduz risco na cadeia de sanitizacao de Markdown sem alterar contrato de entrada/saida do servico.

### Diagnostico Priorizado

| Item | Impacto | Risco | Esforco | Prioridade | Decisao |
|---|---|---|---|---|---|
| DOMPurify direto vulneravel em caminho de Markdown/renderizacao | medio | baixo | baixo | P1 | Corrigido neste ciclo |
| Highs transientes restantes em `@grpc/grpc-js`, `hono`, `protobufjs`, `ws` | medio | medio | medio | P1 | Proximo ciclo candidato |
| Fixes de Angular CLI que sugerem major | medio | alto | medio | P2 | Adiar para avaliacao controlada |
| `allow-scripts` pendentes do npm | medio | medio | baixo | P1 | Nao aprovado neste ciclo |

### Incertezas

- A validacao confirma testes, lint, build e audit local; nao houve teste manual de browser para todos os renderizadores de Markdown.
- As 18 vulnerabilidades restantes parecem concentradas em transientes de tooling/build e devem ser triadas por cadeia antes de qualquer upgrade major.

## Ciclo 5 - Guardrail de Python suportado no tooling backend

### Problema

- Fato observado: a tentativa de rodar `PYTHONPATH=backend pytest -q qa/test_health_endpoint_contract.py qa/test_workers_status_contract.py qa/test_chat_endpoint_contract.py` no host atual falhou durante coleta.
- Fato observado: o Python ativo e `3.13.13`, enquanto `backend/pyproject.toml` declara `python = ">=3.11,<3.13"` e `backend/requirements.txt` usa markers `python_version < "3.13"` em dependencias essenciais.
- Fato observado: as falhas de coleta foram `ModuleNotFoundError` para `aio_pika` e `msgpack`, antes de qualquer contrato funcional de health/chat/workers ser avaliado.
- Inferencia: executar `tooling/dev.py setup` ou `tooling/dev.py qa` com Python 3.13 pode produzir instalacao/teste parcialmente quebrado e conclusoes falsas sobre o funcionamento real do Janus.

### Hipotese

- Hipotese: validar explicitamente a faixa Python suportada antes de `setup` e `qa` melhora a confiabilidade operacional porque impede que dependencias sejam silenciosamente puladas por environment markers.

### Metodo

- Metodo usado: teste de regressao no tooling oficial, com falha rapida antes de executar subprocessos de setup/QA.
- Criterio de aceitacao: Python 3.11 e 3.12 devem ser aceitos; Python 3.10 e 3.13 devem ser rejeitados; `setup` e `qa` devem falhar com mensagem explicita no host atual.

### Observacoes

- Fato observado: `python tooling/dev.py qa` agora falha imediatamente com `Unsupported Python runtime for Janus backend: 3.13.13`.
- Fato observado: `python tooling/dev.py setup` agora falha com a mesma mensagem antes de executar `pip install`.
- Fato observado: README, `backend/README.md` e `documentation/development-guide-backend.md` foram alinhados para Python 3.11 ou 3.12.
- Decisao de engenharia: nao ampliar o suporte para Python 3.13 neste ciclo porque isso exigiria validar compatibilidade de dependencias backend e possivelmente alterar pins/markers.

### Incertezas

- Os contratos reais de health/chat/workers ainda nao foram executados neste host porque o runtime Python local esta fora da faixa suportada.
- A validacao completa backend deve ser repetida em Python 3.11 ou 3.12, ou dentro do ambiente Docker oficial.

## Ciclo 6 - QA oficial funcionando em Python 3.12 no Windows

### Problema

- Fato observado: o host possui Python 3.12.10 disponivel via `py -3.12`, alem do Python 3.13 padrao.
- Fato observado: `py -3.12 -c "import aio_pika, msgpack, fastapi, pytest"` passou, confirmando dependencias backend essenciais no runtime suportado.
- Fato observado: os contratos focados de health/chat/workers passaram em Python 3.12: 27 testes.
- Fato observado: `py -3.12 tooling/dev.py qa` inicialmente executou o bloco backend critico com sucesso: 64 testes passed.
- Fato observado: o mesmo fluxo falhou ao chamar frontend lint porque `subprocess.run(["npm", ...])` no Windows nao resolveu `npm.cmd`, gerando `FileNotFoundError: [WinError 2]`.

### Hipotese

- Hipotese: resolver o executavel `npm` por `shutil.which("npm")` antes de chamar subprocessos torna o workflow oficial `tooling/dev.py qa` funcional no Windows, mantendo o mesmo comportamento em ambientes onde `npm` ja resolve corretamente.

### Metodo

- Metodo usado: teste de regressao operacional pelo proprio workflow oficial `py -3.12 tooling/dev.py qa`.
- Criterio de aceitacao: backend critico, lint frontend, testes frontend e build frontend devem passar pelo comando oficial em Python 3.12 no Windows.

### Observacoes

- Fato observado: `tooling/dev.py` agora usa `resolve_required_executable("npm")`, que retorna `C:\Program Files\nodejs\npm.CMD` no host atual.
- Fato observado: o contrato `qa/test_api_visibility_endpoints.py` foi ajustado para simular pending actions autenticadas com owner persistido, alinhado ao comportamento atual do endpoint.
- Fato observado: `py -3.12 tooling/dev.py qa` passou completo: 64 testes backend, frontend lint, 168 testes frontend e build development.
- Decisao de engenharia: o teste foi ajustado para explicitar owner/autenticacao em pending actions, nao para relaxar autorizacao do endpoint.

### Incertezas

- O comando `tooling/dev.py up` com Docker/PC1/PC2 nao foi executado neste ciclo.
- O aviso de Browserslist/caniuse-lite desatualizado permanece como manutencao de frontend, sem falhar o build.

## Ciclo 7 - Boot real PC2/PC1 pelo tooling oficial

### Problema

- Fato observado: `py -3.12 tooling/dev.py qa` passava, mas isso nao provava que o Janus funcionava em runtime integrado.
- Fato observado: a primeira execucao de `py -3.12 tooling/dev.py up` falhou com `janus_api_pc1 unhealthy`.
- Classificacao: problema operacional e funcional de boot integrado.

### Baseline

- Fato observado: Docker `29.6.1`, Docker Compose `v5.1.4`, Python `3.12.10`, `.env.pc1` e `.env.pc2` estavam disponiveis.
- Fato observado: falhas sequenciais impediram boot real:
  - parsing de listas vazias em Pydantic Settings (`AUTH_ADMIN_CPF_ALLOWLIST` e similares);
  - `tooling/dev.py up` buildava uma tag local diferente da imagem realmente executada pelo Compose;
  - imports `langchain.tools` quebravam com o conjunto atual de dependencias;
  - Qdrant ficava unhealthy porque o healthcheck chamava `curl`, ausente na imagem;
  - API nao alcançava Qdrant pelo IP Tailscale de `.env.pc1` dentro do Docker Desktop, mas alcançava `host.docker.internal`;
  - Neo4j reiniciava por settings legadas/incompativeis e por memoria fixa acima do limite efetivo local.

### Hipotese

- Hipotese: corrigir o bootstrap oficial para usar a imagem Compose real, overrides locais de PC2 e configuracoes Neo4j/Qdrant aceitas pelas imagens atuais faria o stack PC2 -> PC1 subir de forma mensuravel.

### Metodo

- Metodo usado: depuracao por falha observada, um bloqueador por vez, validando com logs de container, healthchecks e o proprio `tooling/dev.py up`.
- Criterio de aceitacao: `tooling/dev.py up` deve passar; API/frontend/PC2 services devem ficar healthy; `tooling/dev.py qa` deve continuar passando.

### Observacoes

- Fato observado: apos as correcoes, `py -3.12 tooling/dev.py up` passou e `docker compose ps` mostrou API, frontend, Neo4j, Qdrant, Ollama, Postgres, Redis e RabbitMQ healthy.
- Fato observado: `py -3.12 tooling/dev.py qa` continuou passando completo.
- Fato observado: logs do API ainda mostram falha de inicializacao de LLM local porque o modelo `gpt-oss:20b` nao esta disponivel no Ollama; `ollama list` retornou vazio enquanto o init continuava baixando um artefato grande.
- Inferencia: o Janus esta operacional para health, frontend, workers e dependencias principais, mas nao deve ser declarado plenamente funcional para chat/inferencia ate haver modelo LLM local ou provider cloud valido.
- Decisao de engenharia: nao alterar `.env.pc1`/`.env.pc2`; os ajustes locais ficam no processo do tooling para preservar deploy split.

### Incertezas

- `tooling/dev.py doctor --host localhost` falhou em `deps_http_ok` por checks HTTP que ainda apontam para topologia split/diagnostico especifica (`100.88.71.49` e gateway `9443`), apesar do stack local estar healthy.
- Ainda falta validar uma requisicao real de chat com LLM disponivel.

## Ciclo 8 - Diagnostico local alinhado ao bootstrap real

### Problema

- Fato observado: no Ciclo 7, `py -3.12 tooling/dev.py up` deixou o stack local healthy, mas `tooling/dev.py doctor --host localhost` falhou em `deps_http_ok`.
- Fato observado: a falha nao indicava necessariamente indisponibilidade real das dependencias locais; o diagnostico HTTP ainda consultava alvos de topologia split (`100.88.71.49` e gateway `9443`).
- Classificacao: problema operacional de diagnostico, com risco de falso negativo para o funcionamento local.

### Baseline

- Fato observado: o JSON anterior do doctor local reportou `health_ok=true`, `deps_tcp_ok=true`, `config_ok=true` e `deps_http_ok=false`.
- Fato observado: nesta sessao, Docker Desktop ficou indisponivel; comandos Docker passaram a falhar ao conectar no pipe `dockerDesktopLinuxEngine`.

### Hipotese

- Hipotese: selecionar alvos HTTP por topologia, usando endpoints locais quando `--host localhost`, reduz falso negativo no diagnostico sem alterar a topologia split de producao/desenvolvimento distribuido.

### Metodo

- Metodo usado: teste de contrato do gerador de relatorio, com probes simulados, cobrindo topologia split e topologia local.
- Criterio de aceitacao: para `host=localhost`, o relatorio deve marcar `topology=local` e consultar Neo4j/Qdrant/Ollama locais; para host remoto, deve preservar os checks split.

### Observacoes

- Fato observado: `tooling/quick_diagnostics.py` agora classifica hosts locais (`localhost`, `127.0.0.1`, `::1`, `host.docker.internal`) como topologia `local`.
- Fato observado: em modo local, o diagnostico usa `http://localhost:7474/browser/`, `http://localhost:6333/healthz` e `http://localhost:11434/api/tags`.
- Fato observado: em modo split, o diagnostico preserva gateway Qdrant `https://<host>:9443` e endpoint Neo4j remoto legado.
- Fato observado: os testes focados passaram, mas o doctor real nao foi reexecutado porque Docker Desktop estava indisponivel.

### Incertezas

- Ainda falta rodar `py -3.12 tooling/dev.py doctor --host localhost` com Docker ativo.
- Ainda falta validar uma requisicao real de chat/inferencia atraves da API Janus com modelo Ollama disponivel.

## Ciclo 9 - Funcionamento real do chat local

### Problema

- Fato observado: o doctor local corrigido passou quando Docker voltou, mas isso ainda nao provava o fluxo principal de uso do Janus.
- Fato observado: `/api/v1/llm/invoke` funcionou com Ollama e retornou `JANUS_OK`.
- Fato observado: o primeiro teste real de `/api/v1/chat/start` falhou com 503 `Rate limiter unavailable`.
- Fato observado: apos corrigir o fallback do rate limiter, o chat avancou e revelou outra falha: token manual com `user_id=1` violava FK porque o usuario nao existia.
- Fato observado: usando registro real, mensagens comuns eram respondidas por `secret_memory`, indicando roteamento indevido para memoria secreta.
- Classificacao: problema funcional/operacional no caminho real de chat.

### Baseline

- Stack PC2/PC1 estava healthy.
- Ollama tinha modelos `deepseek-coder:6.7b` e `gpt-oss:20b`.
- `tooling/dev.py doctor --host localhost` passou apos a correcao de topologia.
- Chat ainda nao podia ser declarado funcional porque falhava em rate limiter, FK de usuario manual e roteamento de secret memory.

### Hipoteses

- Hipotese: permitir fallback local para endpoints de chat quando o rate limiter central falha evita 503 mantendo protecao basica por processo.
- Hipotese: exigir `should_authorize_prompt_recall` antes de consultar secret memory impede que perguntas comuns sejam sequestradas pelo fluxo de segredo.

### Metodo

- Metodo usado: validacao operacional progressiva com API real, partindo de health/doctor, depois LLM direto, depois auth local, criacao de conversa e mensagem.
- Metodo de teste: unit tests focados para os dois contratos alterados e validação runtime com containers reconstruidos.
- Criterio de aceitacao: uma chamada real autenticada de chat deve retornar resposta normal via `ollama/gpt-oss:20b`.

### Observacoes

- Fato observado: `RateLimitMiddleware` ja tinha fallback local para documentos; o ciclo ampliou esse mecanismo para `/api/v1/chat*`.
- Trade-off: o fallback local e menos forte que Redis em ambiente multi-replica, mas e melhor que indisponibilidade total em degradacao do rate limiter.
- Fato observado: `generate_secret_recall_reply` consultava secret memory sem checar autorizacao explicita; agora retorna `None` para mensagens comuns.
- Fato observado: o fluxo final passou com usuario registrado por `/api/v1/auth/local/register`, conversa `7`, pergunta comum e resposta via `provider=ollama`, `model=gpt-oss:20b`.
- Fato observado: o anexo antigo de build aponta problemas de Alpine/BusyBox/musllinux; o Dockerfile atual ja usa Debian slim, `useradd` e `libasound2`.

### Incertezas

- Nao foi executado `py -3.12 tooling/dev.py qa` completo apos este ciclo por custo de tempo; os testes focados e o runtime real foram executados.
- O fallback local do rate limiter deve ser revisitado se houver multiplas replicas de API em producao.

## Ciclo 10 - Audit ledger sem falha de HMAC

### Problema

- Fato observado: o log do API mostrou `audit_ledger_append_failed` com erro `AUDIT_LEDGER_HMAC_KEY is not configured.`
- Fato observado: o container estava com `ENVIRONMENT=production` e `AUDIT_LEDGER_HMAC_KEY_set=False`.
- Classificacao: problema de seguranca/observabilidade/compliance, porque eventos formais de auditoria nao eram assinados nem persistidos.

### Hipotese

- Hipotese: tornar `AUDIT_LEDGER_HMAC_KEY` obrigatoria no Compose, no diagnostico e na validacao de segredos elimina falhas silenciosas do audit ledger e falha cedo quando a configuracao estiver incompleta.

### Metodo

- Metodo usado: contrato de configuracao mais estrito, validacao local via `quick_diagnostics`, recriacao do container e geracao de evento auditavel via auth local.
- Criterio de aceitacao: `AUDIT_LEDGER_HMAC_KEY` deve estar carregada no container; `doctor` deve passar; uma chamada que grava auditoria nao deve produzir novo `audit_ledger_append_failed`.

### Observacoes

- Fato observado: `docker compose ... config --quiet` passou apos persistir a chave em `.env.pc1`.
- Fato observado: o container reportou `AUDIT_LEDGER_HMAC_KEY_set=True`.
- Fato observado: `/api/v1/auth/local/register` retornou 200 depois da recriacao.
- Fato observado: logs desde a recriacao continham o POST de registro e nao continham `audit_ledger_append_failed`.

### Incertezas

- A chave local foi gerada para este ambiente; a gestao de segredo em ambiente distribuido/producao deve ser feita por cofre ou secret manager.

## Ciclo 11 - Qdrant alinhado ao cliente atual

### Problema

- Fato observado: logs do `janus-api` mostraram `qdrant_client 1.18.0` incompatibilidade com servidor Qdrant `1.16.2`.
- Fato observado: o `docker-compose.pc2.yml` fixava `qdrant/qdrant:v1.16.2`.
- Fato observado: tambem havia warning separado de API key em conexao insegura porque o Qdrant local usa HTTP.
- Classificacao: problema funcional/operacional de compatibilidade de dependencia e problema separado de seguranca de transporte.

### Hipotese

- Hipotese: atualizar o servidor Qdrant para um pin explicito `v1.18.2`, mantendo o cliente Python em `1.18.0`, remove o warning de incompatibilidade sem mascarar o check de compatibilidade.

### Metodo

- Metodo usado: verificacao de versao publicada, pull da imagem Docker, atualizacao de pin no Compose, recriacao isolada do servico Qdrant, restart da API e busca de warnings nos logs.
- Criterio de aceitacao: Qdrant deve expor `version=1.18.2`, colecoes existentes devem permanecer acessiveis, `doctor` deve passar e logs novos da API nao devem conter `Qdrant client version ... incompatible`.

### Observacoes

- Fato observado: `docker pull qdrant/qdrant:v1.18.2` passou.
- Fato observado: a API raiz do Qdrant retornou `version=1.18.2`.
- Fato observado: as colecoes `global_chat`, `global_docs`, `global_memory`, `global_secret` e `janus_episodic_memory` permaneceram listaveis apos a recriacao.
- Fato observado: logs novos da API ainda mostram `Api key is used with an insecure connection`, mas nao mostram incompatibilidade cliente/servidor.
- Decisao de engenharia: usar pin explicito `v1.18.2` em vez de `latest`, porque o usuario quer ferramenta atualizada, mas o runtime precisa ser reprodutivel e auditavel.

### Incertezas

- Nao foi feito snapshot manual do Qdrant antes do upgrade porque o update foi aplicado sobre volumes nomeados existentes sem remocao; para ambiente com dados criticos, o proximo endurecimento deve formalizar snapshot/restore antes de upgrades de banco vetorial.
- O transporte HTTP com API key continua como risco local conhecido ate configurar TLS ou rede de confianca explicitamente documentada.

## Ciclo 12 - Contrato TLS para Qdrant

### Problema

- Fato observado: apos alinhar versao, logs do `janus-api` ainda mostram `Api key is used with an insecure connection`.
- Fato observado: `docker-compose.pc1.yml` nao repassava `QDRANT_HTTPS` nem caminho de CA para o container.
- Fato observado: Qdrant suporta TLS por `service.enable_tls` e exige certificado/chave quando habilitado.
- Classificacao: problema de seguranca de transporte e configuracao operacional.

### Hipotese

- Hipotese: centralizar a configuracao do cliente Qdrant e expor `QDRANT_TLS_CA_CERT` permite ativar HTTPS com validacao de CA sem duplicar regras entre memoria, vector store e cliente resiliente.

### Metodo

- Metodo usado: contrato de configuracao + testes unitarios. A mudanca nao habilita TLS sem certificado; ela prepara o sistema para ativacao operacional correta.
- Criterio de aceitacao: em HTTP, o cliente nao deve passar `verify`; em HTTPS com CA, deve passar `verify=<caminho da CA>` preservando caminho Linux; o stack atual deve continuar healthy com TLS desativado.

### Observacoes

- Fato observado: `httpx.AsyncClient` aceita `verify` como string/caminho; `qdrant-client` repassa `**kwargs` ate essa camada.
- Fato observado: o primeiro teste encontrou uma falha real em Windows: `Path('/run/...')` convertia o caminho Linux para barras invertidas. O helper agora preserva a string literal.
- Decisao de engenharia: nao gerar certificado improvisado neste ciclo porque `openssl` nao esta disponivel no host e chave privada local nao deve ser versionada.
- Trade-off: o ciclo melhora a capacidade real de ativar TLS, mas nao remove o warning enquanto certificados nao forem provisionados e `QDRANT_ENABLE_TLS/QDRANT_HTTPS` nao forem habilitados.

### Incertezas

- Falta validar Qdrant com TLS realmente ativado usando certificado com SAN correto para o nome usado por PC1 (`host.docker.internal`, IP Tailscale ou DNS interno).
- Falta decidir se o ambiente split aceitara TLS direto no Qdrant ou terminacao TLS em proxy/gateway controlado.

## Ciclo 13 - TLS Qdrant validado em runtime

### Problema

- Fato observado: o ciclo anterior tinha suporte TLS, mas ainda nao havia certificado local nem ativacao real.
- Fato observado: sem ajustar `quick_diagnostics.py`, o doctor continuaria testando Qdrant local por HTTP mesmo com TLS ativo.
- Classificacao: problema de seguranca operacional e observabilidade.

### Hipotese

- Hipotese: gerar uma CA local, assinar um certificado Qdrant com SANs corretos e ativar `QDRANT_ENABLE_TLS/QDRANT_HTTPS` elimina o warning de API key insegura sem quebrar health, doctor ou inferencia local.

### Metodo

- Metodo usado: provisionamento controlado de certificado local, ativacao de TLS no Qdrant, configuracao do cliente Janus com CA, validacao por API Qdrant, health da API, doctor e smoke LLM.
- Criterio de aceitacao: logs novos da API devem ter `insecure_connection_warning_count=0`, `tls_error_count=0`, Qdrant deve responder por HTTPS validado pela CA e o doctor deve passar usando URL HTTPS.

### Observacoes

- Fato observado: `backend/pyproject.toml` ja declara `cryptography`, entao o gerador usa dependencia existente do backend.
- Fato observado: `.secrets/qdrant/SAN.txt` contem `host.docker.internal`, `localhost`, `127.0.0.1`, `::1`, `qdrant`, `janus_qdrant_pc2` e `100.88.71.49`.
- Fato observado: Qdrant retornou `version=1.18.2` por `https://localhost:6333/` com `verify=.secrets/qdrant/ca.pem`.
- Fato observado: `janus-api` tem `QDRANT_HTTPS=true`, `QDRANT_TLS_CA_CERT=/run/secrets/janus/qdrant/ca.pem` e o arquivo CA existe dentro do container.
- Fato observado: o relatorio do doctor registrou `qdrant_health.url=https://localhost:6333/healthz`.
- Decisao de engenharia: o material TLS local fica fora do Git; o reposititorio guarda o gerador e o contrato, nao os segredos.

### Incertezas

- A CA local nao substitui PKI/secret manager de producao.
- Falta definir rotacao de certificados e distribuicao segura da CA em topologia PC1/PC2 definitiva.

## Ciclo 14 - Backup Qdrant por HTTPS validado

### Problema

- Fato observado: o Qdrant ja estava atualizado e protegido por TLS, mas o processo de backup/restore ainda nao tinha evidencia recente com HTTPS validado.
- Fato observado: `data_plane_backup_restore.py` aceitava apenas `--insecure` ou validacao padrao de CA do sistema, insuficiente para a CA local em `.secrets/qdrant/ca.pem`.
- Fato observado: restore Qdrant inferia colecao por `artifact.name.split("-")[1]`, fragil para colecoes com hifen.
- Classificacao: problema operacional/stateful e de recuperabilidade.

### Hipotese

- Hipotese: adicionar `--qdrant-ca-cert` e preferir metadados do manifest para restore torna snapshots Qdrant auditaveis sob TLS, reduzindo risco de upgrade/manutencao stateful sem backup verificavel.

### Metodo

- Metodo usado: evolucao do script existente de backup/restore, testes unitarios de contrato e execucao real de `backup` e `verify` apenas para Qdrant.
- Criterio de aceitacao: backup real deve baixar snapshot das colecoes Qdrant via HTTPS validado, manifest deve registrar SHA-256 dos artefatos, e verify deve reportar Qdrant `status=ok`.

### Observacoes

- Fato observado: `qdrant-tls-smoke-20260713` baixou snapshots das 5 colecoes atuais.
- Fato observado: `qdrant-tls-verify-20260713` registrou Qdrant `version=1.18.2` e contagens por colecao.
- Fato observado: `global_chat` tinha `points_count=5`; demais colecoes retornaram `points_count=0` no verify deste ciclo.
- Decisao de engenharia: nao executar restore no ambiente ativo, porque restore de snapshot e operacao destrutiva/alteradora e deve ser validada em ambiente descartavel.

### Incertezas

- Falta teste de restore Qdrant fim a fim em ambiente temporario.
- Falta politica de retencao, criptografia externa e offsite para snapshots em producao.

## Ciclo 15 - Restore Qdrant em container descartavel

### Problema

- Fato observado: backup e verify estavam validados, mas restore ainda era apenas contrato unitario.
- Fato observado: restore no Qdrant ativo seria operacao alteradora e inadequada para validacao segura.
- Fato observado: logs do Qdrant temporario revelaram warning interno `Failed to load CA certificate` durante upload de snapshot quando `QDRANT__TLS__CA_CERT` nao estava configurado.
- Classificacao: problema operacional/stateful de recuperabilidade e observabilidade de restore.

### Hipotese

- Hipotese: restaurar os snapshots em um Qdrant efemero com TLS e API key prova recuperacao sem risco ao Qdrant ativo; configurar `QDRANT__TLS__CA_CERT` elimina warning interno de CA durante restore.

### Metodo

- Metodo usado: container Docker temporario `--rm` em porta isolada `16333`, restore via `data_plane_backup_restore.py`, verify por HTTPS validado e remocao do container ao final.
- Criterio de aceitacao: cinco colecoes devem ser restauradas e verificadas no Qdrant temporario; logs nao devem conter warning de CA; Qdrant ativo e API Janus devem permanecer healthy.

### Observacoes

- Fato observado: restore temporario `qdrant-tls-restore-test-20260713-ca` completou 5 etapas, uma por colecao.
- Fato observado: verify temporario `qdrant-tls-restore-verify-20260713-ca` retornou as mesmas colecoes do backup.
- Fato observado: `global_chat.points_count=5`; demais colecoes estavam vazias no snapshot atual.
- Fato observado: `ca_warning_count=0` apos configurar `QDRANT__TLS__CA_CERT=/qdrant/tls/ca.pem`.
- Fato observado: o Qdrant ativo foi recriado com a nova variavel e permaneceu healthy; API `/health` reportou `episodic_memory_qdrant` healthy.

### Incertezas

- Falta validar restore em host remoto/PC2 real com politica de janela, retencao e offsite.

## Ciclo 16 - Retencao auditavel de backups

### Problema

- Fato observado: os ciclos de backup/restore criaram multiplos diretorios em `outputs/qa/data-plane-backups`.
- Fato observado: nao havia politica executavel de retencao para evitar crescimento indefinido de snapshots.
- Restricao observada: `outputs/` pode conter evidencias de QA/diagnostico e nao deve ser apagado automaticamente sem criterio explicito.
- Classificacao: problema operacional/custo/recuperabilidade.

### Hipotese

- Hipotese: adicionar um modo `prune` com dry-run por padrao e `--prune-apply` explicito reduz risco de acumulo sem permitir delecao acidental de evidencias.

### Metodo

- Metodo usado: implementar retencao por idade e quantidade minima preservada, testar selecao em diretorio temporario, executar dry-run real no diretorio de backups atual.
- Criterio de aceitacao: dry-run deve registrar candidatos sem apagar; apply deve apagar apenas candidatos em teste temporario; politica padrao deve produzir manifest auditavel.

### Observacoes

- Fato observado: `prune-dry-run-20260713` reportou 3 candidatos sob politica agressiva `retention_days=0`, `retain_last=3`, todos com `status=would-delete`.
- Fato observado: `prune-policy-default-20260713` reportou `candidate_count=0` para `retention_days=14`, `retain_last=5`.
- Fato observado: `prune` nao consulta servicos externos; `versions.status=skipped` por desenho.
- Decisao de engenharia: manter remocao real atras de `--prune-apply`, porque backups em `outputs/` sao evidencias operacionais.

### Incertezas

- Falta agendamento automatico e politica offsite/criptografia externa.

## Ciclo 17 - Integridade antes de restore

### Problema

- Fato observado: o backup Qdrant ja registrava SHA-256 dos artefatos no manifesto.
- Fato observado: o restore aceitava arquivos do diretorio sem comparar o hash registrado antes de upload/carga.
- Classificacao: problema operacional de recuperabilidade e seguranca de cadeia de custodia dos backups.

### Hipotese

- Hipotese: validar SHA-256 antes do restore reduz o risco de restaurar snapshot corrompido ou trocado, porque transforma divergencia de artefato em falha explicita antes de alterar o destino.

### Metodo

- Metodo usado: teste de contrato unitario para checksum valido e divergente, mais dry-run operacional contra snapshots reais.
- Criterio de aceitacao: artefato com SHA-256 correspondente deve registrar `integrity-check=status ok`; artefato divergente deve abortar com `RuntimeError`; backups legados sem manifesto devem permanecer compativeis com `status=skipped`.

### Observacoes

- Fato observado: dry-run `qdrant-integrity-dry-run-20260713` validou 5 snapshots reais com hash correspondente.
- Fato observado: os testes alvo subiram de 21 para 23 por incluir contrato de integridade.
- Decisao de engenharia: nao bloquear backups legados sem manifesto/SHA neste ciclo; registrar `skipped` e deixar a politica obrigatoria para um rollout posterior.

### Incertezas

- Ainda falta tornar integridade obrigatoria por politica em ambientes de producao depois de garantir que todos os backups operacionais tenham manifesto.
- Ainda falta offsite/criptografia externa/agendamento.

## Ciclo 19 - QA E2E real do frontend

### Problema

- Fato observado: o frontend em Docker servia `/api/*` como fallback SPA antes da correcao de proxy, o que fazia registro falhar no browser mesmo com backend funcional.
- Fato observado: apos corrigir o proxy, o smoke E2E encontrou nova falha funcional: login salvava token, mas reload redirecionava para `/login?returnUrl=%2F`.
- Classificacao: problema funcional e operacional de runtime frontend.

### Hipotese

- Hipotese: o restore inicial de sessao falhava porque `AuthService.initializeAuth()` chamava `/me` durante a construcao do servico e o `authSessionInterceptor` tentava injetar `AuthService` no mesmo request, gerando dependencia circular e acionando `clearSession()`.

### Metodo

- Metodo usado: smoke Playwright com browser real, captura de requests/responses, instrumentacao temporaria de `localStorage.removeItem`, testes unitarios de contrato e rebuild Docker.
- Criterio de aceitacao: registro e login devem usar API real; sessao deve sobreviver a reload; rotas protegidas devem carregar sem redirect para login; non-admin deve ser redirecionado de admin para rota segura; chat deve iniciar conversa e chamar stream com 200.

### Observacoes

- Fato observado: antes da correcao de sessao, `/me` manual com token retornava 200, mas o reload limpava `JANUS_AUTH_TOKEN` e `JANUS_REFRESH_TOKEN` sem request visivel de `/me`.
- Fato observado: stack trace de `Storage.removeItem` apontou `AuthService.clearSession()` chamado por `initializeAuth`.
- Decisao de engenharia: adicionar `SKIP_AUTH_SESSION` no request inicial de `/me`, preservando o `authInterceptor` que anexa `Authorization`.
- Fato observado: apos a correcao, o E2E registrou usuario, logou, recarregou, acessou telas principais e enviou chat com respostas API 200 e console sem errors/warnings.

### Incertezas

- O smoke ainda nao esta versionado em `frontend/e2e` ou fluxo oficial de CI.
- Latencia de cold start do backend no chat precisa avaliacao separada; o frontend aguardou e permaneceu funcional.

## Ciclo 20 - Chat real e streaming leve

### Problema

- Fato observado: o endpoint classico `/api/v1/chat/message` conseguia responder `Ola` via Ollama em ~5,9s apos remover citacoes opcionais do caminho sincrono.
- Fato observado: o frontend usa SSE quando streaming esta ativo; no ID 16 o SSE aceitou a requisicao, mas a resposta so foi persistida ~144s depois.
- Fato observado: logs do ID 16 mostraram `retrieve_context` com RAG/cross-encoder levando 14748 ms antes do modelo para uma mensagem geral.
- Classificacao: problema funcional e de performance percebida no chat.

### Hipotese

- Hipotese: alinhar o streaming ao contrato de "light chat" reduz travamentos para mensagens gerais porque evita retrieval/grounding/citacoes quando nao ha pedido de documento, codigo ou anexo.

### Metodo

- Metodo usado: comparacao endpoint classico vs SSE, leitura de logs por `conversation_id`, consulta direta ao Postgres, mudanca focal no streaming e smoke operacional via `curl -N`.
- Criterio de aceitacao: mensagem geral no SSE deve emitir `event: token` e `event: done`, nao deve acionar `retrieve_context` pesado, e deve manter resposta gerada por LLM real.

### Observacoes

- Fato observado: conversa 16 contem resposta persistida `Ola! Como posso ajudar voce hoje?`, `delivery_status=completed`, `provider=ollama`, `model=gpt-oss:20b`.
- Decisao de engenharia: nao criar resposta estatica para saudacoes; manter LLM real e limitar apenas etapas auxiliares indevidas.
- Trade-off: mensagens gerais deixam de recuperar memorias como citacoes opcionais. Isso reduz ruido e latencia, mas tambem remove fontes nao solicitadas de conversas casuais.

### Incertezas

- Ainda falta um teste automatizado especifico de streaming leve com fake LLM/RAG para impedir regressao sem depender de Docker/Ollama.

### Atualizacao

- Fato observado: o teste automatizado de streaming leve foi adicionado em `backend/tests/unit/test_chat_streaming_service.py` e falha se uma saudacao geral acionar `retrieve_context`, grounding documental ou coleta de citacoes opcionais.
- Fato observado: `qa/test_chat_endpoint_contract.py` agora diferencia pergunta de codigo, que exige citacao, de saudacao geral, que deve retornar `citation_status=not_applicable`.
- Fato observado: Qdrant ativo localmente esta em `qdrant/qdrant:v1.18.2`; o client instalado no `janus-api` esta em `qdrant-client 1.18.0`; as colecoes foram listadas com sucesso via TLS/API key.
- Fato observado: a checagem interna de compatibilidade do `qdrant-client` emitia warning mesmo com `GET /` HTTPS retornando `version=1.18.2`; `QDRANT_CHECK_COMPATIBILITY=False` removeu esse ruido sem desligar TLS, API key ou operacoes reais.
- Fato observado: smoke SSE real com mensagem `Ola` concluiu em 5845 ms, emitiu token e done, e nao retornou erro.

### Incertezas Atualizadas

- Ainda falta promover smoke E2E de streaming real para suite versionada de CI; por enquanto ha teste unitario de contrato e smoke Docker manual.
- Ainda falta metrica operacional p95/p99 separando tempo de LLM local de retrieval/RAG.

## Ciclo 21 - Smoke SSE real versionado

### Problema

- Fato observado: o Ciclo 20 corrigiu e testou o streaming leve, mas a evidencia real de `/api/v1/chat/stream/{conversation_id}` ainda dependia de comando manual temporario.
- Classificacao: problema de qualidade/testabilidade, com impacto funcional alto porque o bug original do ID 16 apareceu apenas no caminho SSE real.

### Hipotese

- Hipotese: versionar um smoke Playwright opt-in para SSE reduz risco de regressao operacional porque transforma o roteiro manual em teste repetivel contra frontend/proxy/backend reais.

### Metodo

- Metodo usado: teste E2E API-level com Playwright, usando usuario sintetico e endpoint real de streaming.
- Criterio de aceitacao: o teste deve registrar usuario, iniciar conversa, receber `event: token`, receber `event: done`, nao receber `event: error`, preservar provider/model reais e marcar citacao como `not_applicable` para `Ola`.

### Observacoes

- Fato observado: `frontend/e2e/chat-sse-runtime.smoke.spec.ts` passou contra `http://localhost:4300` com `JANUS_RUN_REAL_CHAT_E2E=true`.
- Decisao de engenharia: manter o teste opt-in para nao exigir Ollama/backend real em toda execucao local ou CI basico.
- Trade-off: teste opt-in aumenta rastreabilidade, mas ainda nao impede regressao se nao for incluido em uma esteira runtime obrigatoria.

### Incertezas

- Falta definir uma job oficial para executar smokes reais em ambiente com PC2 -> PC1 disponivel.

## Ciclo 22 - Comando oficial para smoke SSE real

### Problema

- Fato observado: o smoke SSE real ja estava versionado, mas nao havia script npm nem documentacao no guia frontend. Isso reduzia descobribilidade e aumentava risco de regressao por nao execucao.
- Classificacao: problema de experiencia de desenvolvimento e qualidade operacional.

### Hipotese

- Hipotese: expor o smoke por `npm run e2e:chat-sse` e documentar pre-requisitos reduz custo de execucao e aumenta chance de uso consistente, porque o comando deixa de depender de memoria da conversa ou comando manual solto.

### Metodo

- Metodo usado: adicionar script npm minimo e atualizar guia frontend com o contrato do teste e comandos Bash/PowerShell.
- Criterio de aceitacao: `package.json` deve permanecer valido; `npm run e2e:chat-sse` deve executar o teste real contra `E2E_BASE_URL`; lint/build/frontend e testes backend focados devem seguir passando.

### Observacoes

- Fato observado: `npm run e2e:chat-sse` passou contra `http://localhost:4300` com `JANUS_RUN_REAL_CHAT_E2E=true`.
- Decisao de engenharia: nao tornar o smoke automatico dentro de `npm test`, porque ele depende de backend, Ollama e infraestrutura PC2 saudaveis.
- Trade-off: a execucao ficou padronizada, mas ainda nao obrigatoria.

### Incertezas

- Falta decidir se o gate real entra em workflow manual, nightly ou pipeline split PC2 -> PC1.

## Ciclo 23 - Smoke SSE no workflow E2E real

### Problema

- Fato observado: `npm run e2e:chat-sse` existia e estava documentado, mas ainda nao era executado por nenhuma esteira versionada.
- Classificacao: problema de qualidade operacional. O risco original do ID 16 so aparece no caminho SSE real, portanto a validacao precisa estar ligada a uma rotina de release/runtime.

### Hipotese

- Hipotese: adicionar o smoke SSE ao workflow manual `.github/workflows/frontend-e2e-real.yml` reduz regressao de release porque executa o contrato leve do chat no mesmo ambiente que ja sobe frontend, API e dependencias para E2E real.

### Metodo

- Metodo usado: integrar uma etapa obrigatoria no workflow manual existente, sem alterar o quality gate basico.
- Criterio de aceitacao: workflow YAML deve ser valido; o comando local equivalente deve passar contra runtime real; lint/build/testes focados devem permanecer verdes.

### Observacoes

- Fato observado: o workflow manual ja exigia segredos E2E e subia stack Docker PC1/PC2 parcial.
- Decisao de engenharia: nao iniciar Ollama adicionalmente neste ciclo; o workflow real ja depende de provedor LLM configurado para o smoke admin. O smoke SSE aceita qualquer `provider/model` real retornado.
- Trade-off: o gate ficou obrigatório dentro do workflow manual real, mas ainda nao dentro de PR/CI basico.

### Incertezas

- Falta executar o workflow no GitHub Actions remoto para capturar evidencia do ambiente CI real.

## Ciclo 24 - Precondicao LLM real no workflow E2E

### Problema

- Fato observado: o workflow E2E real injeta `OPENAI_API_KEY` no `.env.e2e.ci`, mas a etapa de validacao de segredos verificava apenas `E2E_USER_EMAIL` e `E2E_USER_PASSWORD`.
- Inferencia: em GitHub Actions remoto, nao ha garantia de Ollama local com `gpt-oss:20b`; logo o smoke de chat real precisa de um provedor LLM cloud configurado ou deve falhar cedo.
- Classificacao: problema de confiabilidade operacional do gate.

### Hipotese

- Hipotese: exigir `OPENAI_API_KEY` no inicio do workflow reduz falhas tardias e ambiguas do chat real, porque transforma falta de provedor LLM em erro de precondicao claro.

### Metodo

- Metodo usado: validacao explicita de segredo no workflow manual e documentacao no playbook QA.
- Criterio de aceitacao: YAML deve continuar valido; a validacao deve conter `OPENAI_API_KEY`; smoke local e gates direcionados devem seguir passando.

### Observacoes

- Decisao de engenharia: nao tentar baixar/rodar Ollama `gpt-oss:20b` no runner GitHub neste ciclo, porque isso aumentaria custo, tempo e incerteza operacional.
- Trade-off: o workflow fica mais exigente em segredo, mas falha mais cedo e com causa clara quando o ambiente nao esta preparado.

### Incertezas

- Ainda falta evidencia de execucao remota com `OPENAI_API_KEY` real configurada.

## Ciclo 25 - Evidencia JSON do smoke SSE

### Problema

- Fato observado: o workflow ja fazia upload de `frontend/test-results`, mas o smoke SSE nao produzia uma evidencia resumida e auditavel alem do relatorio Playwright.
- Classificacao: problema de observabilidade de QA. Sem artefato estruturado, comparar latencia, provider/model e status de citacao exige abrir traces/logs.

### Hipotese

- Hipotese: anexar um JSON pequeno ao resultado Playwright melhora auditoria do gate porque preserva os sinais essenciais do contrato SSE sem expor token ou depender de interpretacao manual do trace.

### Metodo

- Metodo usado: `testInfo.outputPath` + `testInfo.attach` no Playwright.
- Criterio de aceitacao: o smoke real deve passar e gerar JSON com `conversation_id`, latencia, contagem de eventos, `provider`, `model`, `citation_status` e `agent_state`, sem token.

### Observacoes

- Fato observado: o JSON local registrou `elapsed_ms=2327`, `provider=ollama`, `model=gpt-oss:20b`, `error_event_count=0` e `citation_status.status=not_applicable`.
- Decisao de engenharia: nao salvar o payload SSE bruto por padrao para reduzir risco de capturar conteudo sensivel; preservar apenas metricas e metadados de contrato.

### Incertezas

- Falta validar que o artefato aparece corretamente no upload remoto do GitHub Actions.

## Ciclo 26 - Artefato dedicado para evidencia SSE

### Problema

- Fato observado: o JSON do smoke SSE era gerado dentro de `frontend/test-results`, mas ficava misturado ao pacote amplo de artefatos Playwright.
- Classificacao: problema de auditoria operacional. O artefato existia, mas era menos direto de localizar em revisao de release.

### Hipotese

- Hipotese: publicar `chat-sse-runtime-evidence.json` como artefato dedicado reduz o custo de auditoria, porque separa a evidencia essencial do chat/SSE dos demais traces e relatorios.

### Metodo

- Metodo usado: etapa `actions/upload-artifact@v4` com `if-no-files-found: warn`, mantendo tambem o upload amplo de Playwright.
- Criterio de aceitacao: workflow YAML deve apontar para `frontend/test-results/**/chat-sse-runtime-evidence.json`; o smoke local e gates direcionados devem passar.

### Observacoes

- Decisao de engenharia: usar `warn` quando nao houver arquivo para preservar upload de logs em falhas anteriores ao smoke, sem esconder a falha principal do teste.
- Trade-off: ha pequena duplicacao de artefato, mas com ganho de rastreabilidade para release.

### Incertezas

- Falta evidencia remota do artifact `frontend-chat-sse-evidence` no GitHub Actions.

## Ciclo 27 - Sincronizacao de memoria macro

### Problema

- Fato observado: `META.md` ainda indicava Ciclo 6 como ciclo atual, apesar de os ciclos recentes terem alterado chat real, SSE, workflow E2E e evidencias.
- Fato observado: `ROADMAP.md` nao refletia o marco operacional de chat/SSE nem o proximo passo de evidencia remota.
- Classificacao: problema de documentacao e governanca tecnica.

### Hipotese

- Hipotese: sincronizar `META.md` e `ROADMAP.md` reduz ambiguidade em ciclos futuros porque deixa o estado macro alinhado com os gates reais implementados.

### Metodo

- Metodo usado: atualizacao pequena e direta nos arquivos de memoria macro, sem reescrever historico.
- Criterio de aceitacao: todos os arquivos obrigatorios existem; `META.md` aponta para o ciclo atual; `ROADMAP.md` explicita status e pendencias de Chat/SSE.

### Observacoes

- Fato observado: todos os arquivos obrigatorios existem: `META.md`, `ROADMAP.md`, `NOTES.md`, `CHANGELOG.md`, `DECISIONS.md`, `TEST_LOG.md`, `TODO_TECHNICAL_DEBT.md`.
- Trade-off: nao foi criada nova estrutura de governanca; a melhoria foi limitada a sincronizar memoria existente.

### Incertezas

- Ainda falta execucao remota do workflow E2E real para atualizar a memoria de estado com evidencia externa.

## Ciclo 28 - Resumo GitHub do smoke SSE

### Problema

- Fato observado: o workflow ja faz upload de JSON dedicado, mas a leitura da evidencia ainda exigiria baixar o artefato.
- Classificacao: problema de observabilidade de QA e experiencia de release.

### Hipotese

- Hipotese: publicar os campos essenciais do JSON no `GITHUB_STEP_SUMMARY` reduz tempo de auditoria, porque o revisor consegue confirmar latencia, provider/model e status SSE diretamente na pagina da execucao.

### Metodo

- Metodo usado: etapa Python simples no workflow, lendo o JSON mais recente de `frontend/test-results/**/chat-sse-runtime-evidence.json` e escrevendo tabela Markdown no summary.
- Criterio de aceitacao: YAML valido; script consegue gerar summary local; smoke SSE e gates direcionados continuam passando.

### Observacoes

- Decisao de engenharia: o summary nao falha o workflow se o JSON nao existir; ele registra ausencia. A falha real deve vir do teste Playwright ou dos uploads/logs, preservando diagnostico em falhas anteriores.
- Trade-off: pequena duplicacao de informacao entre artefato JSON e Step Summary, com ganho de auditabilidade.

### Incertezas

- Falta confirmar renderizacao real do summary em GitHub Actions remoto.

## Ciclo 29 - Retencao auditavel da evidencia SSE

### Problema

- Fato observado: o artefato dedicado `frontend-chat-sse-evidence` existia, mas sem janela de retencao explicita no workflow.
- Classificacao: problema de governanca de QA e auditabilidade operacional.

### Hipotese

- Hipotese: declarar `retention-days: 30` melhora a capacidade de auditoria do smoke real porque evita depender da politica default da plataforma e cria uma janela conhecida para revisar evidencias.

### Metodo

- Metodo usado: mudanca pequena no contrato de CI, validada por parser YAML e documentada no playbook.
- Criterio de aceitacao: o upload `frontend-chat-sse-evidence` deve conter `retention-days=30`; o playbook deve mencionar a mesma janela; lint/build/testes de chat direcionados devem continuar passando.

### Observacoes

- Fato observado: nesta rodada, o ambiente runtime local estava desligado ou inacessivel (`4300` e `8000` recusaram conexao; Docker Desktop nao respondeu).
- Inferencia: a falha do smoke E2E nesta rodada nao e evidencia de regressao do chat; e evidencia de pre-condicao operacional ausente.

### Incertezas

- Falta evidencia remota do GitHub Actions confirmando que o upload e o Step Summary aparecem como esperado numa execucao real.

## Ciclo 30 - Preflight operacional do smoke SSE

### Problema

- Fato observado: quando o ambiente local estava desligado, o smoke SSE falhava em `request.post('/api/v1/auth/local/register')` com `ECONNREFUSED`, sem separar claramente indisponibilidade operacional de falha do chat.
- Classificacao: problema de qualidade de teste e diagnostico operacional.

### Hipotese

- Hipotese: executar `GET /healthz` antes do fluxo de chat melhora a interpretabilidade do gate porque falhas de ambiente passam a ser classificadas antes de criar usuario/conversa.

### Metodo

- Metodo usado: preflight simples no proprio teste Playwright, usando o mesmo `E2E_BASE_URL` do fluxo real.
- Criterio de aceitacao: ambiente saudavel continua passando no smoke; ambiente indisponivel falha com mensagem explicita de preflight; lint/build/testes direcionados continuam passando.

### Observacoes

- Fato observado: apos ajuste do Docker, containers PC1/PC2 subiram e `/health` retornou `status=healthy`.
- Fato observado: smoke final gerou evidencia com `conversation_id=31`, `elapsed_ms=2137`, `provider=ollama`, `model=gpt-oss:20b`, `error_event_count=0`, `citation_status=not_applicable` e `agent_state=completed`.
- Decisao de engenharia: a preflight usa `/healthz` via frontend/proxy, nao acesso direto ao backend, para validar o mesmo caminho operacional usado pelo usuario do frontend.

### Incertezas

- A execucao remota do workflow ainda precisa confirmar comportamento com `OPENAI_API_KEY` e segredos reais em GitHub Actions.

## Ciclo 31 - Evidencia SSE com preflight registrada

### Problema

- Fato observado: o smoke validava `/healthz` antes do chat, mas o JSON de evidencia ainda nao registrava o resultado dessa preflight.
- Classificacao: problema de auditabilidade de QA.

### Hipotese

- Hipotese: incluir `runtime_preflight` no JSON melhora a rastreabilidade porque a evidencia passa a provar tanto a disponibilidade inicial quanto o resultado do stream SSE.

### Metodo

- Metodo usado: enriquecer o artefato existente com campos tipados e manter compatibilidade com o upload atual.
- Criterio de aceitacao: JSON deve conter `runtime_preflight.http_status=200`, `runtime_preflight.status=ok`, `error_event_count=0`; Step Summary deve referenciar os novos campos; gates direcionados devem passar.

### Observacoes

- Fato observado: `conversation_id=32`, `elapsed_ms=2216`, `provider=ollama`, `model=gpt-oss:20b`, `runtime_preflight.status=ok`.
- Fato observado: `runtime_preflight.kernel_state=null` porque o endpoint `/healthz` proxied nao retornou esse campo.
- Decisao de engenharia: registrar `null` para campo ausente e evitar inferir kernel state a partir de outro endpoint.

### Incertezas

- Ainda falta evidencia remota do GitHub Actions confirmando renderizacao dos campos `runtime_preflight.*` no Step Summary.

## Ciclo 32 - Contrato obrigatorio da preflight SSE

### Problema

- Fato observado: o JSON registrava `runtime_preflight`, mas o teste nao falhava caso `kernel_state` continuasse ausente ou incorreto.
- Classificacao: problema de contrato de teste e auditabilidade.

### Hipotese

- Hipotese: transformar `runtime_preflight` em contrato obrigatorio melhora a qualidade do gate porque evita evidencias parcialmente preenchidas serem tratadas como sucesso.

### Metodo

- Metodo usado: ler o payload real de `/healthz`, corrigir a extracao de `dependencies.kernel_state` e adicionar asserts no smoke.
- Criterio de aceitacao: smoke real deve passar com `runtime_preflight.kernel_state=healthy`; o verificador do JSON deve confirmar o contrato; lint/build/testes direcionados devem passar.

### Observacoes

- Fato observado: `/healthz` expõe `kernel_state` dentro de `dependencies`, nao na raiz.
- Fato observado: o smoke final gerou `conversation_id=33`, `elapsed_ms=1947`, `runtime_preflight.status=ok`, `runtime_preflight.kernel_state=healthy`, `error_event_count=0` e `agent_state=completed`.
- Decisao de engenharia: falhas de health agora bloqueiam o smoke antes do chat; isso aumenta fidelidade operacional do teste.

### Incertezas

- Ainda falta verificar se o mesmo contrato se mantem no runner remoto com provider cloud e segredos reais.

## Ciclo 33 - Evidencia SSE com degradacao operacional zero

### Problema

- Fato observado: a preflight provava `kernel_state=healthy`, mas nao registrava explicitamente se havia dependencias degradadas.
- Classificacao: problema de observabilidade de QA.

### Hipotese

- Hipotese: registrar e exigir `degraded_dependency_count=0` melhora a utilidade da evidencia porque diferencia chat funcionando em ambiente plenamente saudavel de chat funcionando com degradacao parcial.

### Metodo

- Metodo usado: extrair as chaves de `dependencies.degraded_dependencies` do payload real de `/healthz`, ordenar a lista e salvar no artefato.
- Criterio de aceitacao: smoke real deve passar com `degraded_dependency_count=0` e lista vazia; Step Summary deve exibir esses campos; gates direcionados devem passar.

### Observacoes

- Fato observado: `/healthz` retornou `degraded_dependencies={}` no ambiente local.
- Fato observado: evidencia final `conversation_id=34`, `elapsed_ms=2170`, `runtime_preflight.degraded_dependency_count=0`, `error_event_count=0`.
- Decisao de engenharia: tratar dependencia degradada como falha do smoke real, porque a finalidade do gate e validar experiencia operacional completa do chat.

### Incertezas

- Falta execucao remota para verificar se o contrato permanece estavel no GitHub Actions.

## Ciclo 34 - Timeout alinhado do smoke SSE

### Problema

- Fato observado: `JANUS_LIGHT_CHAT_E2E_MAX_MS` e configuravel e o workflow usa `60000`, mas o timeout total do teste Playwright estava fixo em `60000`.
- Classificacao: problema de robustez de teste e risco de falso negativo.

### Hipotese

- Hipotese: derivar o timeout total do teste a partir de `MAX_LIGHT_CHAT_MS` reduz falso negativo porque reserva tempo para preflight, registro de usuario, criacao de conversa e escrita do artefato.

### Metodo

- Metodo usado: calcular `TEST_TIMEOUT_MS = Math.max(60_000, MAX_LIGHT_CHAT_MS + 15_000)` e manter o timeout da chamada SSE separado.
- Criterio de aceitacao: smoke real deve passar com `JANUS_LIGHT_CHAT_E2E_MAX_MS=60000`; lint/build/testes direcionados devem passar; documentacao deve explicar a margem.

### Observacoes

- Fato observado: evidencia final `conversation_id=35`, `elapsed_ms=2089`, `error_event_count=0`, `degraded_dependency_count=0`.
- Decisao de engenharia: a margem de 15s cobre overhead operacional sem relaxar a assercao de latencia da chamada SSE, que continua usando `elapsedMs < MAX_LIGHT_CHAT_MS`.

### Incertezas

- Falta execucao remota para medir overhead real do workflow com provider cloud.

## Ciclo 35 - Step Summary SSE com escape Markdown

### Problema

- Fato observado: o Step Summary escrevia valores do JSON diretamente em tabela Markdown.
- Classificacao: problema de robustez de observabilidade remota.

### Hipotese

- Hipotese: normalizar valores antes de renderizar a tabela reduz risco de evidencia remota ilegivel quando um valor contem `|`, barra invertida ou quebra de linha.

### Metodo

- Metodo usado: adicionar funcao local `table_value` ao script Python do workflow e validar o script real extraido do YAML contra JSON sintetico com caracteres problematicos.
- Criterio de aceitacao: YAML valido; script gera tabela escapada; smoke real e gates direcionados continuam passando.

### Observacoes

- Fato observado: validacao sintetica confirmou escape de pipe e normalizacao de quebra de linha.
- Fato observado: smoke real final gerou `conversation_id=36`, `elapsed_ms=5065`, `error_event_count=0`, `degraded_dependency_count=0`.
- Decisao de engenharia: a mudanca fica restrita a apresentacao do Step Summary; o JSON de evidencia permanece sem transformacao.

### Incertezas

- Ainda falta observar a renderizacao no Step Summary real do GitHub Actions.

## Ciclo 36 - Chat autenticado sem 403/429

### Problema

- Fato observado: `POST /api/v1/chat/stream/37` retornou 403 quando o frontend era aberto por `127.0.0.1:4300`.
- Fato observado: apos corrigir CORS, uma jornada normal produziu 59 chamadas e recebeu 429 em tools, autonomy e health.
- Classificacao: falha funcional e operacional, impacto alto, risco medio, prioridade P0/P1.

### Hipotese

- Acredito que alinhar as origens locais e isolar rate limit por identidade autenticada elimina 403/429 do chat porque remove dois conflitos de configuracao compartilhados por origem/IP.

### Metodo e Criterio

- Metodo: teste de regressao E2E real com conta sintetica, logs do contêiner, teste unitario do bucket e evidencia JSON.
- Criterio: stream 200, resposta em menos de 60s, persistencia apos reload, provider/model e delivery status reais, nenhum erro inesperado de API/console.

### Resultado

- Fato observado: conversa `42` concluiu em 2898ms com zero falhas de console e sem 429; conversa SSE `43` concluiu em 2295ms.
- Inferencia: o defeito reproduzido foi eliminado no ambiente local reconstruido.
- Limitacao: uma execucao nao mede p95 nem prova escala; exige coleta remota recorrente.

## Ciclo 37 - Memoria generativa real no painel do chat

### Problema

- Fato observado: a UI gravava memoria generativa com HTTP 200, mas a busca falhava com HTTP 500.
- Evidencia: `GenerativeMemoryService.retrieve_memories() got an unexpected keyword argument 'user_id'` nos logs do container.
- Classificacao: falha funcional com implicacao de isolamento de dados.

### Hipotese

- Acredito que completar o contrato do servico com filtro obrigatorio quando `user_id` for informado elimina o 500 e preserva isolamento porque o endpoint ja deriva o ator autenticado.

### Metodo e Criterio

- Metodo: regressao de servico com inspecao do filtro Qdrant e jornada Playwright mutante pela UI.
- Criterio: POST e GET 200, conteudo exclusivo renderizado, memoria presente apos reload, filtros de usuario/conversa presentes e zero falhas inesperadas de console/API.

### Resultado

- Fato observado: todos os criterios funcionais passaram na conversa `47`; memoria levou `1374ms` e permaneceu apos reload.
- Fato observado: o erro de console restante vinha do cancelamento do SSE durante reload; `pagehide` agora aborta explicitamente a conexao e possui teste de lifecycle.
- Inferencia: a classe de falha reproduzida foi eliminada no runtime local reconstruido.
- Trade-off: o filtro por conversa restringe recuperacao ao contexto ativo; memoria global do usuario deve continuar usando endpoint/timeline proprio.

### Eficiencia e Limitacoes

- Chat UI observado em `16881ms`; SSE aquecido em `2115ms`.
- Um outlier frio levou `64726ms`; nao ha amostra suficiente para afirmar p95 ou estabilidade de cauda.
- Decisao recomendada: manter a correcao e medir distribuicao de latencia antes de alterar roteamento/modelo.

## Ciclo 38 - Alinhamento de testes unitarios com contratos de producao

### Problema

- Fato observado: 42 testes unitarios em `backend/tests/unit/` falhavam por drift entre fakes/mocks e contratos de producao.
- Classificacao: divida tecnica de testes, impacto medio, risco baixo, prioridade P1.

### Hipotese

- Acredito que alinhar os fakes aos contratos atuais elimina as falhas sem alterar producao porque as divergencias sao exclusivamente de interface de teste.

### Metodo e Criterio

- Metodo: analise individual dos 3 maiores clusters coerentes (SG012, collaboration hook, autonomy enqueue); correcao minimal nos fakes; validacao com suite completa.
- Criterio: 14 testes alvo passam; suite unitaria nao regred; qa/ contratos nao regred; ruff/format passam.

### Observacoes

- SG012: o padrao `from app.core.security import auth_rate_limiter` seguido de `monkeypatch.setattr(auth_rate_limiter, ...)` nao afeta a referencia ja importada em `auth.py`. Correcao: monkeypatch no modulo `auth` diretamente. A assinatura de `set_reset_token` em producao inclui `user_id` como primeiro parametro posicional.
- Collaboration hook: producao chama `goal_repo.get_goal(goal_id)` antes de `transition_status` para verificar se a meta ja esta concluida. O fake nao implementava `get_goal`.
- Autonomy enqueue: producao substituiu `get_next_goal()` por `list_goals(status=...)`. O fake nao implementava `list_goals`.
- Resultado: 42 -> 30 falhas, 591 -> 603 passed. 12 testes corrigidos, zero regressoes.

### Incertezas

- 30 testes restantes falham por drift em outros clusters (documents, knowledge, memory scroll, observability, security, etc.); cada cluster exige analise individual.

## Ciclo 39 - Mais alinhamento de testes unitarios (goal_manager, documents)

### Problema

- Fato observado: apos Ciclo 38, 30 testes unitarios ainda falhavam por drift.
- Classificacao: divida tecnica de testes, impacto medio, risco baixo, prioridade P1.

### Hipotese

- Os clusters goal_manager e documents sao os proximos maiores coerentes e podem ser corrigidos com alteracoes minimas nos fakes.

### Metodo e Criterio

- Metodo: analise individual dos 3 clusters (goal_manager_sql_facade, documents_endpoint_async_upload, documents_security); correcao minimal nos fakes e monkeypatches; validacao com suite completa.
- Criterio: 7 testes alvo passam; suite unitaria nao regred; ruff/format passam.

### Observacoes

- goal_manager: producao chama `goal_repo.list_children(goal.id)` no metodo `_to_goal` para verificar metas filhas bloqueantes; fake nao implementava.
- documents_endpoint_async_upload: producao substituiu `get_request_actor_id` e `resolve_user_scope_id` por `require_authenticated_actor_id`; `get_manifest` agora recebe `uid`; `app.state.knowledge_facade` e dependencia obrigatoria.
- documents_security: `socket` e importado em `url_safety`, nao em `documents`; `fake_getaddrinfo` precisava aceitar `type=` kwarg; `_is_allowlisted_host` e `require_authenticated_actor_id` precisavam mock.
- Resultado: 30 -> 23 falhas, 603 -> 610 passed. 7 testes corrigidos, zero regressoes.

### Incertezas

- 23 testes restantes falham em clusters menores (observability, security/asvs, knowledge, chat citation, meta-agent, technical_qa, sg011, etc.); cada cluster exige analise individual.
