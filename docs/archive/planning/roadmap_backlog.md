# Pendências e Prioridades — Projeto Janus

## Sumário Executivo
- Total de pendências: 9
- Itens críticos (prioridade Alta): 6
- Status geral: Em evolução de MVP para Assistente Pessoal Auto‑Evolutivo; várias capacidades já prototipadas (observabilidade, workers, memória básica), mas faltam pilares de persistência por usuário, verificação de fatos, personalização profunda e governança.
- Última revisão: 2025‑11‑14

## Objetivo
Documentar as lacunas e priorizar a implementação para que o Janus atinja a visão de assistente pessoal que pensa, analisa, verifica fatos e aprende continuamente com o uso.

## Organização
- Categorias: Técnicas, Funcionais, Burocráticas
- Nível de urgência: Alta, Média, Baixa
- Formato de cada pendência: Descrição, Data, Prioridade, Responsável, Status, Bloqueadores, Prazo, Impacto, Ações recomendadas, Histórico

---

## Pendências por Categoria e Urgência

### Técnicas (Alta)

- [ ] Persistência de conversas e identidades por usuário/projeto
  - Descrição: Criar armazenamento durável de conversas e perfis com `CRUD` por `user_id/session_id`, RBAC básico e indexação vetorial por usuário e por sessão.
  - Data: 2025‑11‑14
  - Prioridade: Alta
  - Responsável: Backend Eng. + DevOps/SRE
  - Status: Em análise
  - Bloqueadores: Definição de esquema de banco (MySQL/Postgres), estratégia de indexação multi‑tenant em Qdrant, autenticação/federation mínima.
  - Prazo: 3–4 semanas
  - Impacto: Sem esta base não há memória pessoal, personalização ou auditoria confiável.
  - Ações recomendadas: Modelar tabelas `users`, `sessions`, `messages`, `profiles`; criar índices por `user_id/session_id`; adapter de armazenamento vetorial por tenant; RBAC mínimo por role.
  - Histórico: 2025‑11‑14 criado a partir da revisão das prioridades; relacionado a “Identidade e personalização” e “Observabilidade centrada no usuário”.

- [ ] Memória semântica pessoal e consolidação contínua
  - Descrição: Extração de fatos/relacionamentos/resumos e versionamento em grafo (Neo4j) com memória episódica em Qdrant; consolidar periodicamente o conhecimento pessoal.
  - Data: 2025‑11‑14
  - Prioridade: Alta
  - Responsável: Backend Eng. + Workers Team
  - Status: Em desenvolvimento
  - Bloqueadores: Batching e deduplicação em Neo4j; consistência de IDs em Qdrant; definição de score/qualidade dos claims.
  - Prazo: 4–6 semanas
  - Impacto: Eleva precisão, evita repetição de erros e cria “sabedoria” consolidada do usuário.
  - Ações recomendadas: Worker de consolidação com extração de entidades/relacionamentos; escrita transacional em Neo4j; política de versionamento; índice por usuário.
  - Histórico: 2025‑11‑14 reforçado; ver `janus/app/core/workers/knowledge_consolidator.py` e `janus/app/db/graph.py`.

- [ ] Orquestração avançada de agentes
  - Descrição: Fluxos com estados, memória de sessão por tarefa, reentrada e depuração; compatibilizar com meta‑agente/planner existentes.
  - Data: 2025‑11‑14
  - Prioridade: Alta
  - Responsável: Arquiteto/Tech Lead
  - Status: Em análise
  - Bloqueadores: Definição de DSL de tarefas/estados; integração com `meta_agent` e `planner`; tracing completo por fluxo.
  - Prazo: 3–5 semanas
  - Impacto: Habilita “pensar antes de responder” com passos verificáveis e memória de sessão por tarefa.
  - Ações recomendadas: Introduzir camada de “task graph”; armazenar estado por tarefa; hooks de observabilidade; testes de reentrada.
  - Histórico: 2025‑11‑14 reforçado; relacionado a “Observabilidade centrada no usuário”.

- [ ] RAG de documentos pessoais
  - Descrição: Pipeline completo de ingestão (upload, parsing, chunking, embeddings, metadados) e busca híbrida (vetor + grafo) por usuário.
  - Data: 2025‑11‑14
  - Prioridade: Alta
  - Responsável: Backend Eng.
  - Status: Em análise
  - Bloqueadores: Armazenamento seguro de arquivos; quotas por usuário; parsers robustos; enrichment no grafo.
  - Prazo: 3–5 semanas
  - Impacto: Permite respostas baseadas em fatos pessoais atualizados e auditáveis.
  - Ações recomendadas: Serviço de upload assíncrono; parsing para `PDF/DOCX/HTML`; embeddings com metadados; relações contextuais em Neo4j.
  - Histórico: 2025‑11‑14 reforçado; ver `janus/app/core/embeddings/embedding_manager.py` e `janus/app/db/vector_store.py`.

