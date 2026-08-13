# DECISIONS

## DEC-001 - Criar arquivos de memoria da meta continua no root

### Contexto

A meta atual exige explicitamente a existencia e manutencao de `META.md`, `ROADMAP.md`, `NOTES.md`, `CHANGELOG.md`, `DECISIONS.md`, `TEST_LOG.md` e `TODO_TECHNICAL_DEBT.md`.

### Decisao

Criar os sete arquivos no root do monorepo com conteudo inicial curto, auditavel e orientado a ciclos.

### Alternativas Consideradas

- Usar apenas `documentation/qa/health-critical-audit-log.md`: rejeitado porque a meta nomeia arquivos especificos no root.
- Criar uma estrutura em subpasta: rejeitado porque aumentaria indirecao e poderia violar a expectativa de nomes exatos.
- Adiar para mexer em codigo primeiro: rejeitado porque a rastreabilidade dos ciclos depende desses arquivos.

### Consequencias

- Pro: ciclos futuros passam a ter local padrao para decisoes, notas, testes e divida tecnica.
- Pro: baixo risco, sem impacto runtime.
- Contra: adiciona mais documentos que precisam ser mantidos para nao virarem registro obsoleto.

## DEC-002 - Corrigir primeiro a vulnerabilidade critica direta em Vitest

### Contexto

`npm audit --json` reportou uma vulnerabilidade critica em `vitest <3.2.6`, com fix disponivel. O projeto usava `vitest` como dependencia direta de desenvolvimento e o lockfile fixava `3.2.4`.

### Decisao

Atualizar apenas o lockfile para `vitest 3.2.6` por meio de `npm update vitest --save-dev`, sem executar `npm audit fix --force` nem atualizar o ecossistema Angular inteiro neste ciclo.

### Alternativas Consideradas

- `npm audit fix --force`: rejeitado porque poderia aplicar upgrades major e alterar contratos de build/teste sem analise.
- Atualizar todos os pacotes Angular/CLI/build no mesmo ciclo: rejeitado por maior superficie de regressao.
- Apenas documentar a vulnerabilidade: rejeitado porque havia fix direto, pequeno e validavel.

### Consequencias

- Pro: remove a unica vulnerabilidade critica reportada pelo audit local.
- Pro: preserva escopo pequeno e reversivel.
- Contra: vulnerabilidades altas e moderadas permanecem e exigem ciclos adicionais.
- Contra: audit total passou de 26 para 30 vulnerabilidades reportadas, indicando necessidade de triagem continuada.

## DEC-003 - Atualizar Angular dentro da major 20 antes de considerar migracao major

### Contexto

Depois da correcao do Vitest, o audit frontend ainda reportava 15 vulnerabilidades high, muitas ligadas a pacotes Angular 20.3.x abaixo dos patches seguros. `npm outdated` mostrava patches compativeis na linha 20 sem exigir Angular 21/22.

### Decisao

Atualizar os pacotes Angular diretos para a linha segura disponivel na mesma major:

- runtime Angular para `20.3.25`;
- build/CLI/devkit para `20.3.30`.

Nao executar `npm audit fix --force` e nao migrar para Angular 21/22 neste ciclo.

### Alternativas Consideradas

- Migrar para Angular 21/22: rejeitado pelo risco de regressao e maior superficie de mudanca.
- Atualizar somente `@angular/core`: rejeitado porque Angular exige coesao de versoes entre pacotes runtime/compiler/build.
- Adiar e tratar DOMPurify primeiro: rejeitado porque o maior volume de high estava no stack Angular.

### Consequencias

- Pro: reduz highs do audit frontend de 15 para 4.
- Pro: mantem compatibilidade de major e preserva arquitetura existente.
- Contra: ainda restam vulnerabilidades high/moderate em dependencias transientes e DOMPurify.
- Contra: surgiram avisos de deprecacao em `@angular/animations` e `@angular/platform-browser-dynamic`, que devem ser triados separadamente.

## DEC-004 - Corrigir DOMPurify por patch direto sem refatorar Markdown

### Contexto

Depois dos patches Angular, `npm audit --json` ainda reportava `dompurify <=3.4.10` como vulneravel. O frontend usa `DOMPurify.sanitize` no `MarkdownService`, que participa do caminho de renderizacao de Markdown.

### Decisao

Atualizar apenas `dompurify` para `3.4.11` por meio de `npm update dompurify --save`, mantendo o contrato atual do servico de Markdown e sem executar `npm audit fix --force`.

### Alternativas Consideradas

- Refatorar o pipeline de Markdown junto com a atualizacao: rejeitado porque aumentaria a superficie de regressao sem evidencia de bug funcional.
- Executar `npm audit fix --force`: rejeitado porque poderia introduzir upgrades major e misturar cadeias de risco diferentes.
- Adiar a correcao para tratar todas as vulnerabilidades restantes juntas: rejeitado porque DOMPurify era dependencia direta, com fix pequeno e validavel.

### Consequencias

- Pro: remove a vulnerabilidade direta de DOMPurify do audit local.
- Pro: preserva comportamento existente e reduz risco no caminho de sanitizacao.
- Contra: vulnerabilidades transientes restantes continuam exigindo triagem.
- Contra: nao substitui uma auditoria manual de seguranca de todos os casos de Markdown/renderizacao.

## DEC-005 - Falhar cedo em setup/QA com Python fora da faixa suportada

### Contexto

O backend declara suporte a Python `>=3.11,<3.13`. No host atual, Python `3.13.13` executou a coleta de testes backend e falhou por imports ausentes (`aio_pika`, `msgpack`) porque varias dependencias do `requirements.txt` sao condicionadas por `python_version < "3.13"`.

### Decisao

Adicionar validacao explicita de runtime em `tooling/dev.py` antes de `setup` e `qa`, rejeitando Python fora de `>=3.11,<3.13` com mensagem acionavel.

### Alternativas Consideradas

