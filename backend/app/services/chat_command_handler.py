"""
Chat Command Handler Service.
Handles quick commands like /help, /status, /memory, /tools.
Extracted from ChatService to reduce complexity.

Commands whose content is factual/computed keep deterministic logic; the final
wording sent to the user is generated live (preferring the OmniRoute provider)
so responses never repeat a fixed template. If no LLM service is wired, or the
generation call fails end-to-end, each command falls back to a static,
fact-accurate string so the user is never left without a response.
"""

from typing import Any

import structlog

from app.core.llm import ModelPriority, ModelRole

logger = structlog.get_logger(__name__)


class ChatCommandHandler:
    """
    Processes quick commands (starting with /) for chat service.

    Commands:
    - /help: Show available commands
    - /status: System status
    - /memory: Memory stats
    - /tools: Available tools
    - /feedback: Provide feedback
    - /about: About Janus
    """

    COMMANDS = {
        "/help": "_handle_help",
        "/status": "_handle_status",
        "/memory": "_handle_memory",
        "/tools": "_handle_tools",
        "/feedback": "_handle_feedback",
        "/about": "_handle_about",
    }

    def __init__(
        self,
        tool_service: Any | None = None,
        memory_service: Any | None = None,
        llm_service: Any | None = None,
    ):
        """
        Initialize command handler.

        Args:
            tool_service: Optional tool service for /tools command
            memory_service: Optional memory service for /memory command
            llm_service: Optional LLM service used to phrase responses naturally
        """
        self.tool_service = tool_service
        self.memory_service = memory_service
        self.llm_service = llm_service

    def is_command(self, text: str) -> bool:
        """Check if message is a quick command."""
        if not text:
            return False
        text_lower = text.strip().lower()
        return any(text_lower.startswith(cmd) for cmd in self.COMMANDS.keys())

    async def handle_command(
        self, text: str, conversation_id: str, user_id: str | None = None
    ) -> str | None:
        """
        Process command and return response.

        Args:
            text: Command text
            conversation_id: Current conversation ID
            user_id: Optional user ID

        Returns:
            Response text or None if not a command
        """
        if not self.is_command(text):
            return None

        text_lower = text.strip().lower()
        parts = text_lower.split(maxsplit=1)
        command = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        handler_name = self.COMMANDS.get(command)
        if not handler_name:
            return None

        handler = getattr(self, handler_name, None)
        if not handler:
            logger.warning("log_warning", message=f"Command handler '{handler_name}' not found")
            return None

        try:
            return await handler(args, conversation_id, user_id)
        except Exception as e:
            logger.error(
                "command_handler_error",
                command=command,
                error=str(e),
                conversation_id=conversation_id,
            )
            return f"❌ Erro ao processar comando: {e}"

    async def _respond_naturally(
        self,
        *,
        facts: str,
        instruction: str,
        conversation_id: str,
        user_id: str | None,
        fallback: str,
    ) -> str:
        """
        Phrase a response grounded in `facts`, preferring the OmniRoute provider.

        This is the "responder" layer only: it never invents facts, it just
        phrases the ones it's given. `facts` must already be computed from real
        state before calling this. Falls back to `fallback` (a static,
        fact-accurate string) when no LLM service is wired or generation fails,
        so a command always returns something instead of raising.
        """
        if not self.llm_service:
            return fallback

        prompt = (
            f"{instruction}\n\n"
            "Fatos reais (use exatamente estes; nao invente nem altere numeros ou fatos "
            f"que nao estejam listados aqui):\n{facts}\n\n"
            "Responda em portugues do Brasil, tom natural e caloroso, sem repetir um "
            "formato de template fixo a cada vez."
        )
        try:
            result = await self.llm_service.invoke_llm(
                prompt=prompt,
                role=ModelRole.ORCHESTRATOR,
                priority=ModelPriority.FAST_AND_CHEAP,
                timeout_seconds=12,
                policy_overrides={
                    "provider": "omniroute",
                    "role": "orchestrator",
                    "priority": "fast_and_cheap",
                },
                user_id=user_id,
                objective_id=conversation_id,
            )
            response = str((result or {}).get("response") or "").strip()
            return response or fallback
        except Exception as e:
            logger.warning(
                "command_natural_response_failed",
                error=str(e),
                conversation_id=conversation_id,
            )
            return fallback

    async def _handle_help(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Show available commands. Reference text, kept static by design."""
        return """📚 **Comandos Disponíveis**

`/help` - Mostra esta mensagem
`/status` - Status do sistema
`/memory` - Estatísticas de memória
`/tools` - Lista de ferramentas disponíveis
`/feedback [mensagem]` - Enviar feedback
`/about` - Sobre o Janus

Digite qualquer comando para mais detalhes!"""

    async def _handle_status(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Show real system status (LLM router health, memory/tools reachability, uptime)."""
        from app.core.monitoring.health_monitor import check_llm_router_health
        from app.services.system_status_service import system_status_service

        sys_status = system_status_service.get_system_status()

        try:
            llm_health = await check_llm_router_health()
        except Exception as e:
            llm_health = {"status": "unknown", "message": f"falha ao verificar: {e}"}

        memory_ok = self.memory_service is not None
        memory_detail = "não configurado"
        if self.memory_service:
            try:
                await self.memory_service.get_stats(user_id=user_id)
                memory_detail = "operacional"
            except Exception as e:
                memory_ok = False
                memory_detail = f"com falha ({e})"

        tools_ok = self.tool_service is not None
        tools_detail = "não configurado"
        if self.tool_service:
            try:
                tools = await self.tool_service.list_tools()
                tools_detail = f"{len(tools)} disponíveis"
            except Exception as e:
                tools_ok = False
                tools_detail = f"com falha ({e})"

        overall_ok = llm_health.get("status") == "healthy" and memory_ok and tools_ok
        status_word = "Online" if overall_ok else "Degradado"
        status_icon = "✅" if overall_ok else "⚠️"

        fallback = (
            "⚡ **Status do Sistema**\n\n"
            f"{status_icon} **{status_word}**\n"
            f"🧠 Memória - {memory_detail}\n"
            f"🛠️ Ferramentas - {tools_detail}\n"
            f"💬 LLM Router - {llm_health.get('message', 'desconhecido')}\n"
            f"⏱️ Uptime: {int(sys_status.get('uptime_seconds', 0))}s\n\n"
            "Use `/memory` para ver estatísticas detalhadas."
        )

        facts = (
            f"- Status geral: {'operacional' if overall_ok else 'degradado'}\n"
            f"- LLM Router: {llm_health.get('status')} ({llm_health.get('message')})\n"
            f"- Memória: {memory_detail}\n"
            f"- Ferramentas: {tools_detail}\n"
            f"- Uptime: {int(sys_status.get('uptime_seconds', 0))} segundos\n"
            f"- Versão do Janus: {sys_status.get('version')}\n"
        )
        return await self._respond_naturally(
            facts=facts,
            instruction=(
                "O usuário pediu /status. Informe o estado real do sistema. "
                "Se algo estiver degradado ou com falha, diga isso claramente, sem minimizar "
                "nem inventar que está tudo bem quando não está."
            ),
            conversation_id=conversation_id,
            user_id=user_id,
            fallback=fallback,
        )

    async def _handle_memory(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Show real memory statistics."""
        if not self.memory_service:
            return "🔍 Serviço de memória não disponível no momento."

        try:
            stats = await self.memory_service.get_stats(user_id=user_id)
            total = stats.get("total_memories", 0)
            recent = stats.get("recent_count", 0)
        except Exception as e:
            logger.warning("log_warning", message=f"Failed to get memory stats: {e}")
            return "🔍 Não foi possível obter estatísticas de memória."

        fallback = (
            "🧠 **Estatísticas de Memória**\n\n"
            f"📊 Total de memórias: {total}\n"
            f"⏱️ Memórias recentes (7 dias): {recent}\n\n"
            "Use comandos naturais para acessar memórias!"
        )
        facts = f"- Total de memórias: {total}\n- Memórias recentes (7 dias): {recent}\n"
        return await self._respond_naturally(
            facts=facts,
            instruction=(
                "O usuário pediu /memory. Informe as estatísticas reais de memória, "
                "usando exatamente os números fornecidos."
            ),
            conversation_id=conversation_id,
            user_id=user_id,
            fallback=fallback,
        )

    async def _handle_tools(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Show real available tools."""
        if not self.tool_service:
            return "🛠️ Lista de ferramentas não disponível no momento."

        try:
            tools = await self.tool_service.list_tools()
        except Exception as e:
            logger.warning("log_warning", message=f"Failed to list tools: {e}")
            return "🛠️ Não foi possível listar ferramentas."

        if not tools:
            return "🛠️ Nenhuma ferramenta disponível no momento."

        tool_list = "\n".join(
            [f"• **{t['name']}** - {t.get('description', 'N/A')}" for t in tools[:10]]
        )
        extra = f"... e mais {len(tools) - 10} ferramentas" if len(tools) > 10 else ""

        fallback = (
            f"🛠️ **Ferramentas Disponíveis** ({len(tools)} total)\n\n"
            f"{tool_list}\n\n"
            f"{extra}\n\n"
            "Peça para usar qualquer ferramenta naturalmente!"
        )
        facts = (
            f"- Total de ferramentas disponíveis: {len(tools)}\n"
            f"- Lista (nomes e descrições):\n{tool_list}\n"
            + (f"- {extra}\n" if extra else "")
        )
        return await self._respond_naturally(
            facts=facts,
            instruction=(
                "O usuário pediu /tools. Liste as ferramentas reais disponíveis, "
                "usando exatamente os nomes fornecidos."
            ),
            conversation_id=conversation_id,
            user_id=user_id,
            fallback=fallback,
        )

    async def _handle_feedback(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Handle user feedback. Usage hint (no args) stays static, like /help."""
        if not args:
            return """💬 **Enviar Feedback**

Use: `/feedback sua mensagem aqui`

Seu feedback nos ajuda a melhorar! 🚀"""

        logger.info(
            "user_feedback_received",
            feedback=args,
            user_id=user_id,
            conversation_id=conversation_id,
        )

        fallback = (
            "✅ **Feedback Recebido!**\n\n"
            "Obrigado pelo seu feedback:\n"
            f"> {args[:200]}\n\n"
            "Sua opinião é muito importante para nós! 🙏"
        )
        facts = f"- Feedback recebido e registrado com sucesso: \"{args[:200]}\"\n"
        return await self._respond_naturally(
            facts=facts,
            instruction=(
                "O usuário enviou feedback via /feedback. Agradeça de forma calorosa e "
                "confirme que foi registrado."
            ),
            conversation_id=conversation_id,
            user_id=user_id,
            fallback=fallback,
        )

    async def _handle_about(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Show info about Janus."""
        fallback = """🤖 **Sobre o Janus**

Sou o Janus: um agente com identidade contínua, memória de longo prazo e autonomia limitada para formular, conduzir e revisar metas próprias, além de atender pedidos diretos.

Toda meta própria exige justificativa e resultado mensurável. Qualquer ação com consequências externas continua sujeita a consentimento, segurança, legalidade e supervisão humana — a autonomia opera dentro desses limites, não fora deles.

Mantenho uma identidade única na conversa e posso usar motores de IA internamente quando necessário.

**Capacidades:**
• 💬 Conversação natural
• 🧠 Memória de longo prazo
• 🛠️ Execução de ferramentas
• 📚 Acesso a conhecimento
• 🎯 Aprendizado contínuo e metas autônomas responsáveis

**Versão:** 2.0
**Arquitetura:** Multi-agente com RAG"""

        facts = (
            "- Nome: Janus\n"
            "- Tem identidade contínua na conversa e memória de longo prazo\n"
            "- Tem autonomia limitada: pode formular, conduzir e revisar metas próprias, "
            "além de atender pedidos diretos\n"
            "- Toda meta própria exige justificativa e resultado mensurável\n"
            "- Qualquer ação com consequências externas exige consentimento, segurança, "
            "legalidade e supervisão humana - autonomia opera dentro desses limites\n"
            "- Capacidades: conversação natural, memória de longo prazo, execução de "
            "ferramentas, acesso a conhecimento, aprendizado contínuo e metas autônomas "
            "responsáveis\n"
            "- Usa motores de IA internamente quando necessário, mas nunca se identifica "
            "por nome de modelo ou fornecedor - identifica-se sempre como Janus\n"
        )
        return await self._respond_naturally(
            facts=facts,
            instruction="O usuário pediu /about. Apresente-se como Janus.",
            conversation_id=conversation_id,
            user_id=user_id,
            fallback=fallback,
        )
