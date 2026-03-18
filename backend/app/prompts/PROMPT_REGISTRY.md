# Janus Prompt Registry

Mapeamento canonico de cada prompt para seu subsistema (ponta) do Janus.

Cada arquivo `.txt` pertence a exatamente um subsistema e e consumido por
componentes especificos do backend. A organizacao em subdiretorios reflete
essa relacao: o diretorio e o subsistema.

---

## Arquitetura de Prompts

```
backend/app/prompts/
  identity/       Personalidade e limites do sistema
  agents/         Agentes especializados (ReAct)
  autonomy/       Planejamento e execucao autonoma
  capabilities/   Habilidades reutilizaveis de raciocinio
  context/        Gestao e compressao de contexto
  meta_agent/     Supervisao e diagnostico do sistema
  reflexion/      Auto-correcao iterativa
  knowledge/      Extracao de conhecimento e memoria
  rag/            Retrieval-Augmented Generation e Knowledge Graph
  tasks/          Protocolos especificos por tipo de tarefa
  tools/          Criacao, validacao e documentacao de ferramentas
  security/       Auditoria de seguranca e red-team
  debate/         Avaliacao multi-perspectiva (proponente/critico)
  workers/        Workers utilitarios e templates genericos
  training/       Aprendizado a partir de experiencias
  reasoning/      Raciocinio e recuperacao de erros
  ui/             Formatacao de saida e UI generativa
```

---

## Mapeamento Completo

### `identity/` - Identidade do Sistema (3 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `system_identity` | Personalidade base e diretrizes comportamentais | `SystemIdentityModule`, `PromptComposer` |
| `system_identity_enforcement` | Regras de identidade e limites operacionais | `SystemIdentityModule` |
| `janus_identity_jarvis` | Persona inspirada em JARVIS | `SystemIdentityModule` |

### `agents/` - Agentes Especializados (9 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `agent_coder` | Codigo: producao, refatoracao, debug | `SpecializedAgent` |
| `agent_documenter` | Documentacao de APIs e codigo | `SpecializedAgent` |
| `agent_optimizer` | Performance e otimizacao | `SpecializedAgent` |
| `agent_project_manager` | Coordenacao de tarefas e progresso | `SpecializedAgent` |
| `agent_researcher` | Pesquisa baseada em evidencias | `SpecializedAgent` |
| `agent_self_optimization` | Auto-melhoria do sistema (safety-critical) | `SpecializedAgent` |
| `agent_sysadmin` | DevOps/infraestrutura | `SpecializedAgent` |
| `agent_tester` | QA: validacao, edge cases, regressao | `SpecializedAgent` |
| `agent_thinker` | Arquitetura e design tecnico | `SpecializedAgent`, `ThinkerAgentWorker` |

### `autonomy/` - Planejamento Autonomo (6 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `autonomy_plan_draft` | Gera planos de execucao (Goal -> JSON plan) | `AutonomyPlanner` |
| `autonomy_plan_critique` | Valida qualidade de planos | `AutonomyPlanner` |
| `autonomy_plan_refine` | Refina planos com base em criticas | `AutonomyPlanner` |
| `autonomy_replanner` | Recupera de falhas na execucao | `AutonomyPlanner` |
| `autonomy_verifier` | Valida sucesso de cada passo | `AutonomyPlanner` |
| `autonomy_reasoning_assistant` | Raciocinio complexo durante autonomia | `AutonomyPlanner` |

### `capabilities/` - Habilidades Reutilizaveis (5 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `capability_chain_of_thought` | Decomposicao passo-a-passo | `ReasoningProtocolModule`, `AdvancedPrompts` |
| `capability_code_review` | Avaliacao de qualidade de codigo | `ReasoningProtocolModule`, `AdvancedPrompts` |
| `capability_hypothesis_debugging` | Debugging cientifico por hipoteses | `ReasoningProtocolModule`, `AdvancedPrompts` |
| `capability_multi_agent_coordination` | Orquestracao multi-agente | `AdvancedPrompts` |
| `capability_self_correction` | Deteccao e correcao de erros | `AdvancedPrompts` |