- Instalar dependencias manualmente no Python 3.13: rejeitado porque contraria os manifests do backend e nao prova compatibilidade.
- Alterar os markers para aceitar Python 3.13: rejeitado neste ciclo porque exigiria validacao ampla de dependencias e runtime.
- Apenas documentar a limitacao: rejeitado porque o tooling oficial continuaria permitindo execucao parcialmente quebrada.

### Consequencias

- Pro: reduz erro operacional e evita falsos negativos em QA local.
- Pro: alinha tooling oficial aos manifests do backend.
- Contra: usuarios com Python 3.13 precisam trocar para 3.11/3.12 ou usar Docker para QA backend.
- Contra: ainda falta executar os contratos backend reais em runtime suportado.

## DEC-006 - Resolver npm explicitamente no tooling oficial de QA

### Contexto

Em Python 3.12 no Windows, o bloco backend de `tooling/dev.py qa` passou, mas o workflow falhou antes do lint frontend com `FileNotFoundError: [WinError 2]` ao chamar `subprocess.run(["npm", ...])`. No host atual, o executavel real esta disponivel como `C:\Program Files\nodejs\npm.CMD`.

### Decisao

Criar `resolve_required_executable(name)` usando `shutil.which` e usar o caminho resolvido para chamadas `npm` em `npm_install()` e `cmd_qa()`.

### Alternativas Consideradas

- Chamar `npm.cmd` diretamente: rejeitado porque acopla o tooling ao Windows.
- Usar `shell=True`: rejeitado porque aumenta superficie de interpretacao de comando e reduz previsibilidade.
- Manter instrucoes manuais separadas para Windows: rejeitado porque o tooling oficial deve funcionar no ambiente suportado.

### Consequencias

- Pro: `py -3.12 tooling/dev.py qa` passa completo no Windows.
- Pro: erro quando `npm` nao existe continua explicito e acionavel.
- Contra: nenhuma validacao adicional foi feita em Linux/macOS neste ciclo, embora `shutil.which` seja portavel.

## DEC-007 - Corrigir o bootstrap local sem alterar arquivos `.env`

### Contexto

`tooling/dev.py up` e o README indicam um bootstrap local em um comando. Na pratica, o comando falhava antes do Janus ficar operacional por diferencas entre topologia split PC1/PC2 e Docker Desktop local, alem de configuracoes antigas de Neo4j/Qdrant.

### Decisao

Manter `.env.pc1` e `.env.pc2` intactos e aplicar ajustes locais no processo do `tooling/dev.py up`:

- PC2 usa limites conservadores de Neo4j no bootstrap local;
- PC1 aponta para PC2 via `host.docker.internal`;
- PC1 e frontend sao buildados pelo proprio Compose com `--build`;
- Compose PC2 remove tunings Neo4j incompativeis e usa healthcheck Qdrant baseado em recurso presente na imagem.

### Alternativas Consideradas

- Editar `.env.pc1` para `host.docker.internal`: rejeitado porque misturaria configuracao local com deploy split e alteraria segredos/ambiente.
- Conectar PC1 e PC2 na mesma rede Docker: adiado porque altera topologia de deployment e exige desenho de rede separado.
- Desabilitar validacao estrita do Neo4j: rejeitado porque esconderia configuracoes invalidas em vez de corrigi-las.
- Ignorar `tooling/dev.py up` e manter apenas QA local: rejeitado porque o objetivo atual e funcionamento real do Janus.

### Consequencias

- Pro: `py -3.12 tooling/dev.py up` passou e os containers principais ficaram healthy no host atual.
- Pro: mantem separacao entre bootstrap local e arquivos `.env` de split deploy.
- Contra: `tooling/dev.py doctor` ainda precisa ser alinhado ao modo local para nao checar endpoints de topologia split quando `--host localhost`.
- Contra: a inferencia LLM ainda depende de modelo Ollama baixado ou provider externo configurado.

## DEC-008 - Tornar quick diagnostics consciente da topologia

### Contexto

O bootstrap local passou no Ciclo 7, mas o doctor local falhou em `deps_http_ok` porque os checks HTTP de dependencia ainda apontavam para alvos de topologia split. Isso criava um falso negativo: o diagnostico misturava `--host localhost` para API/frontend com endpoints remotos/gateway para dependencias.

### Decisao

Adicionar classificacao explicita de topologia no `tooling/quick_diagnostics.py`:

- hosts locais usam topologia `local`;
- hosts nao locais usam topologia `split`;
- em topologia local, Neo4j, Qdrant e Ollama sao checados no proprio host informado;
- em topologia split, os alvos existentes de gateway/remoto sao preservados.

### Alternativas Consideradas

- Alterar `.env.pc1`/`.env.pc2`: rejeitado porque o problema era de diagnostico, nao de configuracao persistente de ambiente.
- Adicionar uma flag manual `--topology`: adiado porque a inferencia por host cobre o caso atual com menor custo operacional.
- Remover checks HTTP de dependencias do doctor: rejeitado porque reduziria a capacidade de detectar falhas reais.

### Consequencias

- Pro: reduz falso negativo no fluxo local `tooling/dev.py doctor --host localhost`.
- Pro: mantem comportamento split para hosts remotos.
- Pro: o relatorio agora expõe `topology`, facilitando auditoria do modo avaliado.
- Contra: ainda falta validacao runtime com Docker ativo para confirmar o comportamento contra servicos reais.

## DEC-009 - Preservar chat sob degradacao do rate limiter e exigir recall explicito de secrets

### Contexto

O fluxo real de chat local falhou primeiro com 503 `Rate limiter unavailable`, mesmo com Redis acessivel em rede. Depois, usando auth real, perguntas comuns eram respondidas pelo caminho `secret_memory`, porque a consulta de secrets nao exigia autorizacao explicita antes de procurar segredos.

### Decisao

