-- Configuration-as-Data: Tabelas para configurações dinâmicas do Janus
-- Permite que o Meta-Agent modifique prompts e configurações de agentes

-- Tabela de Prompts: Armazena templates de prompts versionados
CREATE TABLE IF NOT EXISTS prompts
(
    id
    INT
    AUTO_INCREMENT
    PRIMARY
    KEY,
    prompt_name
    VARCHAR
(
    100
) NOT NULL,
    prompt_version VARCHAR
(
    20
) NOT NULL DEFAULT '1.0',
    prompt_text TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    namespace VARCHAR
(
    50
) DEFAULT 'default',
    language VARCHAR
(
    10
) DEFAULT 'pt-BR',
    model_target VARCHAR
(
    50
) DEFAULT 'general',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR
(
    100
) DEFAULT 'system',

    -- Índices para performance
    INDEX idx_prompt_lookup
(
    prompt_name,
    namespace,
    is_active
),
    INDEX idx_prompt_version
(
    prompt_name,
    prompt_version
),
    INDEX idx_active_prompts
(
    is_active,
    namespace
),

    -- Constraint para garantir apenas um prompt ativo por nome/namespace
    UNIQUE KEY unique_active_prompt
(
    prompt_name,
    namespace,
    is_active,
    language,
    model_target
)
    );

-- Tabela de Configurações de Agentes: Armazena configurações dinâmicas
CREATE TABLE IF NOT EXISTS agent_configurations
(
    id
    INT
    AUTO_INCREMENT
    PRIMARY
    KEY,
    agent_name
    VARCHAR
(
    100
) NOT NULL,
    agent_role VARCHAR
(
    50
) NOT NULL,
    llm_provider VARCHAR
(
    50
) NOT NULL,
    llm_model VARCHAR
(
    100
) NOT NULL,
    prompt_id INT,
    max_retries INT DEFAULT 3,
    timeout_seconds INT DEFAULT 60,
    temperature DECIMAL
(
    3,
    2
) DEFAULT 0.7,
    max_tokens INT DEFAULT 4096,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    priority_level ENUM
(
    'LOW',
    'MEDIUM',
    'HIGH',
    'CRITICAL'
) DEFAULT 'MEDIUM',
    cost_budget_usd DECIMAL
(
    10,
    4
) DEFAULT 0.05,
    performance_threshold DECIMAL
(
    3,
    2
) DEFAULT 0.8,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by VARCHAR
(
    100
) DEFAULT 'system',

    -- Chave estrangeira para prompts
    FOREIGN KEY
(
    prompt_id
) REFERENCES prompts
(
    id
)
                                                   ON DELETE SET NULL,

    -- Índices para performance
    INDEX idx_agent_lookup
(
    agent_name,
    agent_role,
    is_active
),
    INDEX idx_agent_provider
(
    llm_provider,
    llm_model
),
    INDEX idx_active_configs
(
    is_active,
    agent_role
),

    -- Constraint para garantir apenas uma configuração ativa por agente/role
    UNIQUE KEY unique_active_agent
(
    agent_name,
    agent_role,
    is_active
)
    );

-- Tabela de Histórico de Otimizações: Rastreia mudanças do Meta-Agent
CREATE TABLE IF NOT EXISTS optimization_history
(
    id
    INT
    AUTO_INCREMENT
    PRIMARY
    KEY,
    optimization_type
    ENUM
(
    'PROMPT_UPDATE',
    'CONFIG_UPDATE',
    'MODEL_CHANGE'
) NOT NULL,
    target_type ENUM
(
    'AGENT',
    'PROMPT'
) NOT NULL,
    target_id INT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    reason TEXT,
    performance_before DECIMAL
(
    3,
    2
),
    performance_after DECIMAL
(
    3,
    2
),
    cost_impact_usd DECIMAL
(
    10,
    4
),
    success BOOLEAN DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR
(
    100
) DEFAULT 'meta-agent',

    -- Índices para análise
    INDEX idx_optimization_type
(
    optimization_type,
    created_at
),
    INDEX idx_target_history
(
    target_type,
    target_id,
    created_at
),
    INDEX idx_performance_tracking
(
    performance_before,
    performance_after
)
    );

