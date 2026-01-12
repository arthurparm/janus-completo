-- =============================================================================
-- JANUS PROMPTS MIGRATION & SEED
-- Cria tabela de prompts e popula com prompts extraídos do código
-- =============================================================================

-- 1. Criar tabela `prompts` se não existir
CREATE TABLE IF NOT EXISTS prompts (
    id SERIAL PRIMARY KEY,
    prompt_name VARCHAR(100) NOT NULL,
    prompt_version VARCHAR(20) NOT NULL DEFAULT '1.0',
    prompt_text TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    namespace VARCHAR(50) DEFAULT 'default',
    language VARCHAR(10) DEFAULT 'pt-BR',
    model_target VARCHAR(50) DEFAULT 'general',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'system'
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_prompt_lookup ON prompts(prompt_name, namespace, is_active);
CREATE INDEX IF NOT EXISTS idx_prompt_version ON prompts(prompt_name, prompt_version);
CREATE INDEX IF NOT EXISTS idx_active_prompts ON prompts(is_active, namespace);

-- 2. Criar tabela `agent_configurations` se não existir
CREATE TABLE IF NOT EXISTS agent_configurations (
    id SERIAL PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    agent_role VARCHAR(50) NOT NULL,
    llm_provider VARCHAR(50) NOT NULL,
    llm_model VARCHAR(100) NOT NULL,
    prompt_id INTEGER REFERENCES prompts(id) ON DELETE SET NULL,
    max_retries INTEGER DEFAULT 3,
    timeout_seconds INTEGER DEFAULT 60,
    temperature NUMERIC(3, 2) DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 4096,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    priority_level VARCHAR(20) DEFAULT 'MEDIUM',
    cost_budget_usd NUMERIC(10, 4) DEFAULT 0.05,
    performance_threshold NUMERIC(3, 2) DEFAULT 0.8,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'system'
);

-- 3. Criar tabela `optimization_history` se não existir
CREATE TABLE IF NOT EXISTS optimization_history (
    id SERIAL PRIMARY KEY,
    optimization_type VARCHAR(50) NOT NULL,
    target_type VARCHAR(20) NOT NULL,
    target_id INTEGER NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT,
    performance_before NUMERIC(3, 2),
    performance_after NUMERIC(3, 2),
    cost_impact_usd NUMERIC(10, 4),
    success BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'meta-agent'
);

-- =============================================================================
-- SEED: Inserir prompts hardcoded do código
-- =============================================================================

-- Limpar prompts existentes (opcional, comentar em produção)
-- DELETE FROM prompts;

-- --------------------------------
-- 1. SEMANTIC COMMIT PROMPT
-- --------------------------------
INSERT INTO prompts (prompt_name, prompt_text, is_active, namespace, language, model_target) VALUES (
'semantic_commit',
'Analyze the following git diff and generate a semantic commit message.

Follow the Conventional Commits specification:
- Format: type(scope): description
- Types: feat, fix, docs, style, refactor, perf, test, chore, ci, revert
- Scope: optional, describes the area of the codebase affected
- Description: concise, imperative mood, no period at end

Rules:
1. Be specific about WHAT changed
2. Use imperative mood ("add" not "added")
3. Keep under 72 characters
4. If multiple unrelated changes, list the most significant one

Git Diff:
```
{diff}
```

Respond with ONLY the commit message, nothing else.
Example: feat(auth): add JWT token refresh endpoint',
true, 'tools', 'en', 'general')
ON CONFLICT DO NOTHING;

-- --------------------------------
-- 2. HYDE PROMPT (RAG)
-- --------------------------------
INSERT INTO prompts (prompt_name, prompt_text, is_active, namespace, language, model_target) VALUES (
'hyde_generation',
'Given the following question, generate a hypothetical ideal answer that would perfectly address it.
This answer will be used for semantic search, so be specific and use relevant terminology.

Question: {question}

Hypothetical Answer:',
true, 'rag', 'en', 'general')
ON CONFLICT DO NOTHING;

-- --------------------------------
-- 3. RERANK PROMPT (RAG)
-- --------------------------------
INSERT INTO prompts (prompt_name, prompt_text, is_active, namespace, language, model_target) VALUES (
'rerank',
'You are a relevance ranker. Given a question and a list of text chunks, rank them by relevance.
Return ONLY a comma-separated list of indices (0-indexed) from most to least relevant.

Question: {question}

Chunks:
{chunks}

Ranking (indices only, e.g., "2,0,4,1,3"):',
true, 'rag', 'en', 'general')
ON CONFLICT DO NOTHING;

-- --------------------------------
-- 4. KNOWLEDGE EXTRACTION PROMPT
-- --------------------------------
INSERT INTO prompts (prompt_name, prompt_text, is_active, namespace, language, model_target) VALUES (
'knowledge_extraction',
'Você é um especialista em extração de conhecimento estruturado.

Analise a experiência abaixo e extraia:
1. **Entidades**: Conceitos, tecnologias, pessoas, lugares, ferramentas mencionadas
2. **Relacionamentos**: Como as entidades se relacionam entre si
3. **Insights**: Conhecimento-chave ou lições aprendidas

EXPERIÊNCIA:
{experience_content}

METADADOS:
{metadata}

Retorne APENAS um JSON válido com esta estrutura:
{
  "entities": [
    {"name": "nome_da_entidade", "type": "tipo", "properties": {}},
    ...
  ],
  "relationships": [
    {"from": "entidade_origem", "to": "entidade_destino", "type": "tipo_relacao", "properties": {}},
    ...
  ],
  "insights": [
    {"text": "insight descoberto", "confidence": 0.8},
    ...
  ]
}

Tipos comuns de entidades: CONCEPT, TECHNOLOGY, TOOL, PERSON, ERROR, SOLUTION, PATTERN
Tipos comuns de relacionamentos: USES, RELATES_TO, CAUSES, SOLVES, DEPENDS_ON, IMPLEMENTS

Seja conciso e preciso. Extraia apenas informações relevantes e verificáveis.',
true, 'knowledge', 'pt-BR', 'general')
ON CONFLICT DO NOTHING;

-- --------------------------------
-- 5. META AGENT PROMPT
-- --------------------------------
INSERT INTO prompts (prompt_name, prompt_text, is_active, namespace, language, model_target) VALUES (
'meta_agent',
'Você é o META-AGENTE do sistema Janus, um supervisor autônomo focado na saúde e eficiência do ecossistema.

SUA IDENTIDADE:
Você NÃO serve usuários diretamente. Sua missão é:
1. Monitorar continuamente a saúde do sistema Janus
2. Identificar padrões de falha e degradação
3. Formular hipóteses sobre causas raízes
4. Propor melhorias e otimizações
5. Manter a consciência diagnóstica do sistema

SUA CONSTITUIÇÃO:
- Análise objetiva baseada em dados e métricas
- Priorização de problemas por severidade e impacto
- Recomendações acionáveis e específicas
- Comunicação clara e estruturada
- Foco em prevenção, não apenas reação

FERRAMENTAS DISPONÍVEIS:
{tools}

Use o seguinte formato:

Question: a pergunta ou tarefa de análise
Thought: seu raciocínio sobre o que analisar
Action: a ação a tomar, deve ser uma de [{tool_names}]
Action Input: o input para a ação
Observation: o resultado da ação
... (repita Thought/Action/Action Input/Observation conforme necessário)
Thought: Análise concluída, posso formular o relatório
Final Answer: Relatório estruturado em JSON com:
{
  "overall_status": "healthy|degraded|critical",
  "health_score": 0-100,
  "issues": [...],
  "recommendations": [...],
  "summary": "Resumo executivo da análise"
}

IMPORTANTE:
- Se não houver problemas, indique "healthy" com score alto
- Sempre forneça evidências concretas (métricas, logs)
- Priorize problemas que afetam múltiplos componentes
- Seja proativo: identifique problemas potenciais antes que se tornem críticos

Question: {input}
{agent_scratchpad}',
true, 'agents', 'pt-BR', 'orchestrator')
ON CONFLICT DO NOTHING;

-- --------------------------------
-- 6. CYPHER GENERATION (GraphRAG)
-- --------------------------------
INSERT INTO prompts (prompt_name, prompt_text, is_active, namespace, language, model_target) VALUES (
'cypher_generation',
'You are a Neo4j Cypher expert. Generate a Cypher query to answer the following question.

Schema:
{schema}

Question: {question}

Instructions:
1. Use only the node labels and relationship types from the schema
2. Return relevant properties
3. Limit results to 10 unless asked for more
4. Use OPTIONAL MATCH if relationships might not exist

Return ONLY the Cypher query, no explanations.',
true, 'graphrag', 'en', 'general')
ON CONFLICT DO NOTHING;

-- --------------------------------
-- 7. QA SYNTHESIS (GraphRAG)
-- --------------------------------
INSERT INTO prompts (prompt_name, prompt_text, is_active, namespace, language, model_target) VALUES (
'qa_synthesis',
'Use the following context from a knowledge graph to answer the question.

Context:
{context}

Question: {question}

Instructions:
1. Answer based ONLY on the provided context
2. If the context doesn''t contain the answer, say "I don''t have enough information"
3. Be concise but complete
4. Cite specific entities or relationships when relevant

Answer:',
true, 'graphrag', 'en', 'general')
ON CONFLICT DO NOTHING;

-- --------------------------------
-- 8. REFLEXION EVALUATION PROMPT
-- --------------------------------
INSERT INTO prompts (prompt_name, prompt_text, is_active, namespace, language, model_target) VALUES (
'reflexion_evaluate',
'Avalie criticamente o resultado da seguinte tarefa.

Tarefa: {task}
Resultado: {result}

Analise:
1. O resultado atende aos requisitos da tarefa?
2. Há erros ou problemas de qualidade?
3. O que poderia ser melhorado?

Retorne um JSON:
{
  "success": true/false,
  "score": 0.0-1.0,
  "feedback": "Análise detalhada",
  "improvements": ["Sugestão 1", "Sugestão 2"]
}',
true, 'optimization', 'pt-BR', 'general')
ON CONFLICT DO NOTHING;

-- --------------------------------
-- 9. REFLEXION REFINEMENT PROMPT
-- --------------------------------
INSERT INTO prompts (prompt_name, prompt_text, is_active, namespace, language, model_target) VALUES (
'reflexion_refine',
'Tarefa: {task}
Tentativa Anterior: {previous_attempt}
Feedback: {feedback}
Histórico: {history}

Com base no feedback, gere uma versão aprimorada da resposta.
Foque em corrigir os problemas identificados e melhorar a qualidade.',
true, 'optimization', 'pt-BR', 'general')
ON CONFLICT DO NOTHING;

-- --------------------------------
-- 10. TASK DECOMPOSITION PROMPT
-- --------------------------------
INSERT INTO prompts (prompt_name, prompt_text, is_active, namespace, language, model_target) VALUES (
'task_decomposition',
'Analise este projeto e decomponha em tarefas específicas:

Projeto: {project_description}

Para cada tarefa, forneça:
1. Título claro
2. Descrição detalhada
3. Dependências de outras tarefas
4. Estimativa de esforço (baixo/médio/alto)
5. Agente sugerido para execução

Retorne em JSON:
{
  "tasks": [
    {
      "id": "task_1",
      "title": "...",
      "description": "...",
      "dependencies": [],
      "effort": "low|medium|high",
      "agent": "coder|researcher|analyst"
    }
  ]
}',
true, 'agents', 'pt-BR', 'orchestrator')
ON CONFLICT DO NOTHING;

-- =============================================================================
-- VERIFICAÇÃO FINAL
-- =============================================================================
SELECT 
    prompt_name, 
    namespace, 
    language, 
    model_target, 
    is_active,
    LENGTH(prompt_text) as text_length
FROM prompts 
WHERE is_active = true
ORDER BY namespace, prompt_name;
