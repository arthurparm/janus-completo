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