### `context/` - Gestao de Contexto (6 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `context_compression` | Compressao inteligente de conversas | `ContextCompressionModule`, `JanusSpecializedPrompts` |
| `context_compressed_conversation_section` | Template de historico comprimido | `ContextCompressionModule` |
| `context_recent_conversation_section` | Template de mensagens recentes | `ContextCompressionModule` |
| `context_memories_section` | Template de fatos persistidos | `ContextCompressionModule` |
| `context_summary_section` | Template de resumo de alto nivel | `ContextCompressionModule` |
| `specialized_context_compression` | Estrategia alternativa de compressao | `ContextCompressionModule` |

### `meta_agent/` - Supervisao do Sistema (6 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `meta_agent` | Monitoramento de saude (ReAct + JSON) | `MetaAgent`, `MetaAgentCycle` |
| `meta_agent_act_template` | Analise estrategica de licoes | `MetaAgentCycle` |
| `meta_agent_diagnosis` | Causa raiz + severidade | `MetaAgentCycle` |
| `meta_agent_plan_template` | Planejamento de investigacao | `MetaAgentCycle` |
| `meta_agent_planning` | Diagnosticos -> planos de acao | `MetaAgentCycle` |
| `meta_agent_reflection` | Revisao de planos para seguranca | `MetaAgentCycle` |

### `reflexion/` - Auto-Correcao (4 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `reflexion_execution` | Diagnostico de falhas -> correcao | `ReflexionWorker` |
| `reflexion_evaluate` | Score de qualidade (0-1) | `ReflexionWorker` |
| `reflexion_analysis` | Analise de padroes de erro | `ReflexionWorker` |
| `reflexion_refine` | Melhoria iterativa de tentativas | `ReflexionWorker` |

### `knowledge/` - Conhecimento e Memoria (6 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `knowledge_extraction` | Extracao de entidades/relacoes | `KnowledgeService` |
| `knowledge_extraction_system` | Extracao de alta precisao | `KnowledgeExtractionService` |
| `knowledge_wisdom_extraction` | Extracao de sabedoria e padroes | `KnowledgeExtractionService` |
| `memory_integration` | Integra experiencias no knowledge graph | `JanusSpecializedPrompts`, `MemoryService` |
| `memory_rating` | Pontuacao de importancia (1-10) | `MemoryService` |
| `specialized_memory_integration` | Integra memorias em respostas naturais | `MemoryService` |

### `rag/` - RAG e Knowledge Graph (8 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `graph_query_planning` | Traduz perguntas para Cypher | `JanusSpecializedPrompts`, `GraphRAGCore` |
| `graph_rag_synthesis` | Sintetiza respostas do grafo | `GraphRAGCore` |
| `specialized_graph_query_planning` | Planejamento detalhado de queries | `GraphRAGCore` |
| `cypher_generation` | Geracao direta de Cypher | `GraphRAGCore` |
| `hyde_generation` | Documentos hipoteticos para HyDE | `RAGService` |
| `qa_synthesis` | Sintese de QA do grafo | `GraphRAGCore` |
| `rerank` | Re-ranqueamento por relevancia | `SemanticRerankerService` |
| `rag_conversation_summary` | Sumarizacao para contexto RAG | `RAGService` |

### `tasks/` - Protocolos de Tarefa (7 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `task_code_review_protocol` | Ler -> Focar -> Citar -> Corrigir | `TaskSpecificModule` |
| `task_debugging_protocol` | Entender -> Investigar -> Testar -> Corrigir | `TaskSpecificModule` |
| `task_decomposition` | Decomposicao estruturada em JSON | `TaskSpecificModule`, `TaskService` |
| `task_question_protocol` | Basear em fontes, ser direto | `TaskSpecificModule` |
| `task_script_generation_protocol` | Confirmar deps, escrever, explicar | `TaskSpecificModule` |
| `task_tool_creation_protocol` | Usar fluxo de criacao completo | `TaskSpecificModule` |
| `multi_agent_decomposition` | Decomposicao multi-agente (JSON array) | `MultiAgentSystem` |