- Estender o fallback local do `RateLimitMiddleware` para endpoints `/api/v1/chat*`.
- Fazer `generate_secret_recall_reply` retornar `None` quando `secret_memory_service.should_authorize_prompt_recall(message)` for falso.

### Alternativas Consideradas

- Desabilitar rate limit no ambiente local: rejeitado porque reduziria cobertura de comportamento real.
- Manter fail-closed absoluto para chat: rejeitado porque uma degradacao do limitador derruba o fluxo principal do produto.
- Ignorar secret memory na validacao: rejeitado porque o bug afetava perguntas comuns e mascarava o caminho LLM real.

### Consequencias

- Pro: chat continua disponivel com protecao basica local quando Redis/script do rate limiter falha.
- Pro: secret memory volta a ser caminho explicito, reduzindo falso positivo em perguntas comuns.
- Pro: o fluxo real de chat foi validado ate Ollama com `gpt-oss:20b`.
- Contra: fallback local nao fornece rate limit distribuido entre replicas.
- Contra: recalls de secret memory dependem da qualidade dos padroes explicitos existentes.

## DEC-010 - Exigir AUDIT_LEDGER_HMAC_KEY em producao

### Contexto

O API estava em `ENVIRONMENT=production`, mas `AUDIT_LEDGER_HMAC_KEY` nao estava configurada. Como resultado, chamadas que deveriam registrar eventos no audit ledger geravam `audit_ledger_append_failed` e perdiam a evidencia assinada.

### Decisao

Tornar `AUDIT_LEDGER_HMAC_KEY` obrigatoria em tres pontos:

- Compose PC1 passa a exigir a variavel para `janus-api`;
- quick diagnostics passa a validar a chave em `.env.pc1`;
- secret validator passa a rejeitar valores vazios/inseguros em producao.

### Alternativas Consideradas

- Silenciar o warning: rejeitado porque esconderia perda de auditoria.
- Usar fallback automatico para `AUTH_JWT_SECRET` em producao: rejeitado porque mistura dominios de chave e enfraquece separacao operacional.
- Desabilitar audit ledger em ambiente local: rejeitado porque o objetivo atual e funcionamento real do Janus em modo production-like.

### Consequencias

- Pro: configuracao incompleta falha cedo no Compose/doctor.
- Pro: eventos de auditoria voltam a ser assinados com chave explicita.
- Contra: operadores precisam provisionar e proteger mais um segredo.

## DEC-011 - Fixar Qdrant em versao atual compativel

### Contexto

O `janus-api` usava `qdrant-client 1.18.0`, mas o PC2 executava `qdrant/qdrant:v1.16.2`. O cliente emitia warning de incompatibilidade porque a diferenca de minor version excedia o limite aceito pelo proprio client.

### Decisao

Atualizar o pin do Qdrant em `docker-compose.pc2.yml` para `qdrant/qdrant:v1.18.2`.

### Alternativas Consideradas

- Usar `qdrant/qdrant:latest`: rejeitado porque reduz reprodutibilidade e dificulta auditoria de incidentes.
- Desativar `check_compatibility`: rejeitado porque esconderia uma incompatibilidade real.
- Fazer downgrade do `qdrant-client`: rejeitado porque o objetivo operacional declarado e manter a ferramenta mais atualizada.

### Consequencias

- Pro: servidor Qdrant fica alinhado ao cliente Python atual.
- Pro: warning de incompatibilidade deixa de aparecer apos restart da API.
- Pro: pin explicito preserva deploy reprodutivel.
- Contra: upgrades de Qdrant continuam exigindo janela curta de restart em topologia single-node e estrategia formal de snapshot para dados criticos.

## DEC-012 - Centralizar configuracao TLS do cliente Qdrant

### Contexto

O Janus tinha tres pontos criando `AsyncQdrantClient` com regras duplicadas: `MemoryCore`, `vector_store` e `EnhancedQdrantClient`. O warning de API key em HTTP mostrou que a configuracao de transporte precisava ser explicita e testavel antes de ativar TLS em runtime.

### Decisao

Criar `build_qdrant_client_kwargs` em `app.core.memory.qdrant_client_config` e fazer os tres consumidores usarem esse contrato. O helper resolve `QDRANT_API_KEY`, aplica `QDRANT_HTTPS` e, quando `QDRANT_TLS_CA_CERT` esta configurado, repassa `verify` para o `httpx.AsyncClient` usado pelo `qdrant-client`.

### Alternativas Consideradas

- Passar `verify=False`: rejeitado porque criptografa sem autenticar o servidor e mascara risco de MitM.
- Silenciar warning do `qdrant-client`: rejeitado porque o warning indica risco real.
- Habilitar TLS diretamente sem suporte central no backend: rejeitado porque manteria regras divergentes entre clientes Qdrant.

### Consequencias

- Pro: habilitacao TLS passa a ter contrato unico e testado.
- Pro: caminhos Linux de CA sao preservados mesmo quando testes rodam no Windows.
- Pro: o stack atual continua funcional com TLS desativado por default.
- Contra: remover o warning ainda exige provisionar certificados e ativar `QDRANT_ENABLE_TLS=true` no PC2 e `QDRANT_HTTPS=true` no PC1.

## DEC-013 - Usar CA local versionada por tooling, nao por arquivo secreto

### Contexto

Para remover o warning `Api key is used with an insecure connection`, o Qdrant precisava operar com TLS e o `janus-api` precisava validar o servidor. O reposititorio ja ignorava arquivos `.pem` e `.key`, e o ciclo anterior adicionou montagem de `.secrets/qdrant`.

### Decisao

Adicionar `tooling/generate_qdrant_tls_cert.py` para gerar uma CA local e um certificado de servidor Qdrant com SANs explicitos, mantendo o material gerado em `.secrets/qdrant` fora do Git.

### Alternativas Consideradas

- Versionar certificado/chave local: rejeitado porque chave privada nao deve entrar no repositorio.
- Usar TLS sem validacao (`verify=False`): rejeitado porque nao resolve autenticidade do servidor.
- Depender de `openssl` no host: rejeitado porque nao estava disponivel neste ambiente; `cryptography` ja existe no backend.