### Técnicas (Média)

- [ ] Observabilidade centrada no usuário
  - Descrição: Tracing por conversa/ação com correlação por `TRACE_ID` e `user_id`, spans por ferramenta/ação, dashboards e trilhas de auditoria.
  - Data: 2025‑11‑14
  - Prioridade: Média
  - Responsável: DevOps/SRE + Backend Eng.
  - Status: Em desenvolvimento
  - Bloqueadores: Propagação de contexto por requisição; mapeamento de usuários em métricas; retenção e privacidade.
  - Prazo: 2–3 semanas
  - Impacto: Reduz MTTR, melhora confiança e possibilita auditoria por usuário.
  - Ações recomendadas: OpenTelemetry com export para Prometheus/Grafana; correlação em middlewares; painéis focados em conversas/ações.
  - Histórico: 2025‑11‑14 reforçado; ver `janus/app/core/infrastructure/logging_config.py` e `janus/grafana/dashboards/janus-overview.json`.

### Funcionais (Alta)

- [ ] Identidade e personalização
  - Descrição: Perfis, preferências persistentes e memória autobiográfica com linha do tempo e evolução temporal por usuário.
  - Data: 2025‑11‑14
  - Prioridade: Alta
  - Responsável: Backend Eng. + Frontend Eng.
  - Status: Em análise
  - Bloqueadores: Modelo de dados de perfis; UI para preferências; sincronização com memória pessoal.
  - Prazo: 2–4 semanas
  - Impacto: Essencial para o “Janus pessoa” (estilo, preferências e evolução).
  - Ações recomendadas: Tabelas de perfil/preferências; API de leitura/escrita; UI de personalização; vincular consolidação ao perfil.
  - Histórico: 2025‑11‑14 criado; relacionado a “Persistência de conversas” e “Memória semântica pessoal”.

- [ ] Ferramentas de produtividade pessoal
  - Descrição: Integrações com calendário, e‑mail, notas e automação web com políticas de consentimento e revisão humana opcional.
  - Data: 2025‑11‑14
  - Prioridade: Média
  - Responsável: Backend Eng. + Frontend Eng.
  - Status: Em análise
  - Bloqueadores: OAuth2/SAML, escopos e consentimentos; sandbox seguro; limites de taxa das APIs externas.
  - Prazo: 4–8 semanas
  - Impacto: Aumenta utilidade prática diária e contexto pessoal em tempo real.
  - Ações recomendadas: Ferramentas para Google/Microsoft (Calendar/Mail/Drive); registro de escopos; telemetria de uso; HITL para ações sensíveis.
  - Histórico: 2025‑11‑14 reforçado; ver `janus/app/core/tools/action_module.py`, `janus/app/core/tools/agent_tools.py`.

### Funcionais (Média)

- [ ] Aprendizado contínuo
  - Descrição: Automação de fine‑tuning leve (LoRA), avaliação A/B e implantação segura baseada em dados colhidos por usuário.
  - Data: 2025‑11‑14
  - Prioridade: Média
  - Responsável: Optimization Team + Backend Eng.
  - Status: Em análise
  - Bloqueadores: Curadoria de dados rotulados; infraestrutura de GPU; governança de modelos; custo operacional.
  - Prazo: 6–8 semanas
  - Impacto: Melhora contínua de precisão e aderência às preferências do usuário.
  - Ações recomendadas: Jobs assíncronos de treino; avaliação A/B; publicação controlada; registro de custos/métricas.
  - Histórico: 2025‑11‑14 reforçado; ver `janus/app/core/optimization/self_optimization.py` e `janus/app/core/llm/llm_manager.py`.

### Burocráticas (Alta)

- [ ] Segurança e governança
  - Descrição: Políticas dinâmicas por usuário/grupo, escopos e consentimentos granulares; revisão humana opcional (HITL) para ações sensíveis.
  - Data: 2025‑11‑14
  - Prioridade: Alta
  - Responsável: Arquiteto/Tech Lead + DevOps/SRE
  - Status: Em análise
  - Bloqueadores: Policy engine; autenticação/autorização robusta; trilhas de consentimento; requisitos de compliance.
  - Prazo: 4–8 semanas
  - Impacto: Base para confiança, auditoria e venda enterprise.
  - Ações recomendadas: Implementar Policy Engine; reforçar RBAC; registro de consentimentos; auditoria exportável.
  - Histórico: 2025‑11‑14 reforçado; ver `janus/app/core/infrastructure/rate_limit_middleware.py` e `janus/app/api/v1/endpoints/tools.py`.

---

