---
tipo: operacao
dominio: infra
camada: dependencias
fonte-de-verdade: codigo
status: ativo
---

# Bancos Filas e Modelos

## Objetivo
Mapear cada recurso infra ao papel sistêmico que ele cumpre.

## Responsabilidades
- Dizer “quem serve a quem”.
- Explicar impacto de indisponibilidade.

## Entradas
- Compose.
- `AppSettings`.
- Serviços centrais.

## Saídas
- Matriz componente -> host -> recurso -> impacto.

## Dependências
- [[01 - Visão do Sistema/Dependências Externas]]
- [[05 - Infra e Operação/PC1 PC2 e Docker]]

## Papel real de cada recurso
### Postgres
- host: PC1
- acesso operacional: local ao host, publicado em `127.0.0.1:5432`
- papel sistêmico:
  - fonte de verdade transacional do backend via SQLAlchemy
  - guarda identidade e acesso: `users`, `profiles`, `roles`, `user_roles`, `user_privacy_consents`, `oauth_tokens`, `audit_events`
  - guarda chat persistido: `sessions` e `messages`, incluindo metadados JSON de citações, source scope, understanding e estado do agente
  - guarda controle operacional e configuração: `prompts`, `agent_configurations`, `optimization_history`, `outbox_events`, `pending_actions`, `tool_daily_usage`
  - guarda autonomia: `autonomy_runs`, `autonomy_steps`, `autonomy_goals`, transições, sprints, evidências, self-study runs/files/state, enqueue ledger e `autonomy_loop_leases`
  - guarda metadados documentais: `document_manifests` e `knowledge_spaces`
  - também sustenta persistência do checkpointer do `graph_orchestrator` via `AsyncPostgresSaver`
- impacto de falha:
  - no deploy atual, o boot da API depende de Postgres saudável via `depends_on`
  - sem Postgres, o produto perde persistência de chat, identidade, autonomia, prompts, status documental, knowledge spaces, outbox e quotas diárias SQL
  - se o saver do `graph_orchestrator` falhar na inicialização, o fluxo degrada para `MemorySaver`, preservando o app mas perdendo durabilidade do estado do grafo nessa instância

### Redis
- host: PC1
- acesso operacional: local ao host, publicado em `127.0.0.1:6379`
- papel sistêmico:
  - não é fonte de verdade de domínio; é coordenação efêmera
  - sustenta rate limit HTTP com Lua token bucket no `RateLimitMiddleware`
  - sustenta `ConfigService` para hot-reload e broadcast de config via Pub/Sub
  - sustenta `RedisUsageTracker` para spend por provider, budget por tenant/objetivo e quotas temporárias de tools por janela deslizante
- impacto de falha:
  - o kernel tenta inicializar Redis, mas o client opera em fail-open quando indisponível
  - rate limit pode abrir a requisição, responder `503` em produção ou cair para fallback local apenas em endpoints documentais específicos
  - hot-reload distribuído de configuração deixa de funcionar
  - contabilidade de custo e quotas temporárias viram best effort; não afeta a fonte primária de dados do usuário

### RabbitMQ
- host: PC1
- acesso operacional: local ao host, publicado em `127.0.0.1:5672` e `127.0.0.1:15672`
- papel sistêmico:
  - fila e broker para workers assíncronos
  - participa do pipeline de ingestão documental e de dispatch do outbox
- impacto de falha:
  - o backend perde processamento desacoplado e parte do trabalho em background, mas não substitui Postgres, Redis, Neo4j ou Qdrant como banco

### Neo4j
- host: PC2
- acesso operacional: remoto via `NEO4J_URI`, com usuário e senha obrigatórios
- papel sistêmico:
  - fonte de verdade estrutural para conhecimento, não para chat transacional
  - guarda `Experience`, `Entity`, relações consolidadas, code graph (`CodeFile`, `CodeFunction`, `CodeClass`), `SelfMemory` e projeção estrutural de `KnowledgeSpace`
  - é usado por `KnowledgeGraphService`, `KnowledgeRepository`, `KnowledgeService`, `AutonomyAdminService`, `CodeHybridSearchService` e auditorias de observabilidade
