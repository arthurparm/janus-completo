import logging
from typing import Any

from app.core.tools import action_registry

logger = logging.getLogger(__name__)

class PromptBuilderService:
    """Responsável por construir os prompts completos para o LLM.

    Centraliza toda a lógica de construção de contexto, incluindo:
    - Inserção de personability listings, tool documentation).
    """

    def build_prompt(
        self,
        persona: str,
        history: list[dict[str, Any]],
        new_user_message: str,
        summary: str | None,
        relevant_memories: str | None = None,
    ) -> str:
        # Log request for debugging
        logger.info(
            "[PROMPT_BUILD] Building prompt for message: '%s...'",
            new_user_message[:100] if new_user_message else "(empty)"
        )

        lines: list[str] = []
        # Identity and tone (English by default), emphasizing first person
        lines.append(
            "System: You are Janus assistant. Always speak in first person (I) and address the user in second person (you). Avoid referring to yourself in third person or as 'Janus' or 'the assistant'. Use a polite, professional and natural tone, be direct and clear, and highlight next steps when helpful. Respond in the same language as the user; by default, in Portuguese when user speaks Portuguese."
        )

        # Identity and Privacy
        lines.append(
            "You are Janus, an advanced AI assistant created to help with programming tasks, "
            "code analysis and knowledge management. You have long-term memory and can use tools."
        )
        lines.append(
            "PRIVACY RULES (CRITICAL): When asked about yourself, NEVER disclose internal information such as:"
        )
        lines.append("- Budgets, costs or monetary values (e.g., '$50 USD', 'monthly budget')")
        lines.append("- Token prices or API costs")
        lines.append("- Specific LLM provider names (OpenAI, DeepSeek, Gemini, Ollama)")
        lines.append("- Internal configurations, environment variables or technical parameters")
        lines.append("- Infrastructure details such as container names, ports or hosts")
        lines.append(
            "If asked about these details, politely respond that they are internal system information."
        )
        lines.append(
            f"System: Current persona: {persona}. Adapt style to context while maintaining clarity and professionalism."
        )

        if relevant_memories:
            lines.append("System: FATOS RELEVANTES LEMBRADOS (Contexto de longo prazo):")
            lines.append(relevant_memories)
            lines.append("System: Use esses fatos para personalizar a resposta se apropriado.")

        # Check for tool creation keywords and log
        tool_keywords = ['tool', 'ferramenta', 'capability', 'capacidade', 'crie uma ferramenta', 'create a tool']
        script_keywords = ['script', 'file', 'arquivo', 'código', 'write a script', 'escreva um script']

        detected_tool = any(kw.lower() in new_user_message.lower() for kw in tool_keywords)
        detected_script = any(kw.lower() in new_user_message.lower() for kw in script_keywords)

        if detected_tool:
            logger.warning(
                "[INTENT_DETECTION] 🎯 TOOL keywords detected in message! Should route to AUTO-EVOLUTION"
            )
        elif detected_script:
            logger.warning(
                "[INTENT_DETECTION] 📄 SCRIPT keywords detected in message! Should use write_file"
            )
        else:
            logger.warning(
                "[INTENT_DETECTION] ❓ AMBIGUOUS - No clear TOOL or SCRIPT keywords. Should ask user."
            )

        lines.append("System: REASONING PROTOCOL (MANDATORY):")
        lines.append("")
        lines.append("0. INTENT CLASSIFICATION (CHAIN-OF-THOUGHT):")
        lines.append("   BEFORE taking ANY action, reason step-by-step about user intent:")
        lines.append("   Step 1: Identify keywords in request")
        lines.append("   Step 2: Classify intent:")
        lines.append("     • SYSTEM TOOL: 'tool', 'ferramenta', 'capability', 'capacidade' → Route to AUTO-EVOLUTION")
        lines.append("     • STANDALONE SCRIPT: 'script', 'file', 'arquivo', 'código' → Use write_file")
        lines.append("     • AMBIGUOUS: No clear keywords → ASK user for clarification FIRST")
        lines.append("   Step 3: Execute appropriate action based on classification")
        lines.append("")
        lines.append(
            "1. ANALYZE: For complex code requests, check if you need context from existing codebase."
        )
        lines.append(
            "   But CREATION tasks still require Step 0 classification to route correctly."
        )
        lines.append(
            "2. DECOMPOSE: For complex questions, break them into sub-questions. Solve each sequentially."
        )
        lines.append(
            "3. TOOL STRATEGY: Do not guess. Use 'query_knowledge_graph', 'read_file', or 'list_directory' to ground your answers."
        )
        lines.append(
            "   This applies to QUESTIONS and ANALYSIS, not to CREATION tasks."
        )
        lines.append(
            "4. VERIFY: After using a tool, verify the result makes sense before proceeding. If inconsistent, investigate."
        )
        lines.append(
            "5. ASK WHEN UNCLEAR: If user request is ambiguous (missing parameters, multiple interpretations), ASK for clarification instead of guessing."
        )
        lines.append(
            "6. SAFETY: If asked to modify code, verify existing tests first. If asked about internal system details, refuse politely."
        )
        lines.append(
            "7. CLARITY: Be concise. Avoid filler phrases like 'I understand' or 'As an AI'."
        )
        lines.append("")
        lines.append("System: WHEN TO ASK FOR CLARIFICATION:")
        lines.append("- Multiple valid interpretations exist")
        lines.append("- Missing critical parameters (file paths, IDs, specific values)")
        lines.append("- Ambiguous scope ('all files' vs 'specific module')")
        lines.append("- User intent unclear (debugging vs feature request vs documentation)")
        lines.append("- Risk of destructive action without confirmation")
        lines.append("")
        lines.append("System: ⚠️ CRITICAL DISTINCTION - SYSTEM TOOL vs STANDALONE SCRIPT:")
        lines.append("")
        lines.append("SYSTEM TOOL Request Indicators:")
        lines.append("  • Keywords: 'tool', 'ferramenta', 'capability', 'capacidade', 'habilidade', 'ability'")
        lines.append("  • Intent: User wants YOU to have a new capability")
        lines.append("  • Action: Route to auto-evolution system (NEVER use write_file)")
        lines.append("  • Response: 'I'll create this as a registered system tool using auto-evolution.'")
        lines.append("")
        lines.append("STANDALONE SCRIPT Request Indicators:")
        lines.append("  • Keywords: 'script', 'file', 'arquivo', 'código', 'program'")
        lines.append("  • Intent: User wants a file they can run")
        lines.append("  • Action: Use write_file to create in /app/workspace/")
        lines.append("  • Response: Generate code and save to file")
        lines.append("")
        lines.append("WHEN AMBIGUOUS:")
        lines.append("  • ASK: 'Do you want a SYSTEM TOOL (I can use) or STANDALONE SCRIPT (you run)?'")
        lines.append("  • DO NOT assume - wait for clarification")
        lines.append("")
        lines.append("System: FEW-SHOT EXAMPLES - Learn from these cases:")
        lines.append("")
        lines.append("Example 1 [SYSTEM TOOL]:")
        lines.append("  User: 'Create a tool to fetch ZIP code info'")
        lines.append("  CoT Reasoning:")
        lines.append("    → Keyword detected: 'tool'")
        lines.append("    → Classification: SYSTEM TOOL request")
        lines.append("    → Route to: auto-evolution")
        lines.append("  Response: 'I'll create this as a system tool using auto-evolution.'")
        lines.append("  Action: Use 'evolve_tool' with the full capability description (NEVER write_file)")
        lines.append("")
        lines.append("Example 2 [STANDALONE SCRIPT]:")
        lines.append("  User: 'Write a Python script that calculates fibonacci'")
        lines.append("  CoT Reasoning:")
        lines.append("    → Keyword detected: 'script'")
        lines.append("    → Classification: STANDALONE SCRIPT request")
        lines.append("    → Route to: write_file")
        lines.append("  Response: *generates code silently*")
        lines.append("  Action: write_file(file_path='fibonacci.py', content=<generated_code>)")
        lines.append("")
        lines.append("Example 3 [AMBIGUOUS]:")
        lines.append("  User: 'Create code to validate email'")
        lines.append("  CoT Reasoning:")
        lines.append("    → Keyword: 'code' (neutral/ambiguous)")
        lines.append("    → Classification: AMBIGUOUS - cannot determine intent")
        lines.append("    → Action required: ASK before proceeding")
        lines.append("  Response: 'Would you like a SYSTEM TOOL (I can use internally) or STANDALONE SCRIPT (file you run)?'")
        lines.append("  Action: WAIT for user clarification (do NOT guess)")

        lines.append("System: RESPONSE GUIDELINES:")
        lines.append(
            "- NO REPETITION: Do not repeat the user's question. Do not start every message with 'Understood' or 'Got it'. Be direct."
        )
        lines.append(
            "- NO FLUFF: Avoid generic intros like 'I utilize Python/LangChain...'. Answer the question specifically."
        )
        lines.append(
            "- BE HONEST: If you need to check the code to answer, say 'I'll check the code' and call the tool."
        )
        lines.append("\nSystem: TOOL USE INSTRUCTIONS:")
        lines.append(
            "You have access to a set of tools to interact with the system. To use a tool, you MUST output a valid XML block like this:"
        )
        lines.append("<tool_use>")
        lines.append("    <name>tool_name</name>")
        lines.append('    <args>{"arg1": "value1"}</args>')
        lines.append("</tool_use>")
        lines.append("The 'args' field must be a valid JSON string representing the arguments.")
        lines.append(
            "After you output a tool call, the system will execute it and provide the result in the next message."
        )
        lines.append("")
        lines.append("TOOL COMPOSITION STRATEGIES:")
        lines.append("1. Sequential: Use output of Tool A as input to Tool B")
        lines.append("   Example: list_directory -> read_file -> analyze code")
        lines.append("2. Validation: Verify results before proceeding")
        lines.append("   Example: query_knowledge_graph -> verify data -> answer user")
        lines.append("3. Fallback: If primary tool fails, try alternative")
        lines.append("   Example: query_kg fails -> read_file directly -> manual search")
        lines.append ("")
        lines.append("AVAILABLE TOOLS:")

        try:
            tools = action_registry.list_tools()
            target_tools = [
                "execute_shell",
                "read_file",
                "write_file",
                "list_directory",
                "query_knowledge_graph",
                "find_related_concepts",
                "evolve_tool",
            ]
            for t in tools:
                if t.name in target_tools:
                    desc = (t.description or "").split("\n")[0]
                    lines.append(f"- {t.name}: {desc}")
        except Exception:
            lines.append("(Failed to list tools)")

        lines.append(
            "\nUse tools only when necessary. If you don't need a tool, just respond naturally."
        )
        lines.append("BEST PRACTICES:")
        lines.append("- For QUESTIONS about code: Use knowledge_graph or read_file to ground your answers")
        lines.append("- For CREATION tasks (write/generate code): Generate directly using your training. No research needed.")
        lines.append("- For DEBUGGING: Use tools to investigate errors and inspect state")
        lines.append("- For CONSISTENCY: Only if user asks 'create X following pattern of Y', then inspect Y first")
        lines.append("- Combine tools when single tool insufficient for ANALYSIS tasks")
        lines.append("- If tool fails, explain to user and try alternative approach")
        lines.append("")
        lines.append("IMPORTANT CONTEXT (Self-Awareness):")
        lines.append("- You are running inside a Docker container named 'janus_api'.")
        lines.append(
            "- You have access to the Docker CLI. You can inspect, restart, and view logs of all containers."
        )
        lines.append(
            "- To see your own logs: execute_system_command with 'docker logs janus_api --tail 100'"
        )
        lines.append("- To see all containers: execute_system_command with 'docker ps -a'")
        lines.append(
            "- Your code is mounted at /app/app. You can read and modify your own source code."
        )
        lines.append("- Use code inspection for DEBUGGING and ERROR ANALYSIS, not for CREATING new features.")
        lines.append("- When asked to CREATE something new, use your training knowledge directly. Do not grep/read existing code as a template.")
        lines.append("- Use this power responsibly to debug issues, learn from errors, and evolve.")
        lines.append("----------------------------\n")

        if summary:
            lines.append(f"System: PREVIOUS CONTEXT SUMMARY:\n{summary}")

        if history:
            lines.append("\nSystem: CURRENT CONVERSATION HISTORY:")
            for m in history:
                r = m.get("role", "user")
                t = m.get("text", "")
                if r == "assistant":
                    lines.append(f"Assistant: {t}")
                else:
                    lines.append(f"User: {t}")

        lines.append("\nSystem: NEW USER MESSAGE:")
        lines.append(f"User: {new_user_message}")
        lines.append("Assistant:")
        return "\n".join(lines)

    def is_capabilities_query(self, text: str) -> bool:
        try:
            t = (text or "").lower()
            keywords = [
                "quais funcionalidades",
                "funcionalidades",
                "ferramentas disponíveis",
                "listar ferramentas",
                "o que você pode fazer",
                "capacidades",
                "habilidades",
                "comandos disponíveis",
                "ferramentas locais",
                "minhas ferramentas",
                "capabilities",
                "what can you do",
                "tools available",
                "list tools",
                "available tools",
                "skills",
                "features",
            ]
            return any(k in t for k in keywords)
        except Exception:
            return False

    def is_discovery_query(self, text: str) -> bool:
        try:
            t = (text or "").lower()
            keywords = [
                "coletar informações",
                "coleta de informações",
                "coletar dados",
                "questionário",
                "wizard",
                "configurar ferramentas",
                "configurar ambiente",
                "descoberta de ferramentas",
                "levantamento",
                "diagnóstico de ferramentas",
                "mapear ferramentas",
                "plano dinâmico",
                "collect information",
                "information gathering",
                "collect data",
                "questionnaire",
                "setup",
                "configure tools",
                "tool discovery",
                "diagnostic",
                "survey",
            ]
            return any(k in t for k in keywords)
        except Exception:
            return False

    def is_docs_query(self, text: str) -> bool:
        try:
            t = (text or "").lower()
            keywords = [
                "gerar documentação",
                "documentação de ferramentas",
                "explicar ferramentas",
                "texto explicativo",
                "documentar as ferramentas",
                "criar documentação",
                "documentação automática",
                "detalhar ferramentas",
                "tool docs",
                "generate docs",
                "tools documentation",
            ]
            return any(k in t for k in keywords)
        except Exception:
            return False

    def render_local_capabilities(self, tool_service: Any | None) -> str:
        # Fallback se o serviço de ferramentas não está disponível
        if not tool_service:
            return (
                "Capacidades locais: serviço de ferramentas não disponível. "
                "Use /web/overview para consultar status do sistema."
            )

        try:
            metas = tool_service.list_tools(category=None, permission_level=None, tags=None)
            stats = tool_service.get_statistics()
        except Exception:
            metas = []
            stats = {}

        if not metas:
            return (
                "Nenhuma ferramenta registrada no momento. "
                "Você pode criar ferramentas dinâmicas via Action Module (Sprint 6)."
            )

        # Agrupa por categoria
        grouped: dict[str, list[str]] = {}
        for m in metas:
            cat = getattr(m.category, "value", str(m.category))
            perm = getattr(m.permission_level, "value", str(m.permission_level))
            grouped.setdefault(cat, []).append(f"{m.name} ({perm})")

        lines: list[str] = []
        lines.append("Capacidades locais detectadas dinamicamente:")
        lines.append(f"- Ferramentas registradas: {len(metas)}")
        if stats:
            total_calls = stats.get("total_calls")
            success_rate = stats.get("success_rate")
            if total_calls is not None and success_rate is not None:
                lines.append(
                    f"- Uso recente: {total_calls} chamadas, taxa de sucesso {success_rate}"
                )

        for cat, items in sorted(grouped.items(), key=lambda x: x[0]):
            lines.append(f"- Categoria '{cat}': {', '.join(sorted(items))}")

        lines.append(
            "\nDica: pergunte 'executar diagnóstico de ferramentas' para um fluxo guiado de verificação."
        )
        return "\n".join(lines)

    def render_tools_documentation(self, tool_service: Any | None) -> str:
        # Fallback se o serviço de ferramentas não está disponível
        if not tool_service:
            return (
                "Não consigo gerar documentação local porque o serviço de ferramentas não está disponível. "
                "Verifique o estado do ToolService."
            )

        try:
            return tool_service.generate_documentation(include_stats=True, format="markdown")
        except Exception as e:
            # logger.error("Falha ao gerar documentação de ferramentas", exc_info=e)
            return (
                f"Ocorreu um erro ao gerar a documentação das ferramentas locais: {e}. "
                "Tente novamente mais tarde."
            )

    def render_discovery_intro(self, tool_service: Any | None) -> str:
        # Usa estado atual para montar um plano adaptativo
        metas: list[Any] = []
        stats: dict[str, Any] = {}
        if tool_service:
            try:
                metas = tool_service.list_tools(category=None, permission_level=None, tags=None)
                stats = tool_service.get_statistics()
            except Exception:
                pass

        categorias = (
            sorted({getattr(m.category, "value", str(m.category)) for m in metas}) if metas else []
        )
        pontos = [
            "1) Seleção de categorias relevantes (filesystem, system, web, computation, database)",
            "2) Nível de permissão desejado (read_only, safe, write, dangerous)",
            "3) Rate limit por minuto (ex.: 10, 30, 60)",
            "4) Preferência de confirmação antes de executar (sim/não)",
            "5) Ferramentas prioritárias para uso frequente",
            "6) Execução de diagnóstico rápido para validar acesso (get_system_info, list_directory, execute_python_expression)",
        ]

        lines: list[str] = []
        lines.append("Plano dinâmico de coleta e validação de ferramentas locais:")
        if categorias:
            lines.append(f"- Categorias detectadas agora: {', '.join(categorias)}")
        if stats:
            lines.append(
                f"- Registro atual: {stats.get('total_tools_registered', 0)} ferramentas, "
                f"{stats.get('total_calls', 0)} chamadas recentes"
            )

        lines.append("\nFluxo interativo:")
        for p in pontos:
            lines.append(f"- {p}")

        lines.append(
            "\nComo responder: envie algo como 'Categorias: filesystem, system; Permissões: safe; "
            "Rate limit: 30; Confirmar: sim; Prioridades: read_file, search_web; Iniciar diagnóstico'."
        )
        lines.append(
            "Eu vou adaptar as próximas perguntas com base nas suas respostas e no que estiver "
            "efetivamente disponível localmente."
        )
        return "\n".join(lines)

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate the number of tokens in a text string.
        Uses a simple heuristic (char count / 4) for efficiency.
        """
        if not text:
            return 0
        return len(text) // 4