-## Prioridades de Implementação
- [ ] Persistência de conversas e perfis
  - Repositório durável (MySQL/Postgres) com CRUD por `user_id/session_id`, indexação vetorial por usuário e RBAC básico.
- [ ] Pipeline de documentos e RAG
  - Upload, parsing (`PDF/DOCX/HTML`), chunking, embeddings via gerenciador, gravação em Qdrant com metadados e enriquecimento de relações em Neo4j.
- [ ] Consolidação de conhecimento
  - Worker que extrai entidades/relacionamentos/claims com score, deduplicação e escrita em grafo e memória episódica.
- [ ] Integrações de produtividade
  - Ferramentas para Google/Microsoft (Calendar/Mail/Drive) registradas com escopos/permissões e telemetria.
- [ ] Orquestração e memória de sessão
  - Camada de “task graph” com estados e memória por tarefa, supervisionada pelo MetaAgent.
- [ ] Aprendizado contínuo
  - Jobs de treinamento (LoRA), avaliação A/B, publicação controlada e registro de custos/métricas.
- [ ] Observabilidade e auditoria
  - Correlação por `TRACE_ID` e `user_id`, spans por ferramenta/ação, dashboards e trilhas de auditoria.
- [ ] Segurança e governança
  - Policy Engine com políticas dinâmicas por usuário/grupo e consentimentos.

## Marcos (Fases)
- [ ] Fase 1 — Fundação do Assistente Pessoal
  - [ ] Persistência de conversas e perfis
  - [ ] Pipeline de documentos e RAG (básico)
  - [ ] Consolidação inicial de conhecimento
  - [ ] Observabilidade por conversa/ação
- [ ] Fase 2 — Conhecimento e Produtividade
  - [ ] RAG híbrido completo (vetor + grafo)
  - [ ] Integrações de calendário/e‑mail/notas
  - [ ] Orquestração com memória de sessão por tarefa
  - [ ] Auditoria e dashboards por usuário
- [ ] Fase 3 — Aprendizado e Governança
  - [ ] Aprendizado contínuo (LoRA/fine‑tuning) com avaliação
  - [ ] Políticas dinâmicas e consentimentos granulares
  - [ ] Revisão humana opcional (HITL) para ações sensíveis
  - [ ] Personalização avançada e memória autobiográfica

## Critérios de Aceitação por Tema
- [ ] Conversas/Perfis: histórico durável por usuário, busca por sessão, RBAC funcional.
- [ ] RAG: upload de documentos, busca relevante em consultas reais, latência aceitável.
- [ ] Consolidação: novos fatos/relacionamentos visíveis no grafo, sem duplicatas.
- [ ] Produtividade: criação/consulta de eventos/emails/notas com autorização explícita.
- [ ] Orquestração: execução de tarefas multi‑passo com estado, reentrada e logs de decisão.
- [ ] Aprendizado: ciclos de treino/regressão controlados, melhora mensurável em tarefas alvo.
- [ ] Observabilidade: tracing completo por conversa, painel por usuário e auditoria exportável.
- [ ] Governança: políticas aplicadas por escopo, registros de consentimento e bloqueios adequados.

## Referências Técnicas (pontos de extensão)
- Entrypoint/DI/Middlewares: `janus/app/main.py`
- LLM/Embeddings: `janus/app/core/llm/llm_manager.py`, `janus/app/core/embeddings/embedding_manager.py`
- Memória (vetorial/grafo): `janus/app/core/memory/memory_core.py`, `janus/app/db/graph.py`, `janus/app/db/vector_store.py`
- Workers: `janus/app/core/workers/knowledge_consolidator.py`, `janus/app/core/workers/data_harvester.py`
- Ferramentas: `janus/app/core/tools/action_module.py`, `janus/app/core/tools/agent_tools.py`
- Observabilidade: `janus/app/core/monitoring/health_monitor.py`, `janus/app/core/infrastructure/logging_config.py`
- Sistema: composição e startup `janus/app/main.py:69-76,140-176,240-256`
- Status do sistema: `janus/app/api/v1/endpoints/system_status.py:43-54,56-135`
- LLM manager e métricas: `janus/app/core/llm/llm_manager.py:23-43,144-169,539-864,1005-1166`
- Broker e filas: `janus/app/core/infrastructure/message_broker.py:19-22,69-123,258-335`

## Próximos Passos
- Iniciar pela persistência de conversas (DB + indexação vetorial por `user_id`).
- Implementar ingestão de documentos e busca RAG mínima.
- Expandir consolidator para escrita sistemática em Neo4j/Qdrant.
- Adicionar tracing por conversa/ação e auditoria de ferramentas.

---

## Plano de Higiene do Grafo de Conhecimento