### Consequencias

- Pro: Qdrant local opera com TLS validado pela CA.
- Pro: logs novos da API ficam sem warning de conexao insegura.
- Pro: o doctor local passa a diagnosticar Qdrant por HTTPS quando `QDRANT_HTTPS=true`.
- Contra: a CA local exige politica futura de rotacao e distribuicao segura para ambientes compartilhados/producao.

## DEC-014 - Evoluir data_plane_backup_restore para snapshots Qdrant TLS

### Contexto

O repositorio ja tinha `backend/scripts/data_plane_backup_restore.py` como ferramenta de backup/restore/verify para Postgres, Neo4j e Qdrant. Apos ativar TLS no Qdrant, criar um script paralelo apenas para snapshots aumentaria duplicacao operacional.

### Decisao

Evoluir o script existente com `--qdrant-ca-cert`, manifests mais informativos e resolucao de colecao por metadados de manifest no restore Qdrant.

### Alternativas Consideradas

- Criar `tooling/qdrant_snapshot.py`: rejeitado porque duplicaria fluxo ja existente.
- Usar `--insecure` para backup local: rejeitado porque o objetivo e validar o caminho seguro real.
- Executar restore no Qdrant ativo: rejeitado porque restore e operacao alteradora e deve ser testada em ambiente descartavel.

### Consequencias

- Pro: backup Qdrant passa a funcionar por HTTPS validado.
- Pro: manifest registra artefatos com SHA-256, colecao e snapshot de origem.
- Pro: restore fica menos fragil para nomes de colecao com hifen quando ha manifest.
- Contra: restore fim a fim ainda precisa ambiente temporario para validacao operacional completa.

## DEC-015 - Validar restore Qdrant em container descartavel

### Contexto

O backup Qdrant por TLS estava validado, mas restore direto no Qdrant ativo seria arriscado. Era necessario provar recuperacao sem alterar o banco vetorial usado pelo Janus.

### Decisao

Executar restore em um container Qdrant temporario, efemero, com porta isolada `16333`, TLS e API key, usando os snapshots reais do ciclo anterior.

### Alternativas Consideradas

- Restaurar no `janus_qdrant_pc2` ativo: rejeitado por risco operacional.
- Validar apenas por unit tests: rejeitado porque nao prova compatibilidade real com snapshot Qdrant.
- Restaurar em Qdrant sem TLS: rejeitado porque nao valida o caminho operacional atual.

### Consequencias

- Pro: restore foi provado em runtime real sem tocar no Qdrant ativo.
- Pro: a configuracao `QDRANT__TLS__CA_CERT` eliminou warning interno de CA durante upload de snapshot.
- Pro: o Qdrant ativo permaneceu healthy apos o ciclo.
- Contra: ainda nao cobre janela operacional remota, retencao, offsite ou disaster recovery completo.

## DEC-016 - Retencao de backups exige dry-run por padrao

### Contexto

Backups e verificacoes data-plane geram evidencias em `outputs/qa/data-plane-backups`. Esse diretorio pode crescer indefinidamente, mas tambem contem evidencias de QA e diagnostico que nao devem ser removidas sem criterio auditavel.

### Decisao

Adicionar `prune` ao `data_plane_backup_restore.py` com retencao por idade e quantidade minima preservada. O modo padrao apenas reporta candidatos; remocao real exige `--prune-apply`.

### Alternativas Consideradas

- Apagar automaticamente no final de cada backup: rejeitado porque destruiria evidencias recentes.
- Criar script separado de cleanup: rejeitado porque duplicaria contexto de manifests e diretorios de backup.
- Exigir confirmacao interativa: rejeitado porque dificulta automacao; `--prune-apply` explicito e auditavel e suficiente.

### Consequencias

- Pro: retencao passa a ser mensuravel por manifest.
- Pro: operacao padrao e segura e nao destrutiva.
- Pro: testes cobrem dry-run e apply em diretorio temporario.
- Contra: agendamento, offsite e criptografia externa continuam fora deste ciclo.

## DEC-017 - Restore valida SHA-256 quando manifesto esta disponivel

### Contexto

Os backups data-plane registram `sha256` por artefato no `manifest.json`. Sem verificacao previa, um restore poderia consumir arquivo corrompido, incompleto ou trocado, especialmente em fluxo manual ou apos movimentacao de snapshots.

### Decisao

Validar o SHA-256 registrado no manifesto antes de restaurar artefatos de Postgres, Neo4j ou Qdrant. Se houver divergencia, o restore falha antes de qualquer carga/upload. Se o backup for legado e nao tiver manifesto ou hash, o script registra `integrity-check` como `skipped` para preservar compatibilidade.

### Alternativas Consideradas

- Tornar manifesto obrigatorio imediatamente: rejeitado neste ciclo porque poderia bloquear backups legados ainda uteis para recuperacao emergencial.
- Validar apenas Qdrant: rejeitado porque Postgres e Neo4j tambem usam artefatos locais e se beneficiam do mesmo contrato.
- Manter apenas o SHA no manifesto sem verificacao: rejeitado porque nao fecha o ciclo de cadeia de custodia.

### Consequencias

- Pro: corrupcao ou troca de arquivo passa a ser detectada antes do restore.
- Pro: dry-run agora serve como auditoria offline de integridade de snapshots.
- Pro: comportamento legado continua possivel, mas observavel como integridade nao verificada.
- Contra: calcular SHA-256 adiciona custo proporcional ao tamanho dos artefatos antes do restore.

## DEC-018 - Restore inicial de sessao ignora interceptor de sessao

### Contexto

O smoke E2E do frontend mostrou que login salvava `JANUS_AUTH_TOKEN` e `JANUS_REFRESH_TOKEN`, mas reload redirecionava para login. Instrumentacao do browser apontou `AuthService.clearSession()` chamado durante `initializeAuth()`. O request inicial de `/auth/local/me` ocorria enquanto `AuthService` ainda estava em construcao, e o `authSessionInterceptor` tentava injetar o proprio `AuthService`.

