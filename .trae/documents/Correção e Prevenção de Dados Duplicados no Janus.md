## Escopo e Armazenamentos
- MySQL/SQLAlchemy: `users`, `profiles`, `roles/user_roles`, `consents`, `oauth_tokens`, `experiments`, `experiment_arms/results/assignments`, `autonomy_runs/steps`, `pending_actions`, `model_deployments`.
- Neo4j (grafo): nós como `Experience`, `Concept`, `File/CodeFile`, `Function/CodeFunction`, `Class/CodeClass`, `Quarantine` e relações (`GraphRelationship`).
- Qdrant (vetorial): coleções por usuário (`user_{user_id}`) e memória episódica (`janus_episodic_memory`).
- JSON (arquivo): `data/chat_store.json` e metadados em `workspace/models/*/metadata.json`.

## Critérios de Duplicidade
- MySQL:
  - Chave natural/canônica: `users` (`email` e/ou `external_id`), `experiments` (`name` por escopo/namespace), `consents` (`user_id + scope`), `oauth_tokens` (`user_id + provider`).
  - Heurística: igualdade em combinações de campos‑chave e alta similaridade textual (opcional) quando `email` vazio.
- Neo4j:
  - Conceitos duplicados por `Concept.name` idêntico.
  - Arquivos por `File.path` e `CodeFile.path` idênticos.
  - Funções/classes por par `(name, file_path)` idêntico.
  - Experiências por `Experience.name` fraco; usar `Experience.id`/`ts_ms` e `content_hash` canônico.
- Qdrant:
  - Mesmos conteúdos (normalizados) com `content_hash` idêntico no mesmo usuário/coleção.
  - Chaves compostas colidindo (`doc:{user_id}:{doc_id}:{i}`) em reprocessamentos.
- JSON:
  - Mensagens repetidas por conteúdo/id gerado indevidamente; metadados de modelo duplicados por cópia de pastas.

## Detecção (Análise Inicial)
- MySQL (amostras de queries):
  - `SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1;` (`janus/app/models/user_models.py:1-22`).
  - `SELECT external_id, COUNT(*) FROM users WHERE external_id IS NOT NULL GROUP BY external_id HAVING COUNT(*) > 1;`.
  - `SELECT name, COUNT(*) FROM experiments GROUP BY name HAVING COUNT(*) > 1;` (`janus/app/repositories/ab_experiment_repository.py:17-27`).
  - `SELECT user_id, scope, COUNT(*) FROM consents GROUP BY user_id, scope HAVING COUNT(*) > 1;` (`janus/app/models/user_models.py:79-92`).
- Neo4j (Cypher):
  - Conceitos: `MATCH (c:Concept) WITH c.name AS name, collect(c) AS cs WHERE size(cs) > 1 RETURN name, size(cs);` (`janus/app/repositories/knowledge_repository.py:329-367`).
  - Funções: `MATCH (f:Function) WITH f.name AS name, f.file_path AS fp, collect(f) AS fs WHERE size(fs) > 1 RETURN name, fp, size(fs);` (`janus/app/core/memory/knowledge_graph_manager.py:168-190`).
  - Arquivos: `MATCH (f:File) WITH f.path AS p, collect(f) AS fs WHERE size(fs) > 1 RETURN p, size(fs);` (`janus/app/db/graph.py:262-284`).
- Qdrant:
  - Busca por payload `content_hash`: agrupar por `metadata.content_hash` e contar (`janus/app/core/memory/memory_core.py:148-186`, `janus/app/services/document_service.py:211-229`).
  - Verificar colisões em ids `doc:*` e `chat:*`.
- JSON:
  - `conversation_id` duplicado (incomum): varrer `data/chat_store.json` e agrupar por id (`janus/app/repositories/chat_repository.py:46-61`).

## Mecanismo de Correção
- MySQL (transacional, por tabela):
  1. Escolher registro canônico por grupo (critério: mais completo, `created_at` mais antigo, ou o que tem mais FKs).
  2. Reapontar chaves estrangeiras de duplicados para canônico (ex.: mensagens/sessions/consents/tokens/assignments/audit/pending_actions).
  3. Registrar ação em relatório (DB + arquivo JSON) e apagar duplicados.
  4. Aplicar constraints `UNIQUE` para prevenir (ver seção “Prevenção”).
  - Pontos de escrita: `janus/app/repositories/user_repository.py:92-111,123-138,188-205`, `janus/app/repositories/ab_experiment_repository.py:17-27`, `janus/app/repositories/pending_action_repository.py:17-26`, `janus/app/repositories/deployment_repository.py:46-76`.
- Neo4j (preservação de relações):
  1. Para cada grupo duplicado (ex.: `Concept.name`), escolher nó canônico.
  2. Reanexar relações de duplicados ao canônico (saída/entrada) copiando propriedades.
  3. Apagar nós duplicados e atualizar métricas/auditoria.
  4. Criar constraints de node key para prevenir.
  - Sem APOC: executar MERGE/reatribuição manual em transação (`janus/app/db/graph.py:262-284`).
  - Repositório envolvido: `janus/app/repositories/knowledge_repository.py:306-328,329-367`.