### Governança de Ontologia
- [ ] Unificar fonte de verdade de tipos de relação e entidades (enum canônico)
- [ ] Registrar todos os `RelationshipType` no bootstrap do grafo
- [ ] Definir convenções: labels em PascalCase, relações em UPPERCASE com underscore
- [ ] Manter catálogo versionado de tipos aceitos e sinônimos

### Qualidade de Dados
- [ ] Normalizar nomes para forma canônica e preservar `original_name`
- [ ] Aplicar limiar de confiança em relações extraídas (ex.: `confidence ≥ 0.6`)
- [ ] Filtrar relações inválidas (origem/destino vazio, `from == to`, nomes muito curtos)
- [ ] Enviar entradas de baixa qualidade para `:Quarantine` com `[:EXTRACTED_FROM]`

### Ingestão e Normalização
- [ ] Padronizar extração via Guardião: sinônimos PT/EN, lematização simples
- [ ] Exigir `source_experience` e opcional `source_snippet` em relações
- [ ] Validar tipos via enum canônico; mapear sinônimos para tipos permitidos

### Estrutura e Índices
- [ ] Garantir constraints e índices essenciais (id único, índices por `name`, `file_path`)
- [ ] Manter multi-labels coerentes em nós de código (`:File:CodeFile`, `:Function:CodeFunction`)
- [ ] Usar propriedades temporais úteis (`discovered_at`, `last_seen`, `consolidated_at`)

### Versionamento e Evolução
- [ ] Adotar versionamento leve para entidades mutáveis (`valid_from`, `valid_to`)
- [ ] Registrar histórico de mudanças por entidade (ex.: `previous_name`)
- [ ] Arestas de reconciliação semântica para mudanças de nomenclatura

### Auditoria e Higiene
- [ ] Criar relatório de auditoria do grafo via API
- [ ] Alertar relações presentes e não registradas em `RelationshipType`
- [ ] Detectar relações fora do padrão de nomenclatura (`^[A-Z_]+$`)
- [ ] Monitorar tamanho da quarentena e taxa de promoção

### Resolução e HITL
- [ ] Workflow de aprovação humana para itens em quarentena
- [ ] Promover relações aprovadas ao grafo principal
- [ ] Rejeitar e registrar motivos; melhorar sinônimos/heurísticas com feedback

### Consultas e Visualizações
- [ ] Painéis por entidade: grau, tipos de arestas, últimas atualizações
- [ ] Subgrafos temáticos (Tecnologia → Ferramentas → Padrões)
- [ ] Trilhas de experiência: `(:Experience)-[:MENTIONS]->(n)` e derivadas

### Performance e Escalabilidade
- [ ] Agrupar `MERGE` em transações por tipo para reduzir N+1
- [ ] Usar índices e chaves compostas em `MATCH` (`name,file_path`)
- [ ] Paginação e limites em queries de exploração

### Segurança e Governança
- [ ] RBAC sobre operações de escrita no grafo
- [ ] Políticas por escopo de usuário (quem pode criar certos tipos/labels)
- [ ] Auditoria exportável de mudanças (quem, quando, o quê)

### APIs e Ferramentas
- [ ] API para registrar novos tipos canônicos (com aprovação)
- [ ] API para sinônimos de entidade/relação (thesaurus vivo)
- [ ] Ferramenta de lint do grafo (valida padrões antes de persistir)

### Testes e Monitoramento
- [ ] Teste que falha se surgir `type(r)` fora do conjunto canônico
- [ ] Teste que garante `RelationshipType` para qualquer aresta criada
- [ ] Métricas: `knowledge_relationships_created_total`, latência por operação, taxa de quarentena

### Quick Wins
- [ ] Registrar todos os tipos usados pelo consolidator no bootstrap
- [ ] Filtrar e quarentenar relações de baixa qualidade
- [ ] Adicionar limiar de confiança e `source_experience/source_snippet`
- [ ] Auditar e corrigir relações não registradas via endpoint

### Avançado
- [ ] Versionamento de entidades e reconciliação semântica
- [ ] Regras de enriquecimento automático (derivar `DEPENDS_ON` de co-uso)
- [ ] HITL com UI para revisão e promoção de quarentena
- [ ] Aprendizado ativo: usar feedback para melhorar sinônimos/heurísticas

### Referências
- Ontologia e registro: `janus/app/db/graph.py:51-73`
- Enum de relações canônicas: `janus/app/models/schemas.py:42-61`
- Guardião de nomenclatura: `janus/app/core/memory/graph_guardian.py:233-276,296-338,339-377,408-451`
- `MENTIONS` e quarentena: `janus/app/core/workers/knowledge_consolidator_worker.py:295-316,327-413`
- Auditoria do grafo: `janus/app/api/v1/endpoints/observability.py:93-97`, `janus/app/services/observability_service.py:108-115`, `janus/app/repositories/observability_repository.py:120-183`