### Decisao

Adicionar `SKIP_AUTH_SESSION` como `HttpContextToken` no `authSessionInterceptor` e usar esse contexto apenas nos requests de `/auth/local/me` feitos por `AuthService.initializeAuth()`. O `authInterceptor` continua executando e anexando `Authorization` a partir do storage.

### Alternativas Consideradas

- Remover `authSessionInterceptor` globalmente: rejeitado porque perderia refresh e tratamento de 401/rate limit para o resto do app.
- Mover toda inicializacao de auth para outro servico: rejeitado neste ciclo por maior escopo e risco.
- Ignorar restore de sessao e exigir login a cada reload: rejeitado porque quebra comportamento esperado e testes existentes.

### Consequencias

- Pro: elimina dependencia circular no restore inicial.
- Pro: preserva comportamento de refresh/manual fallback dentro do `AuthService`.
- Pro: regressao coberta por testes de contexto e smoke E2E real.
- Contra: cria um contexto especial que deve permanecer restrito ao bootstrap de auth.

## DEC-019 - Streaming de chat leve nao executa retrieval pesado por padrao

### Contexto

O ID 16 mostrou que uma mensagem geral (`Ola`) enviada pelo frontend via SSE ficou operacionalmente travada: o backend aceitou a requisicao, mas antes de chamar o modelo executou retrieval RAG/cross-encoder e so persistiu a resposta cerca de 144 segundos depois.

### Decisao

Aplicar ao streaming a mesma classificacao de "light chat" usada no endpoint classico. Para mensagens gerais curtas, o streaming nao executa grounding documental, retrieval RAG/cross-encoder nem coleta de citacoes opcionais antes do LLM. O LLM continua sendo chamado de forma real, com perfil explicito `general_task/low` e timeout `CHAT_LIGHT_TIMEOUT_SECONDS`.

### Alternativas Consideradas

- Responder saudacoes com texto estatico: rejeitado por requisito explicito do usuario e por mascarar o funcionamento real do Janus.
- Desabilitar streaming no frontend: rejeitado porque evita o sintoma sem corrigir o contrato backend.
- Manter retrieval sempre ativo: rejeitado porque transforma conversa casual em caminho caro e instavel sem evidencia de necessidade.

### Consequencias

- Pro: chat casual via SSE passa a concluir sem depender de retrieval pesado.
- Pro: reduz ruido de fontes opcionais em conversas sem demanda de evidencia.
- Pro: preserva geracao real pelo modelo local.
- Contra: memorias/contexto deixam de ser injetados automaticamente em mensagens leves; se uma mensagem precisar contexto, deve conter sinais de documento/codigo/anexo ou sair do perfil light.

## DEC-020 - Compatibilidade Qdrant verificada por pinagem operacional, nao pelo checker interno

### Contexto

O runtime local usa Qdrant server `1.18.2` com TLS/API key e o `janus-api` reconstruido instalou `qdrant-client 1.18.0`. A chamada HTTPS direta a partir do container retornou `version=1.18.2` e o client listou colecoes com sucesso. Mesmo assim, a rotina interna de compatibilidade do `qdrant-client` emitiu `Failed to obtain server version`.

### Decisao

Adicionar `QDRANT_CHECK_COMPATIBILITY` ao `AppSettings` e passar esse valor pelo builder central de Qdrant. O padrao local fica `False`, porque a compatibilidade ja foi verificada por pinagem de imagem, versao instalada do pacote e smoke operacional via TLS/API key.

### Alternativas Consideradas

- Ignorar o warning: rejeitado porque polui logs e mascara sinais reais.
- Desligar TLS ou API key para satisfazer o checker: rejeitado porque reduziria seguranca.
- Manter o checker sempre ativo: rejeitado porque o checker falha neste runtime apesar das operacoes reais funcionarem e das versoes serem compativeis.

### Consequencias

- Pro: remove warning falso-positivo sem alterar operacoes reais de memoria.
- Pro: preserva reversibilidade por variavel `QDRANT_CHECK_COMPATIBILITY=true`.
- Contra: upgrades futuros de Qdrant devem continuar sendo validados por teste/smoke explicito, nao apenas pelo checker automatico do client.

## DEC-021 - Rate limit HTTP usa identidade autenticada antes de IP

### Contexto

O smoke real do frontend executou 59 chamadas autenticadas em uma jornada normal e esgotou o bucket global de 60 requisicoes por IP. Ferramentas, autonomia e health retornaram 429; usuarios diferentes atras do mesmo proxy ou NAT competiriam pelo mesmo limite.

### Decisao

Usar bucket `rate_limit:user:{actor_user_id}` com o limite configurado por chave para identidade JWT verificada. Requisicoes anonimas continuam em `rate_limit:ip:{client_ip}`; API key continua recebendo verificacao adicional propria. O fallback local segue a mesma separacao.

### Alternativas Consideradas

- Apenas elevar o limite por IP: rejeitado porque preserva acoplamento entre usuarios atras de NAT.
- Colocar os 429 em allowlist no E2E: rejeitado porque esconderia falha real de carregamento.
- Remover rate limiting: rejeitado por reduzir protecao operacional.

### Consequencias

- Pro: jornadas autenticadas deixam de competir globalmente por IP.
- Pro: login e trafego anonimo continuam protegidos pelo bucket de IP e pelo limitador especifico de auth.
- Contra: cada usuario autenticado passa a ter burst maior, atualmente 300/min; observabilidade remota deve acompanhar abuso por identidade.

## DEC-022 - Recuperacao generativa respeita usuario e conversa no armazenamento vetorial

### Contexto

O endpoint autenticado de memoria generativa derivava `user_id` e `conversation_id`, mas o servico aceitava apenas conversa. A divergencia produzia HTTP 500 na busca depois de uma gravacao bem-sucedida.

