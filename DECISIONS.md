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
