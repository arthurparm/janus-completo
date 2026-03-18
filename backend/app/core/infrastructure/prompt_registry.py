"""
Prompt Registry - Mapeamento programatico de cada prompt para seu subsistema Janus.

Cada prompt pertence a exatamente um subsistema (ponta) do Janus.
O registro serve como fonte canonica para descobrir qual parte do sistema
um prompt alimenta e quais prompts cada subsistema consome.
"""

from dataclasses import dataclass, field
from enum import Enum


class JanusSubsystem(str, Enum):
    """Subsistemas (pontas) do Janus que consomem prompts."""

    IDENTITY = "identity"
    AGENTS = "agents"
    AUTONOMY = "autonomy"
    CAPABILITIES = "capabilities"
    CONTEXT = "context"
    META_AGENT = "meta_agent"
    REFLEXION = "reflexion"
    KNOWLEDGE = "knowledge"
    RAG = "rag"
    TASKS = "tasks"
    TOOLS = "tools"
    SECURITY = "security"
    DEBATE = "debate"
    WORKERS = "workers"
    TRAINING = "training"
    REASONING = "reasoning"
    UI = "ui"


@dataclass(frozen=True)
class PromptEntry:
    """Registro de um prompt com seu subsistema e descricao."""

    name: str
    subsystem: JanusSubsystem
    description: str
    consumers: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Registro completo: cada prompt .txt -> subsistema Janus
# ---------------------------------------------------------------------------