- impacto de falha:
  - `GraphDatabase.connect()` pode entrar em modo offline
  - consultas tendem a retornar vazio e `execute()` vira no-op; parte do sistema degrada silenciosamente
  - chat comum ainda pode operar com Qdrant, mas code graph, auditoria de self-memory, consolidação estrutural e consultas de conhecimento perdem utilidade

### Qdrant
- host: PC2
- acesso operacional: remoto via `QDRANT_HOST`, `QDRANT_PORT` e `QDRANT_API_KEY`
- papel sistêmico:
  - fonte de verdade vetorial do sistema
  - coleções observadas:
    - `janus_episodic_memory`
    - `user_chat_<user_id>`
    - `user_docs_<user_id>`
    - `user_memory_<user_id>`
    - `user_secret_<user_id>`
  - sustenta memória episódica, recall do chat, chunks documentais, preferências, regras procedurais, segredos e a indexação consolidada de `KnowledgeSpace`
  - serve como fila persistente implícita da consolidação de conhecimento, porque o `KnowledgeConsolidator` consome apenas itens pendentes em `janus_episodic_memory`
- impacto de falha:
  - `MemoryCore` entra em modo degradado/offline
  - o chat perde enriquecimento RAG, documentos deixam de ser indexados/consultados, citações documentais falham e o consolidator não encontra lote para transformar em Neo4j
  - apenas fluxos que passam por cache local do `MemoryCore` podem sobreviver temporariamente no processo; `index_interaction()` e ingestão documental não têm esse amortecedor

### Ollama
- host: PC2
- acesso operacional: remoto via `OLLAMA_HOST`
- papel sistêmico:
  - inferência local e suporte a tarefas de manutenção, extração e autoestudo
- impacto de falha:
  - perda do provedor local, especialmente relevante com `AUTONOMY_SELF_STUDY_LOCAL_ONLY=true`

## Matriz domínio -> banco dominante
- Identidade, sessão, mensagens, consentimento, auditoria e OAuth -> Postgres
- Prompt/config dinâmica, outbox, pending actions, leases de autonomia e quotas diárias de tools -> Postgres
- Rate limit, Pub/Sub de config e spend/quota temporária -> Redis
- Memória episódica, contexto do chat, preferências, regras, segredos e chunks documentais -> Qdrant
- Conhecimento estruturado, experiência consolidada, code graph, self-memory e grafo de knowledge spaces -> Neo4j
- Knowledge space consolidado -> Postgres + Qdrant + Neo4j

## Leitura operacional
- PC1 concentra dependências que o Compose usa para readiness do backend.
- PC2 concentra dependências que o backend exige por configuração, mas que ficam fora do controle direto do `depends_on`.
- O mapa de falha é assimétrico:
  - queda de PC1 derruba o produto
  - queda de PC2 preserva parte da superfície HTTP, mas remove persistência cognitiva e inferência remota

## Arquivos-fonte
- `backend/app/config.py`
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Conversa e Chat]]
- [[04 - Fluxos End-to-End/Autonomia]]

## Riscos/Lacunas
- O runtime depende de tecnologias distribuídas entre dois hosts com superfícies de falha diferentes.
- Neo4j, Qdrant e Ollama ficam expostos remotamente no PC2, enquanto Postgres, Redis e RabbitMQ ficam restritos ao loopback do PC1.
- `DataRetentionService.cleanup_user_artifacts()` limpa coleções vetoriais hardcoded (`janus_memory`, `janus_knowledge`) que não correspondem às coleções realmente usadas pelo código atual (`janus_episodic_memory` e `user_*`), então a retenção cross-store não está alinhada com a persistência real.