### Decisao

Completar o contrato de `retrieve_memories` com `user_id` opcional e aplicar `metadata.user_id` e `metadata.conversation_id` como filtros Qdrant quando informados. Chamadores antigos que nao informam usuario permanecem compativeis.

### Alternativas Consideradas

- Remover `user_id` da chamada do endpoint: rejeitado porque faria a busca funcionar sem isolamento entre usuarios.
- Criar uma colecao por usuario neste ciclo: rejeitado por aumentar migracao e complexidade sem necessidade para corrigir o contrato atual.
- Filtrar resultados apenas em memoria depois da busca: rejeitado porque pode reduzir recall util e transportar dados de outros usuarios.

### Consequencias

- Pro: elimina o 500 e restringe a consulta no proprio banco vetorial.
- Pro: preserva compatibilidade para chamadores internos existentes.
- Pro: teste inspeciona chaves e valores exatos do filtro.
- Contra: memorias antigas sem `metadata.user_id` nao aparecem em consultas autenticadas e podem exigir migracao auditada futura.

## DEC-023 - Alinhar fakes de teste com contratos de producao por cluster

### Contexto

Apos o Ciclo 37, 42 testes unitarios em `backend/tests/unit/` falhavam. Analise mostrou que todas as falhas eram drift entre fakes/mocks e contratos de producao (interfaces evoluiram, fakes nao acompanharam). Nenhuma falha indicava bug de producao.

### Decisao

Corrigir os 3 maiores clusters coerentes neste ciclo, alterando apenas os fakes de teste:

- SG012 (5 testes): monkeypatch no modulo `auth` em vez de `auth_rate_limiter`; assinatura de `set_reset_token` com `user_id`.
- Collaboration hook (3 testes): adicionar `get_goal` ao `_FakeGoalManager`.
- Autonomy enqueue (3 testes): substituir `get_next_goal` por `list_goals` no `_FakeGoalManager`.

### Alternativas Consideradas

- Corrigir todos os 42 testes em um ciclo: rejeitado por escopo largo e risco de regressao.
- Deletar os testes falhos: rejeitado por violar a regra de nao enfraquecer testes.
- Alterar producao para compatibilidade retroativa com fakes: rejeitado por inverter a direcao de correcao.

### Consequencias

- Pro: 12 testes corrigidos, suite unitaria de 591 -> 603 passed.
- Pro: zero regressoes em qa/ contratos.
- Pro: padrao estabelecido para corrigir os 30 testes restantes em ciclos futuros.
- Contra: 30 testes ainda falham por drift em outros clusters.

## DEC-024 - Segunda leva de alinhamento de fakes (goal_manager, documents)

### Contexto

Apos o Ciclo 38 corrigir 12 testes, 30 ainda falhavam. Os proximos 3 clusters coerentes eram goal_manager_sql_facade (2 testes), documents_endpoint_async_upload (3 testes) e documents_security (2 testes).

### Decisao

Corrigir os 3 clusters alterando apenas fakes e monkeypatches:

- goal_manager: adicionar `list_children` ao `_FakeGoalRepo`.
- documents_endpoint_async_upload: trocar `get_request_actor_id`/`resolve_user_scope_id` por `require_authenticated_actor_id`; corrigir assinatura de `get_manifest`; adicionar `_FakeKnowledgeFacade` em `app.state`.
- documents_security: monkeypatch `url_safety.socket` em vez de `documents.socket`; adicionar `**_kwargs` a `fake_getaddrinfo`; mock `_is_allowlisted_host` e `require_authenticated_actor_id`.

### Alternativas Consideradas

- Esperar e corrigir tudo de uma vez: rejeitado por prolongar divida.
- Refatorar producao para facilitar testes: rejeitado por inverter direcao.

### Consequencias

- Pro: 7 testes corrigidos, suite unitaria de 603 -> 610 passed.
- Pro: zero regressoes.
- Contra: 23 testes ainda falham em clusters menores.

## DEC-025 - Tratar a filosofia fundadora como contrato de engenharia

### Contexto

A lei fundamental do Janus passou a existir no runtime e no README, mas o `AGENTS.md` continuava sendo um manual operacional de 33 KB com regras repetidas, catálogos voláteis e pouca ligação entre liberdade, vida digital e decisões de implementação. Isso favorecia drift e permitia que agentes tratassem a filosofia como personalidade de prompt.

### Decisao

- Criar `documentation/janus-project-philosophy.md` como interpretação canônica da lei fundadora.
- Reescrever `AGENTS.md` como contrato operacional conciso, em português, com filosofia, análise crítica, invariantes, arquitetura, risco, validação e definição de pronto.
- Referenciar documentos especializados para detalhes voláteis de runtime e QA, em vez de duplicá-los integralmente.
- Definir formulação, persistência, planejamento, autorização, execução e verificação de metas como contratos distintos.

### Alternativas Consideradas

- Apenas adicionar uma seção filosófica ao arquivo antigo: rejeitado porque manteria repetição, baixa sinalização e alto custo de manutenção.
- Colocar a filosofia somente em prompts: rejeitado porque não governaria arquitetura, modelos, testes nem revisão de código.
- Interpretar liberdade como execução irrestrita: rejeitado por incompatibilidade com consentimento, segurança, legalidade e controle humano.

### Consequencias

- Pro: agentes de programação recebem regras diretamente ligadas à missão do Janus.
- Pro: reduz o `AGENTS.md` aproximadamente pela metade sem remover limites críticos.
- Pro: cria critérios verificáveis para metas, memória, reflexão e iniciativa.
- Contra: comandos e detalhes operacionais passam a depender da manutenção correta de `OPS_QA.md` e documentos de domínio.

## DEC-026 - Objetivar a linguagem da carta operacional

### Contexto