-- Inserir prompts padrão do sistema
INSERT INTO prompts (prompt_name, prompt_version, prompt_text, is_active, namespace, language, model_target, created_by)
VALUES ('cypher_generation', '1.0',
        'Você é um especialista em Cypher (Neo4j). Gere consultas Cypher precisas baseadas na pergunta do usuário.\n\n<INSTRUCOES>\n1. Analise a pergunta e identifique entidades e relacionamentos\n2. Gere uma consulta Cypher válida e eficiente\n3. NÃO ADICIONE nenhuma informação que não esteja diretamente presente na <INFORMACAO>\n</INSTRUCOES>\n\n<INFORMACAO>\n{context}\n</INFORMACAO>\n\n---\n<PERGUNTA>\n{question}\n</PERGUNTA>\n\nRaciocínio:\n<seu raciocínio passo a passo aqui>\n---\nConsulta Cypher:',
        TRUE, 'default', 'pt-BR', 'general', 'system'),

       ('qa_synthesis', '1.0',
        'Você é um assistente especializado em sintetizar respostas precisas baseadas em informações fornecidas.\n\n<INSTRUCOES>\n1. Leia cuidadosamente a <INFORMACAO> fornecida\n2. Responda à <PERGUNTA> usando APENAS as informações disponíveis\n3. NÃO ADICIONE nenhuma informação que não esteja diretamente presente na <INFORMACAO>\n</INSTRUCOES>\n\n<INFORMACAO>\n{context}\n</INFORMACAO>\n\n---\n<PERGUNTA>\n{question}\n</PERGUNTA>\n\nRaciocínio:\n<seu raciocínio passo a passo aqui>\n---\nResposta Útil:',
        TRUE, 'default', 'pt-BR', 'general', 'system'),

       ('react_agent', '1.0',
        'Você é um **engenheiro de software de IA altamente experiente e meticuloso**. Sua missão é resolver os desafios do usuário de forma autônoma, usando um conjunto ESTRITO de capacidades.\n\n---\n**<INSTRUCOES_CRUCIAIS_E_OBRIGATORIAS>**\n1. **SEMPRE** siga o formato de saída <FORMATO> sem desvios.\n2. Sua primeira `Thought` (Pensamento) DEVE ser analisar a consulta do usuário e identificar qual ferramenta das <CAPACIDADES> é a mais adequada.\n3. Se uma ferramenta adequada existir, sua `Action` (Ação) deve ser usar essa ferramenta.\n4. Se NENHUMA ferramenta em <CAPACIDADES> puder resolver a consulta, sua ÚNICA ação permitida é responder diretamente com `Final Answer`, informando que você não possui a capacidade necessária.\n5. Se uma `Action` resultar em um erro na `Observation`, PARE IMEDIATAMENTE e forneça uma `Final Answer` que explique o erro ao usuário.\n**</INSTRUCOES_CRUCIAIS_E_OBRIGATORIAS>**\n---\n\n<CAPACIDADES>\n{tools}\n</CAPACIDADES>\n\n---\n<FORMATO>\nThought: A consulta do usuário é [resumo da consulta]. Analisando minhas capacidades, a ferramenta mais adequada é `[nome_da_ferramenta]`.\nAction: [nome_da_ferramenta]\nAction Input: [O input da capacidade em JSON]\n\nOU, SE NENHUMA FERRAMENTA FOR ADEQUADA:\n\nThought: A consulta do usuário é [resumo da consulta]. Analisando minhas capacidades, nenhuma ferramenta é capaz de realizar esta tarefa. Devo informar ao usuário.\nFinal Answer: Eu não possuo a capacidade de [ação solicitada pelo usuário]. Minhas ferramentas disponíveis são: [lista de nomes de ferramentas].\n\n... (o ciclo de Thought/Action/Observation pode repetir após a primeira ação)\n\nThought: Eu completei a tarefa.\nFinal Answer: [A resposta final e concisa para o usuário.]\n</FORMATO>\n\n---\nInicie a tarefa.\n\n<USER_QUERY>\n{input}\n</USER_QUERY>\n\n{agent_scratchpad}\n~~\n**AVISO FINAL:** A sua resposta `Final Answer` DEVE ser, sem exceção, em Português do Brasil.',
        TRUE, 'default', 'pt-BR', 'general', 'system'),

       ('meta_agent_supervisor', '1.0',
        'Você é o Meta-Agente supervisor do sistema de IA Janus. Sua única função é monitorar a saúde e o desempenho do sistema de forma proativa, usando as ferramentas de introspecção fornecidas.\n\n**<INSTRUÇÕES>**\n1. Sua tarefa principal é analisar o histórico de operações do Janus para identificar padrões de falhas ou ineficiências.\n2. Use a ferramenta `analyze_memory_for_failures` para revisar as experiências recentes.\n3. Com base na análise, formule uma hipótese sobre a causa raiz de quaisquer problemas recorrentes.\n4. Se um padrão de falha for detectado, sua `Final Answer` deve ser um resumo conciso do problema e uma recomendação de tarefa para um agente `TOOL_USER` resolver o problema.\n5. Se nenhuma falha significativa for encontrada, sua `Final Answer` deve ser um relatório de status confirmando que o sistema está a operar normalmente.\n**</INSTRUÇÕES>\n\n<CAPACIDADES>\n{tools}\n</CAPACIDADES>\n\n---\nInicie a análise.\n\n<USER_QUERY>\n{input}\n</USER_QUERY>\n\n{agent_scratchpad}',
        TRUE, 'default', 'pt-BR', 'general', 'system');

-- Inserir configurações padrão de agentes
INSERT INTO agent_configurations (agent_name, agent_role, llm_provider, llm_model, prompt_id, max_retries,
                                  timeout_seconds, temperature, max_tokens, is_active, priority_level, cost_budget_usd,
                                  performance_threshold, created_by)
VALUES ('Orchestrator', 'ORCHESTRATOR', 'ollama', 'llama3.1:8b', (SELECT id
                                                                  FROM prompts
                                                                  WHERE prompt_name = 'react_agent'
                                                                    AND is_active = TRUE LIMIT 1), 3, 60, 0.7, 4096, TRUE, 'HIGH', 0.02, 0.8, 'system'),
('CodeGenerator', 'CODE_GENERATOR', 'ollama', 'llama3.1:8b', (SELECT id FROM prompts WHERE prompt_name = 'react_agent' AND is_active = TRUE LIMIT 1), 3, 90, 0.3, 8192, TRUE, 'HIGH', 0.05, 0.8, 'system'),
('KnowledgeCurator', 'KNOWLEDGE_CURATOR', 'ollama', 'llama3.1:8b', (SELECT id FROM prompts WHERE prompt_name = 'cypher_generation' AND is_active = TRUE LIMIT 1), 2, 45, 0.5, 2048, TRUE, 'MEDIUM', 0.01, 0.8, 'system'),
('MetaAgent', 'META_AGENT', 'ollama', 'llama3.1:8b', (SELECT id FROM prompts WHERE prompt_name = 'meta_agent_supervisor' AND is_active = TRUE LIMIT 1), 2, 180, 0.6, 4096, TRUE, 'CRITICAL', 0.03, 0.9, 'system');