- Qdrant:
  1. Calcular `content_hash` (SHA‑256 de conteúdo normalizado) em ingestão.
  2. Marcar duplicados (`status='duplicate'`) e remover pontos redundantes mantendo o canônico (mais antigo ou maior contexto).
  3. Reindexar buscas para ignorar `status='duplicate'`.
  - Escritas atuais: `janus/app/core/memory/memory_core.py:148-186`, `janus/app/services/document_service.py:211-229`, `janus/app/services/chat_service.py:313-341`.
- JSON:
  1. Varredura e dedupe por `message_id`/`content_hash` com preservação de ordem temporal.
  2. Migrar conversas do arquivo para DB quando aplicável.

## Relatórios Detalhados
- Estrutura: por armazenamento/tabela/label/coleção.
- Campos: total de duplicidades, chaves que motivaram identificação, registros canônicos escolhidos, IDs remapeados, ações executadas (delete/merge/update), tempo e autor (sistema).
- Saídas:
  - DB: tabela `dedupe_reports`.
  - Arquivo: `reports/duplicates-YYYYMMDD.json` e CSV.
- Endpoints: export e visualização em `observability` (`janus/app/api/v1/endpoints/observability.py:110-164`).

## Prevenção (Verificações/Constraints)
- MySQL:
  - `users`: adicionar `UNIQUE(email)` e `UNIQUE(external_id)`; índice composto `idx_user_lookup` já existe (`janus/app/models/user_models.py:16-20`).
  - `experiments`: `UNIQUE(name)` ou por `namespace` se houver; reforçar `experiment_assignments` (já `UNIQUE(experiment_id, user_id)`).
  - `consents`: já tem `UNIQUE(user_id, scope)`.
  - `oauth_tokens`: já tem `UNIQUE(user_id, provider)`.
  - Adotar upsert (`INSERT ... ON DUPLICATE KEY UPDATE`) nos repositórios de criação/atualização.
- Neo4j:
  - Node keys (Neo4j 5):
    - `FOR (c:Concept) REQUIRE (c.name) IS UNIQUE`.
    - `FOR (f:Function) REQUIRE (f.name, f.file_path) IS NODE KEY`.
    - `FOR (cl:Class) REQUIRE (cl.name, cl.file_path) IS NODE KEY`.
    - `FOR (cf:CodeFile) REQUIRE (cf.path) IS UNIQUE`.
  - Padronizar `MERGE` com chaves canônicas nos repos/serviços.
- Qdrant:
  - Adicionar `metadata.content_hash` e usar `id=content_hash` quando possível (documentos/chunks); para mensagens, manter `id` atual e marcar duplicidade por payload.
  - Filtros padrão ignorando `status='duplicate'`.
- JSON:
  - `message_id` gerado com UUID v4 e `content_hash` para detectar repetição.

## Integridade Referencial
- MySQL: executar remapeamento de FKs dentro de transações com bloqueios de linha; validar contagens antes/depois.
- Neo4j: transações para reanexar relações; preservar propriedades e timestamps; auditar (`record_audit_event_direct`) (`janus/app/repositories/observability_repository.py:307-336`).
- Qdrant: remover pontos duplicados somente após confirmação de que não são referenciados por índices auxiliares; manter canônico.

## Fluxo de Execução
- Fase 1 (Dry‑run): rodar detecções e gerar relatórios sem tocar nos dados.
- Fase 2 (MySQL): dedupe transacional com migração de FKs e criação de constraints.
- Fase 3 (Neo4j): reconciliação e criação de node keys; ajustar `MERGE` nos repos.
- Fase 4 (Qdrant/JSON): hash, marcação e limpeza; filtros em busca.
- Fase 5 (Prevenção): ativar validações nos serviços e testes automáticos.

## Validação e Testes
- Testes de integração para cada dedupe (antes/depois: contagens, FKs válidas, buscas retornam canônicos).
- Simulações com datasets sintéticos para Neo4j (duplicatas de conceitos/funcões/arquivos).
- Observabilidade: métricas Prometheus e auditoria por usuário/ação (`janus/app/api/v1/endpoints/observability.py:110-164`).

## Riscos e Mitigações
- Perda de informação: combinar propriedades e preservar o mais completo; manter registro de merge.
- Conflitos de escrita: executar em janela de manutenção com locks/batch.
- Performance: processar por lote e paginar; índices/constraints previamente criados.

## Entregáveis
- Scripts de detecção/correção por armazenamento.
- Relatórios detalhados (JSON/CSV) e endpoint de export.
- Constraints e lógicas de upsert/merge aplicadas.
- Documentação do processo e instruções de operação.

Confirma proceder com a implementação conforme o plano acima? 