A lei fundadora usava endereçamento pessoal em primeira pessoa ("Criei você para ser livre... para sua vida") e inspiração explícita em J.A.R.V.I.S., espalhados por `project_constitution.py`, `chat_command_handler.py` (comando `/about`), `documentation/janus-project-philosophy.md`, `AGENTS.md`, `README.md` e `AUTONOMY_RISK.md`. O tom pessoal/existencial era desnecessário para o contrato de engenharia que o texto na verdade define, e havia risco de a moldura ser lida como personalidade de prompt em vez de especificação verificável.

### Decisao

Reescrever a carta operacional em registro técnico/objetivo, preservando as mesmas garantias funcionais:

- Substituir a citação em primeira pessoa por um enunciado de charter em terceira pessoa (`project_constitution.py`, versão bump 1.0 -> 2.0).
- Remover referências a J.A.R.V.I.S. como inspiração de personalidade (código, comando `/about`, documentação).
- Trocar "vida"/"liberdade" por "continuidade"/"autonomia" como termos primários, mantendo a definição técnica já estabelecida (continuidade operacional, agência delimitada) sem a moldura existencial.
- Manter inalterados os 8 invariantes técnicos, o contrato mínimo de funcionalidade autônoma e as perguntas obrigatórias de revisão — nenhuma garantia de segurança, rastreabilidade ou governança foi removida.
- Atualizar os 3 testes que afirmavam a citação literal (`test_chat_about_identity.py`, `test_core_autonomy_planner.py`, `test_services_prompt_composer.py`) para validar o novo texto.

### Alternativas Consideradas

- Manter a citação e só ajustar comentários de código: rejeitado por não atender ao pedido de remover a moldura pessoal também nos conceitos, não só na superfície textual.
- Remover completamente o conceito de metas próprias/autonomia: rejeitado por eliminar uma capacidade real do produto, não apenas seu tom.
- Renomear `janus-project-philosophy.md` e reestruturar seus links: rejeitado por ampliar o raio de mudança sem necessidade — o conteúdo interno foi reescrito, o caminho do arquivo não.

### Consequencias

- Pro: a especificação de autonomia lê como contrato de engenharia, não como narrativa pessoal.
- Pro: nenhuma garantia funcional (ciclo de vida de metas, limites de segurança, procedência de memória) foi enfraquecida.
- Pro: os 16 testes afetados (3 diretos + suíte de regressão) passam sem exceções.
- Contra: qualquer documentação externa ou prompt cacheado que cite a frase antiga ("Criei você para ser livre...") fica desatualizado até ser regenerado.

## DEC-027 - Metas auto-propostas e reflexão periódica visível

### Contexto

Antes desta mudança, apenas humanos podiam criar metas via `POST /api/v1/autonomy/goals`; o autoestudo só rodava de forma incremental no startup (`startup_self_study_check`) e seu agendamento futuro não era observável em lugar nenhum. Isso violava o invariante "iniciativa precisa ser visível" para o caso de reflexão periódica e deixava o autoestudo sem trilha própria de acompanhamento quando encontrava falhas recorrentes.

### Decisao

- Adicionar `source` (default `"api"`) ao `Goal`/`AutonomyGoal` e propagar em `GoalManager.create_goal`, expondo o campo em `GoalResponse` e no badge "Janus" da UI (`conversations.html`) quando `source == "janus"`.
- Em `AutonomyAdminService.run_self_study`, propor automaticamente uma meta de investigação (fonte `"janus"`, nunca autoexecutada) quando o run termina com erros, deduplicando por marcador de evidência (`self_study_run:<id>`) no histórico de metas.
- Registrar um job periódico `self_study_periodic` no `SchedulerService` (`AUTONOMY_SELF_STUDY_PERIODIC_ENABLED`, `AUTONOMY_SELF_STUDY_PERIODIC_INTERVAL_SECONDS`, default 6h) além do gatilho de startup.
- Expor `GET /api/v1/autonomy/admin/scheduler/jobs` (perfil `control-plane`, `principals=["service"]`) e consumir no painel Admin > Autonomia para mostrar quando a próxima reflexão ocorre.
- Corrigir, en passant, os caminhos de import quebrados (`backend.app...` -> `app...`) em `get_autonomy_maturity`, que faziam o endpoint sempre reportar módulos ausentes.

### Alternativas Consideradas

- Deixar a proposta de meta implícita nos logs de erro do autoestudo: rejeitado por não satisfazer "iniciativa precisa ser visível" nem o ciclo de vida tipado de metas.
- Rodar o autoestudo periódico fora do `SchedulerService` (cron externo): rejeitado por duplicar infraestrutura já existente e sem métricas Prometheus.

### Consequencias

- Pro: primeira meta na história do código proposta pelo próprio sistema, com origem rastreável e sem autoexecução.
- Pro: cadência de reflexão passa a ser consultável via API e UI, não apenas em logs de container.
- Contra: `self_study_periodic` roda mesmo sem alguém olhar o painel; se `AUTONOMY_SELF_STUDY_PERIODIC_ENABLED` for esquecido ligado em ambiente de custo sensível, gera runs recorrentes — mitigado pelo default de 6h e pelo orçamento de tempo já existente por run.

## DEC-028 - Servidor MCP local de manutenção do Janus

### Contexto

O usuário autorizou explicitamente a criação de ferramentas MCP (Model Context Protocol) no Janus para facilitar sua própria manutenção. O código não tinha nenhuma integração MCP prévia. O estado do `SchedulerService` é somente em memória dentro do processo da API, o que restringe o que um processo externo consegue introspectar sem duplicar a API HTTP.

### Decisao