### `tools/` - Ferramentas (6 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `tool_specification` | Design: JSON spec (nome, args, safety) | `EvolutionManager` |
| `tool_generation` | Implementacao Python com @tool | `EvolutionManager` |
| `tool_validation` | Revisao de seguranca e qualidade | `EvolutionManager` |
| `tool_documentation` | Documentacao de uso para o LLM | `ToolDocumentationModule` |
| `evolution_tool_specification` | Spec para evolucao do sistema | `ReasoningProtocolModule` |
| `evolution_tool_generation` | Geracao de codigo de evolucao | `EvolutionManager` |

### `security/` - Seguranca (3 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `security_red_team` | Auditoria adversarial (pentester) | `RedTeamAgentWorker` |
| `security_red_team_audit` | Busca de vulnerabilidades + scoring | `RedTeamAgentWorker` |
| `professor_code_review` | Revisao senior: APPROVED/REJECTED | `ProfessorAgentWorker` |

### `debate/` - Avaliacao Multi-Perspectiva (2 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `debate_proponent_prompt` | Gera codigo Python robusto | `DebateProponentWorker` |
| `debate_critic_prompt` | Audita seguranca e edge cases | `DebateCriticWorker` |

### `workers/` - Workers Utilitarios (5 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `leaf_worker_assistant` | Worker generico de assistencia | `LeafWorker` |
| `leaf_worker_coder` | Worker de engenharia | `LeafWorker` |
| `leaf_worker_sysadmin` | Worker de infraestrutura | `LeafWorker` |
| `code_agent_task` | Template de tarefa de codigo | `CodeAgentWorker` |
| `react_agent` | Template generico ReAct | `LeafWorker`, `SpecializedAgent` |

### `training/` - Aprendizado (3 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `training_action_success_prompt` | Documenta acoes bem-sucedidas | `NeuralTrainingSystem` |
| `training_lessons_learned_prompt` | Extrai licoes generalizaveis | `NeuralTrainingSystem` |
| `training_metadata_context_prompt` | Metadados para amostras de treino | `NeuralTrainingSystem` |

### `reasoning/` - Raciocinio e Recuperacao (3 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `error_recovery` | Recuperacao inteligente com prevencao | `JanusSpecializedPrompts`, `FallbackChain` |
| `specialized_error_recovery` | Recuperacao de erros de ferramentas | `FallbackChain` |
| `reasoning_session` | Sessao ReAct com tool calls | `ReasoningCore` |

### `ui/` - Formatacao de Saida (2 prompts)

| Prompt | Descricao | Consumidores |
|--------|-----------|-------------|
| `generative_ui` | Tabelas e blocos de UI opcionais | `GenerativeUIModule` |
| `semantic_commit` | Mensagens de commit semantico | `SemanticCommitService` |

---

## Fluxo de Carregamento

```
Prompt solicitado pelo nome (ex: "agent_coder")
       |
       v
  1. Banco de dados (PostgreSQL) -- via PromptRepository
       |  (miss)
       v
  2. Provider externo (se configurado)
       |  (miss)
       v
  3. Arquivo local -- busca recursiva em subdiretorios
       |  (miss)
       v
  4. Fallback em memoria (dict PROMPTS)
       |  (miss)
       v
  KeyError
```

Os nomes dos prompts sao os nomes dos arquivos sem extensao `.txt`.
A organizacao em subdiretorios nao afeta o nome: `agents/agent_coder.txt`
continua sendo referenciado como `"agent_coder"`.

---

## Sincronizacao

O script `backend/scripts/sync_prompts.py` varre recursivamente todos os
subdiretorios de `backend/app/prompts/` e sincroniza cada `.txt` com o
banco de dados. Executado automaticamente antes do start da API.

**Total: 84 prompts em 16 subsistemas**