PROMPT_REGISTRY: tuple[PromptEntry, ...] = (
    # ── Identity ──────────────────────────────────────────────────────────
    PromptEntry(
        name="system_identity",
        subsystem=JanusSubsystem.IDENTITY,
        description="Personalidade base e diretrizes comportamentais do sistema",
        consumers=("SystemIdentityModule", "PromptComposer"),
    ),
    PromptEntry(
        name="system_identity_enforcement",
        subsystem=JanusSubsystem.IDENTITY,
        description="Regras de identidade e limites operacionais",
        consumers=("SystemIdentityModule",),
    ),
    PromptEntry(
        name="janus_identity_jarvis",
        subsystem=JanusSubsystem.IDENTITY,
        description="Persona inspirada em JARVIS (tom elegante, parceiro confiavel)",
        consumers=("SystemIdentityModule",),
    ),
    # ── Agents ────────────────────────────────────────────────────────────
    PromptEntry(
        name="agent_coder",
        subsystem=JanusSubsystem.AGENTS,
        description="Agente especializado em codigo: producao, refatoracao, debug",
        consumers=("SpecializedAgent",),
    ),
    PromptEntry(
        name="agent_documenter",
        subsystem=JanusSubsystem.AGENTS,
        description="Agente especializado em documentacao de APIs e codigo",
        consumers=("SpecializedAgent",),
    ),
    PromptEntry(
        name="agent_optimizer",
        subsystem=JanusSubsystem.AGENTS,
        description="Agente especializado em performance e otimizacao",
        consumers=("SpecializedAgent",),
    ),
    PromptEntry(
        name="agent_project_manager",
        subsystem=JanusSubsystem.AGENTS,
        description="Agente coordenador de tarefas e progresso",
        consumers=("SpecializedAgent",),
    ),
    PromptEntry(
        name="agent_researcher",
        subsystem=JanusSubsystem.AGENTS,
        description="Agente de pesquisa e investigacao baseada em evidencias",
        consumers=("SpecializedAgent",),
    ),
    PromptEntry(
        name="agent_self_optimization",
        subsystem=JanusSubsystem.AGENTS,
        description="Agente de auto-melhoria do sistema (safety-critical)",
        consumers=("SpecializedAgent",),
    ),
    PromptEntry(
        name="agent_sysadmin",
        subsystem=JanusSubsystem.AGENTS,
        description="Agente DevOps/infraestrutura: deploy, configuracao",
        consumers=("SpecializedAgent",),
    ),
    PromptEntry(
        name="agent_tester",
        subsystem=JanusSubsystem.AGENTS,
        description="Agente QA: validacao, edge cases, testes de regressao",
        consumers=("SpecializedAgent",),
    ),
    PromptEntry(
        name="agent_thinker",
        subsystem=JanusSubsystem.AGENTS,
        description="Agente arquiteto: design tecnico e planejamento conceitual",
        consumers=("SpecializedAgent", "ThinkerAgentWorker"),
    ),
    # ── Autonomy ──────────────────────────────────────────────────────────
    PromptEntry(
        name="autonomy_plan_draft",
        subsystem=JanusSubsystem.AUTONOMY,
        description="Gera planos de execucao autonoma (Goal -> JSON plan)",
        consumers=("AutonomyPlanner",),
    ),
    PromptEntry(
        name="autonomy_plan_critique",
        subsystem=JanusSubsystem.AUTONOMY,
        description="Valida qualidade de planos (Plan -> JSON critique scores)",
        consumers=("AutonomyPlanner",),
    ),
    PromptEntry(
        name="autonomy_plan_refine",
        subsystem=JanusSubsystem.AUTONOMY,
        description="Refina planos com base em criticas (Critique -> refined plan)",
        consumers=("AutonomyPlanner",),
    ),
    PromptEntry(
        name="autonomy_replanner",
        subsystem=JanusSubsystem.AUTONOMY,
        description="Recupera de falhas na execucao autonoma",
        consumers=("AutonomyPlanner",),
    ),
    PromptEntry(
        name="autonomy_verifier",
        subsystem=JanusSubsystem.AUTONOMY,
        description="Valida sucesso de cada passo da execucao",
        consumers=("AutonomyPlanner",),
    ),
    PromptEntry(
        name="autonomy_reasoning_assistant",
        subsystem=JanusSubsystem.AUTONOMY,
        description="Raciocinio complexo para analise durante autonomia",
        consumers=("AutonomyPlanner",),
    ),
    # ── Capabilities ──────────────────────────────────────────────────────
    PromptEntry(
        name="capability_chain_of_thought",
        subsystem=JanusSubsystem.CAPABILITIES,
        description="Raciocinio estruturado: decomposicao passo-a-passo",
        consumers=("ReasoningProtocolModule", "AdvancedPrompts"),
    ),
    PromptEntry(
        name="capability_code_review",
        subsystem=JanusSubsystem.CAPABILITIES,
        description="Avaliacao de qualidade de codigo: seguranca, performance",
        consumers=("ReasoningProtocolModule", "AdvancedPrompts"),
    ),
    PromptEntry(
        name="capability_hypothesis_debugging",
        subsystem=JanusSubsystem.CAPABILITIES,
        description="Debugging cientifico: analise de causa raiz por hipoteses",
        consumers=("ReasoningProtocolModule", "AdvancedPrompts"),
    ),
    PromptEntry(
        name="capability_multi_agent_coordination",
        subsystem=JanusSubsystem.CAPABILITIES,
        description="Orquestracao de tarefas entre multiplos agentes",
        consumers=("AdvancedPrompts",),
    ),
    PromptEntry(
        name="capability_self_correction",
        subsystem=JanusSubsystem.CAPABILITIES,
        description="Deteccao e correcao de erros proprios",
        consumers=("AdvancedPrompts",),
    ),
    # ── Context ───────────────────────────────────────────────────────────
    PromptEntry(
        name="context_compression",
        subsystem=JanusSubsystem.CONTEXT,
        description="Compressao inteligente de conversas longas",
        consumers=("ContextCompressionModule", "JanusSpecializedPrompts"),
    ),
    PromptEntry(
        name="context_compressed_conversation_section",
        subsystem=JanusSubsystem.CONTEXT,
        description="Template somente-leitura para historico comprimido",
        consumers=("ContextCompressionModule",),
    ),
    PromptEntry(
        name="context_recent_conversation_section",
        subsystem=JanusSubsystem.CONTEXT,
        description="Template somente-leitura para mensagens recentes",
        consumers=("ContextCompressionModule",),
    ),
    PromptEntry(
        name="context_memories_section",
        subsystem=JanusSubsystem.CONTEXT,
        description="Template somente-leitura para fatos persistidos",
        consumers=("ContextCompressionModule",),
    ),
    PromptEntry(
        name="context_summary_section",
        subsystem=JanusSubsystem.CONTEXT,
        description="Template somente-leitura para resumo de alto nivel",
        consumers=("ContextCompressionModule",),
    ),
    PromptEntry(
        name="specialized_context_compression",
        subsystem=JanusSubsystem.CONTEXT,
        description="Estrategia alternativa de compressao de contexto",
        consumers=("ContextCompressionModule",),
    ),
    # ── Meta-Agent ────────────────────────────────────────────────────────
    PromptEntry(
        name="meta_agent",
        subsystem=JanusSubsystem.META_AGENT,
        description="Monitoramento geral de saude do sistema (ReAct + JSON)",
        consumers=("MetaAgent", "MetaAgentCycle"),
    ),
    PromptEntry(
        name="meta_agent_act_template",
        subsystem=JanusSubsystem.META_AGENT,
        description="Analise estrategica de licoes aprendidas",
        consumers=("MetaAgentCycle",),
    ),
    PromptEntry(
        name="meta_agent_diagnosis",
        subsystem=JanusSubsystem.META_AGENT,
        description="Identificacao de causa raiz com severidade",
        consumers=("MetaAgentCycle",),
    ),
    PromptEntry(
        name="meta_agent_plan_template",
        subsystem=JanusSubsystem.META_AGENT,
        description="Template de planejamento de investigacao",
        consumers=("MetaAgentCycle",),
    ),
    PromptEntry(
        name="meta_agent_planning",
        subsystem=JanusSubsystem.META_AGENT,
        description="Transforma diagnosticos em planos de acao (JSON)",
        consumers=("MetaAgentCycle",),
    ),
    PromptEntry(
        name="meta_agent_reflection",
        subsystem=JanusSubsystem.META_AGENT,
        description="Revisao de planos de remediacao para seguranca",
        consumers=("MetaAgentCycle",),
    ),
    # ── Reflexion ─────────────────────────────────────────────────────────
    PromptEntry(
        name="reflexion_execution",
        subsystem=JanusSubsystem.REFLEXION,
        description="Diagnostico de falhas de execucao -> plano de correcao",
        consumers=("ReflexionWorker",),
    ),
    PromptEntry(
        name="reflexion_evaluate",
        subsystem=JanusSubsystem.REFLEXION,
        description="Pontuacao de qualidade do resultado (0-1)",
        consumers=("ReflexionWorker",),
    ),
    PromptEntry(
        name="reflexion_analysis",
        subsystem=JanusSubsystem.REFLEXION,
        description="Analise de padroes de erro em markdown",
        consumers=("ReflexionWorker",),
    ),
    PromptEntry(
        name="reflexion_refine",
        subsystem=JanusSubsystem.REFLEXION,
        description="Melhoria iterativa de tentativas anteriores",
        consumers=("ReflexionWorker",),
    ),
    # ── Knowledge ─────────────────────────────────────────────────────────
    PromptEntry(
        name="knowledge_extraction",
        subsystem=JanusSubsystem.KNOWLEDGE,
        description="Extracao de entidades/relacoes estruturadas de experiencias",
        consumers=("KnowledgeService", "KnowledgeExtractionService"),
    ),
    PromptEntry(
        name="knowledge_extraction_system",
        subsystem=JanusSubsystem.KNOWLEDGE,
        description="Extracao de alta precisao de texto + metadados",
        consumers=("KnowledgeExtractionService",),
    ),
    PromptEntry(
        name="knowledge_wisdom_extraction",
        subsystem=JanusSubsystem.KNOWLEDGE,
        description="Extracao de sabedoria e padroes (fatos, licoes, conceitos)",
        consumers=("KnowledgeExtractionService",),
    ),
    PromptEntry(
        name="memory_integration",
        subsystem=JanusSubsystem.KNOWLEDGE,
        description="Integra experiencias novas no knowledge graph (JSON ops)",
        consumers=("JanusSpecializedPrompts", "MemoryService"),
    ),
    PromptEntry(
        name="memory_rating",
        subsystem=JanusSubsystem.KNOWLEDGE,
        description="Pontuacao de importancia de memorias (1-10)",
        consumers=("MemoryService",),
    ),
    PromptEntry(
        name="specialized_memory_integration",
        subsystem=JanusSubsystem.KNOWLEDGE,
        description="Integra memorias recuperadas em respostas naturais",
        consumers=("MemoryService",),
    ),
    # ── RAG ───────────────────────────────────────────────────────────────
    PromptEntry(
        name="graph_query_planning",
        subsystem=JanusSubsystem.RAG,
        description="Traduz perguntas para Cypher com otimizacao",
        consumers=("JanusSpecializedPrompts", "GraphRAGCore"),
    ),
    PromptEntry(
        name="graph_rag_synthesis",
        subsystem=JanusSubsystem.RAG,
        description="Sintetiza respostas a partir de contexto do grafo",
        consumers=("GraphRAGCore",),
    ),
    PromptEntry(
        name="specialized_graph_query_planning",
        subsystem=JanusSubsystem.RAG,
        description="Planejamento detalhado de queries ao grafo",
        consumers=("GraphRAGCore",),
    ),
    PromptEntry(
        name="cypher_generation",
        subsystem=JanusSubsystem.RAG,
        description="Geracao direta de codigo Cypher",
        consumers=("GraphRAGCore",),
    ),
    PromptEntry(
        name="hyde_generation",
        subsystem=JanusSubsystem.RAG,
        description="Geracao de documentos hipoteticos para busca semantica (HyDE)",
        consumers=("RAGService", "ReasoningRAGService"),
    ),
    PromptEntry(
        name="qa_synthesis",
        subsystem=JanusSubsystem.RAG,
        description="Sintetiza respostas de QA do grafo de conhecimento",
        consumers=("GraphRAGCore",),
    ),
    PromptEntry(
        name="rerank",
        subsystem=JanusSubsystem.RAG,
        description="Re-ranqueia chunks recuperados por relevancia",
        consumers=("SemanticRerankerService",),
    ),
    PromptEntry(
        name="rag_conversation_summary",
        subsystem=JanusSubsystem.RAG,
        description="Sumarizacao de conversas para contexto RAG",
        consumers=("RAGService",),
    ),
    # ── Tasks ─────────────────────────────────────────────────────────────
    PromptEntry(
        name="task_code_review_protocol",
        subsystem=JanusSubsystem.TASKS,
        description="Protocolo: Ler -> Focar -> Citar -> Corrigir",
        consumers=("TaskSpecificModule",),
    ),
    PromptEntry(
        name="task_debugging_protocol",
        subsystem=JanusSubsystem.TASKS,
        description="Protocolo: Entender -> Investigar -> Hipotese -> Testar -> Corrigir",
        consumers=("TaskSpecificModule",),
    ),
    PromptEntry(
        name="task_decomposition",
        subsystem=JanusSubsystem.TASKS,
        description="Decomposicao estruturada de tarefas em JSON",
        consumers=("TaskSpecificModule", "TaskService"),
    ),
    PromptEntry(
        name="task_question_protocol",
        subsystem=JanusSubsystem.TASKS,
        description="Protocolo: basear em fontes, ser direto",
        consumers=("TaskSpecificModule",),
    ),
    PromptEntry(
        name="task_script_generation_protocol",
        subsystem=JanusSubsystem.TASKS,
        description="Protocolo: confirmar deps, escrever, explicar",
        consumers=("TaskSpecificModule",),
    ),
    PromptEntry(
        name="task_tool_creation_protocol",
        subsystem=JanusSubsystem.TASKS,
        description="Protocolo: usar fluxo de criacao, descricao completa",
        consumers=("TaskSpecificModule",),
    ),
    PromptEntry(
        name="multi_agent_decomposition",
        subsystem=JanusSubsystem.TASKS,
        description="Decomposicao de projetos em tarefas com agentes (JSON array)",
        consumers=("MultiAgentSystem", "GraphOrchestrator"),
    ),
    # ── Tools ─────────────────────────────────────────────────────────────
    PromptEntry(
        name="tool_specification",
        subsystem=JanusSubsystem.TOOLS,
        description="Design de ferramentas: JSON spec (nome, args, safety level)",
        consumers=("EvolutionManager",),
    ),
    PromptEntry(
        name="tool_generation",
        subsystem=JanusSubsystem.TOOLS,
        description="Implementacao de ferramentas em Python com @tool",
        consumers=("EvolutionManager",),
    ),
    PromptEntry(
        name="tool_validation",
        subsystem=JanusSubsystem.TOOLS,
        description="Revisao de seguranca, complexidade e qualidade de tools",
        consumers=("EvolutionManager",),
    ),
    PromptEntry(
        name="tool_documentation",
        subsystem=JanusSubsystem.TOOLS,
        description="Documentacao de uso de ferramentas para o LLM",
        consumers=("ToolDocumentationModule",),
    ),
    PromptEntry(
        name="evolution_tool_specification",
        subsystem=JanusSubsystem.TOOLS,
        description="Especificacao de ferramentas para evolucao do sistema",
        consumers=("ReasoningProtocolModule",),
    ),
    PromptEntry(
        name="evolution_tool_generation",
        subsystem=JanusSubsystem.TOOLS,
        description="Geracao de codigo para evolucao de ferramentas",
        consumers=("EvolutionManager",),
    ),
    # ── Security ──────────────────────────────────────────────────────────
    PromptEntry(
        name="security_red_team",
        subsystem=JanusSubsystem.SECURITY,
        description="Auditoria adversarial com mentalidade de pentester",
        consumers=("RedTeamAgentWorker",),
    ),
    PromptEntry(
        name="security_red_team_audit",
        subsystem=JanusSubsystem.SECURITY,
        description="Busca de vulnerabilidades com scoring de severidade",
        consumers=("RedTeamAgentWorker",),
    ),
    PromptEntry(
        name="professor_code_review",
        subsystem=JanusSubsystem.SECURITY,
        description="Revisao senior: APPROVED/REJECTED + score",
        consumers=("ProfessorAgentWorker",),
    ),
    # ── Debate ────────────────────────────────────────────────────────────
    PromptEntry(
        name="debate_proponent_prompt",
        subsystem=JanusSubsystem.DEBATE,
        description="Proponente no debate: gera codigo Python robusto",
        consumers=("DebateProponentWorker",),
    ),
    PromptEntry(
        name="debate_critic_prompt",
        subsystem=JanusSubsystem.DEBATE,
        description="Critico no debate: audita seguranca e edge cases",
        consumers=("DebateCriticWorker",),
    ),
    # ── Workers ───────────────────────────────────────────────────────────
    PromptEntry(
        name="leaf_worker_assistant",
        subsystem=JanusSubsystem.WORKERS,
        description="Worker generico de assistencia",
        consumers=("LeafWorker",),
    ),
    PromptEntry(
        name="leaf_worker_coder",
        subsystem=JanusSubsystem.WORKERS,
        description="Worker de assistencia em engenharia",
        consumers=("LeafWorker",),
    ),
    PromptEntry(
        name="leaf_worker_sysadmin",
        subsystem=JanusSubsystem.WORKERS,
        description="Worker de assistencia em infraestrutura",
        consumers=("LeafWorker",),
    ),
    PromptEntry(
        name="code_agent_task",
        subsystem=JanusSubsystem.WORKERS,
        description="Template de tarefa de implementacao de codigo",
        consumers=("CodeAgentWorker",),
    ),
    PromptEntry(
        name="react_agent",
        subsystem=JanusSubsystem.WORKERS,
        description="Template generico de agente ReAct",
        consumers=("LeafWorker", "SpecializedAgent"),
    ),
    # ── Training ──────────────────────────────────────────────────────────
    PromptEntry(
        name="training_action_success_prompt",
        subsystem=JanusSubsystem.TRAINING,
        description="Documentacao de resultados de acoes bem-sucedidas",
        consumers=("NeuralTrainingSystem",),
    ),
    PromptEntry(
        name="training_lessons_learned_prompt",
        subsystem=JanusSubsystem.TRAINING,
        description="Extracao de licoes generalizaveis de experiencias",
        consumers=("NeuralTrainingSystem",),
    ),
    PromptEntry(
        name="training_metadata_context_prompt",
        subsystem=JanusSubsystem.TRAINING,
        description="Uso de metadados para gerar amostras de treinamento",
        consumers=("NeuralTrainingSystem",),
    ),
    # ── Reasoning ─────────────────────────────────────────────────────────
    PromptEntry(
        name="error_recovery",
        subsystem=JanusSubsystem.REASONING,
        description="Recuperacao inteligente de erros com prevencao",
        consumers=("JanusSpecializedPrompts", "FallbackChain"),
    ),
    PromptEntry(
        name="specialized_error_recovery",
        subsystem=JanusSubsystem.REASONING,
        description="Recuperacao de erros especificos de ferramentas",
        consumers=("FallbackChain",),
    ),
    PromptEntry(
        name="reasoning_session",
        subsystem=JanusSubsystem.REASONING,
        description="Sessao de raciocinio ReAct com tool calls",
        consumers=("ReasoningCore",),
    ),
    # ── UI ────────────────────────────────────────────────────────────────
    PromptEntry(
        name="generative_ui",
        subsystem=JanusSubsystem.UI,
        description="Renderizacao opcional de tabelas e blocos de UI",
        consumers=("GenerativeUIModule",),
    ),
    PromptEntry(
        name="semantic_commit",
        subsystem=JanusSubsystem.UI,
        description="Geracao de mensagens de commit semantico",
        consumers=("SemanticCommitService",),
    ),
)


# ---------------------------------------------------------------------------
# Helpers de consulta
# ---------------------------------------------------------------------------


def get_prompts_by_subsystem(subsystem: JanusSubsystem) -> list[PromptEntry]:
    """Retorna todos os prompts de um subsistema."""
    return [p for p in PROMPT_REGISTRY if p.subsystem == subsystem]


def get_prompt_entry(name: str) -> PromptEntry | None:
    """Busca o registro de um prompt pelo nome."""
    for p in PROMPT_REGISTRY:
        if p.name == name:
            return p
    return None


def get_subsystem_for_prompt(name: str) -> JanusSubsystem | None:
    """Retorna o subsistema ao qual um prompt pertence."""
    entry = get_prompt_entry(name)
    return entry.subsystem if entry else None


def get_subsystem_summary() -> dict[str, int]:
    """Retorna contagem de prompts por subsistema."""
    counts: dict[str, int] = {}
    for p in PROMPT_REGISTRY:
        key = p.subsystem.value
        counts[key] = counts.get(key, 0) + 1
    return counts