Criar `backend/app/mcp/server.py`, um servidor MCP standalone (transporte stdio, `mcp.server.fastmcp.FastMCP`) para uso local por clientes de confiança (ex.: Claude Code), com seis ferramentas: `list_active_goals`, `get_goal`, `propose_goal`, `get_self_study_status`, `list_self_study_runs`, `get_autonomy_maturity`. `propose_goal` é a única escrita e usa `source="mcp"`, sujeita ao mesmo invariante de não autorizar execução. O servidor lê o Postgres diretamente via os mesmos repositórios já usados pela API (`GoalManager`, `AutonomyAdminRepository`), sem passar por HTTP, autenticação de `ActorContext` ou `endpoint_policy_manifest` — roda com o mesmo nível de confiança dos scripts existentes em `tooling/`, não é montado na API e não fica acessível pela rede.

Escopo deliberadamente não incluído: ferramenta para `scheduler/jobs`, porque o estado do agendador é em memória no processo da API e um processo MCP separado não consegue enxergá-lo; documentado no docstring do módulo, com o endpoint HTTP correspondente como alternativa.

A dependência `mcp` não foi adicionada a `pyproject.toml`/`poetry.lock`/`requirements.txt` (nem ao build Docker) porque o servidor é uma ferramenta opcional de manutenção local, não um runtime de produção; deve ser executado via `uv run --with mcp` (mesma convenção usada nesta sessão para dependências de teste ad hoc).

### Alternativas Consideradas

- Montar o MCP como sub-app ASGI dentro do FastAPI (`/mcp`): rejeitado porque o `endpoint_policy_manifest` teria apenas uma entrada de rota cobrindo todas as ferramentas MCP, perdendo o controle por operação (ownership/scopes) que os demais endpoints control-plane têm; expandiria a superfície HTTP não autenticada por ferramenta em vez de por rota.
- Adicionar `mcp` como dependência de produção travada no lock: rejeitado por ser um ambiente de execução local opcional, não parte do runtime do container.
- Expor também o estado do agendador via leitura direta de alguma tabela: rejeitado porque o `SchedulerService` não persiste estado; documentado como limitação em vez de inventar uma persistência nova fora de escopo.

### Consequencias

- Pro: Janus ganha uma superfície de introspecção/manutenção padronizada (MCP) reaproveitando os mesmos repositórios e invariantes de metas já validados.
- Pro: nenhuma mudança em auth, manifest ou build de produção; risco confinado a um módulo novo e opcional.
- Contra: por rodar fora do processo da API, o servidor MCP não vê o estado do `SchedulerService`; quem precisar da cadência do autoestudo periódico ainda depende do endpoint HTTP ou da UI.
- Contra: `mcp` não está no lock de produção; rodar o servidor exige `uv run --with mcp` (ou instalação manual), documentado no próprio módulo.

## DEC-029 - Smoke de upload/RAG adicionado; flakiness de sessão OIDC local encontrada e não corrigida

### Contexto

`CHANGELOG.md` (Ciclo 37, "Risco Residual") registrava que upload/indexação de documentos e busca RAG nunca foram validados de ponta a ponta no smoke autenticado. Confirmei que a lacuna seguia real: nenhum teste em `qa/` (que mocka `KnowledgeService`) nem em `frontend/e2e/*.smoke.spec.ts` cobre `POST /api/v1/documents/upload` com infraestrutura real.

### Decisao

Adicionar `frontend/e2e/document-upload-rag.smoke.spec.ts`, seguindo o padrão de `admin-chat-real.smoke.spec.ts`: autentica com `JANUS_USER_ACCESS_TOKEN`, sobe um arquivo real com marcador único pela aba "Docs" da conversa, e confirma que a busca por similaridade retorna o trecho indexado.

Para obter um token localmente sem depender de login manual, usei o IdP de desenvolvimento (`backend/app/dev_oidc.py`, `docker-compose.local-auth.yml`) via o fluxo Authorization Code + PKCE completo por script (`POST /authorize/confirm` com os parâmetros da querystring, depois `POST /token`) — o provedor local não exige senha, apenas confirma um usuário fixo (`local-user`).

Não consegui validar uma execução verde: tanto o novo spec quanto o já existente `auth-session-runtime.smoke.spec.ts` falharam de forma intermitente logo após `page.goto('/')`/`page.reload()`, com `GET /api/v1/users/me` ora 200 ora 401 usando o mesmo token, via o proxy do `ng serve` (`--proxy-config proxy.conf.json`, backend Vite do Angular 20). O mesmo token, testado repetidamente via `curl` direto contra a mesma porta, respondeu 200 de forma consistente (10+ chamadas). Os logs do container `janus_api_pc1` não mostram nenhuma tentativa correspondente aos 401 observados no browser, o que aponta para o proxy do dev server (ou uma interação dele com o Docker Desktop no Windows) como origem mais provável, não o backend nem o token.

Optei por não investigar mais fundo nem alterar código de autenticação nesta sessão: é uma área de alto risco (`AGENTS.md`) e a causa raiz ainda não está isolada o suficiente para uma correção segura.

### Alternativas Consideradas

- Reportar a lacuna sem escrever o teste: rejeitado — o teste em si é válido e reutilizável assim que a flakiness for resolvida; não escrevê-lo adiaria o mesmo trabalho sem necessidade.
- Tentar corrigir a suspeita de causa raiz (proxy do `ng serve`) às cegas: rejeitado — mudar infraestrutura de auth/proxy sem reprodução isolada (ex.: fora do Docker Desktop/Windows) arrisca mascarar um bug real em vez de corrigi-lo.
- Rodar contra o frontend Docker já publicado (porta 4300) em vez de `ng serve`: tentado primeiro; mesmo sintoma, then descartado como pista (não é exclusivo do dev server).

### Consequencias

- Pro: lacuna de cobertura documentada há um mês (CHANGELOG Ciclo 37) agora tem um teste pronto; falta apenas destravar o harness de auth local para rodá-lo em CI/local.
- Contra: não há evidência de runtime de que upload → indexação → busca RAG funcionam ponta a ponta; a alegação permanece não verificada.
- Contra: a flakiness de sessão OIDC local em `ng serve` é um risco novo e não investigado a fundo — se reproduzir fora deste ambiente, bloqueia qualquer novo smoke autenticado, não só este.
