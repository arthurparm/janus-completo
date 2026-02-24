"""
Chat Command Handler Service.
Handles quick commands like /help, /status, /memory, /tools.
Extracted from ChatService to reduce complexity.
"""

import structlog
from typing import Any

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

    def __init__(self, tool_service: Any | None = None, memory_service: Any | None = None):
        """
        Initialize command handler.

        Args:
            tool_service: Optional tool service for /tools command
            memory_service: Optional memory service for /memory command
        """
        self.tool_service = tool_service
        self.memory_service = memory_service

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

    async def _handle_help(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Show available commands."""
        return """📚 **Comandos Disponíveis**

`/help` - Mostra esta mensagem
`/status` - Status do sistema
`/memory` - Estatísticas de memória
`/tools` - Lista de ferramentas disponíveis
`/feedback [mensagem]` - Enviar feedback
`/about` - Sobre o Janus

Digite qualquer comando para mais detalhes!"""

    async def _handle_status(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Show system status."""
        return """⚡ **Status do Sistema**

✅ **Online** - Todos os sistemas operacionais
🧠 **Memória** - Funcionando
🛠️ **Ferramentas** - Disponíveis
💬 **Chat** - Ativo

Use `/memory` para ver estatísticas detalhadas."""

    async def _handle_memory(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Show memory statistics."""
        if not self.memory_service:
            return "🔍 Serviço de memória não disponível no momento."

        try:
            # Get memory stats
            stats = await self.memory_service.get_stats(user_id=user_id)

            total = stats.get("total_memories", 0)
            recent = stats.get("recent_count", 0)

            return f"""🧠 **Estatísticas de Memória**

📊 Total de memórias: {total}
⏱️ Memórias recentes (7 dias): {recent}

Use comandos naturais para acessar memórias!"""
        except Exception as e:
            logger.warning("log_warning", message=f"Failed to get memory stats: {e}")
            return "🔍 Não foi possível obter estatísticas de memória."

    async def _handle_tools(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Show available tools."""
        if not self.tool_service:
            return "🛠️ Lista de ferramentas não disponível no momento."

        try:
            tools = await self.tool_service.list_tools()

            if not tools:
                return "🛠️ Nenhuma ferramenta disponível no momento."

            tool_list = "\n".join(
                [f"• **{t['name']}** - {t.get('description', 'N/A')}" for t in tools[:10]]
            )

            return f"""🛠️ **Ferramentas Disponíveis** ({len(tools)} total)

{tool_list}

{f'... e mais {len(tools) - 10} ferramentas' if len(tools) > 10 else ''}

Peça para usar qualquer ferramenta naturalmente!"""
        except Exception as e:
            logger.warning("log_warning", message=f"Failed to list tools: {e}")
            return "🛠️ Não foi possível listar ferramentas."

    async def _handle_feedback(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Handle user feedback."""
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

        return f"""✅ **Feedback Recebido!**

Obrigado pelo seu feedback:
> {args[:200]}

Sua opinião é muito importante para nós! 🙏"""

    async def _handle_about(self, args: str, conversation_id: str, user_id: str | None) -> str:
        """Show info about Janus."""
        return """🤖 **Sobre o Janus**

Sou o Janus, seu assistente de IA avançado.

**Capacidades:**
• 💬 Conversação natural
• 🧠 Memória de longo prazo
• 🛠️ Execução de ferramentas
• 📚 Acesso a conhecimento
• 🎯 Aprendizado contínuo

**Versão:** 2.0
**Arquitetura:** Multi-agente com RAG

Digite qualquer pergunta ou comando!"""
