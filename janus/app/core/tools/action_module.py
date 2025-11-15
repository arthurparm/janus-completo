"""
Sprint 6: Action Module - Gateway de Ferramentas Dinâmicas

Provê um sistema extensível de registro e gerenciamento de ferramentas (tools)
que o agente pode utilizar para interagir com o mundo externo.

Funcionalidades:
- Registro dinâmico de ferramentas
- Categorização por tipo (filesystem, api, computation, etc)
- Geração automática de ferramentas a partir de especificações
- Controle de permissões e rate limiting
- Telemetria de uso de ferramentas
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Callable, Any, Type

from langchain.tools import BaseTool, tool
from prometheus_client import Counter, Histogram
from pydantic import BaseModel
import inspect

logger = logging.getLogger(__name__)

# ==================== MÉTRICAS ====================

_TOOL_CALLS = Counter(
    "action_module_tool_calls_total",
    "Total de chamadas de ferramentas",
    ["tool_name", "category", "outcome"]
)

_TOOL_LATENCY = Histogram(
    "action_module_tool_latency_seconds",
    "Latência de execução de ferramentas",
    ["tool_name", "category"]
)


# ==================== ENUMS ====================

class ToolCategory(Enum):
    """Categorias de ferramentas disponíveis."""
    FILESYSTEM = "filesystem"
    API = "api"
    DATABASE = "database"
    COMPUTATION = "computation"
    WEB = "web"
    SYSTEM = "system"
    CUSTOM = "custom"


class PermissionLevel(Enum):
    """Níveis de permissão para ferramentas."""
    READ_ONLY = "read_only"
    SAFE = "safe"
    WRITE = "write"
    DANGEROUS = "dangerous"


# ==================== DATACLASSES ====================

@dataclass
class ToolMetadata:
    """Metadados sobre uma ferramenta."""
    name: str
    category: ToolCategory
    description: str
    permission_level: PermissionLevel
    rate_limit_per_minute: Optional[int] = None
    requires_confirmation: bool = False
    tags: List[str] = field(default_factory=list)


@dataclass
class ToolCall:
    """Registro de uma chamada de ferramenta."""
    tool_name: str
    timestamp: float
    duration_seconds: float
    success: bool
    error: Optional[str] = None
    input_args: Dict[str, Any] = field(default_factory=dict)


# ==================== GERADOR DE FERRAMENTAS ====================

class DynamicToolGenerator:
    """
    Gera ferramentas dinamicamente a partir de especificações.

    Permite criar ferramentas Python em runtime sem precisar
    escrever código manualmente.
    """

    @staticmethod
    def from_function_spec(
            name: str,
            description: str,
            func: Callable,
            args_schema: Optional[Type[BaseModel]] = None
    ) -> BaseTool:
        """
        Cria uma ferramenta LangChain a partir de uma função Python.

        Args:
            name: Nome da ferramenta
            description: Descrição do que ela faz
            func: Função Python a ser envolvida
            args_schema: Schema Pydantic para validação de argumentos

        Returns:
            BaseTool pronta para uso
        """
        try:
            is_async = inspect.iscoroutinefunction(func)
            if args_schema:
                if is_async:
                    @tool(description=description, args_schema=args_schema)
                    async def dynamic_tool(*args, **kwargs):
                        return await func(*args, **kwargs)
                else:
                    @tool(description=description, args_schema=args_schema)
                    def dynamic_tool(*args, **kwargs):
                        return func(*args, **kwargs)
            else:
                if is_async:
                    @tool(description=description)
                    async def dynamic_tool(*args, **kwargs):
                        return await func(*args, **kwargs)
                else:
                    @tool(description=description)
                    def dynamic_tool(*args, **kwargs):
                        return func(*args, **kwargs)

            # Renomeia a ferramenta para o nome desejado
            dynamic_tool.name = name
            dynamic_tool.__name__ = name

            logger.info(f"[ActionModule] Ferramenta dinâmica criada: {name}")
            return dynamic_tool

        except Exception as e:
            logger.error(f"[ActionModule] Erro ao criar ferramenta '{name}': {e}", exc_info=True)
            raise

    @staticmethod
    def from_api_endpoint(
            name: str,
            description: str,
            endpoint_url: str,
            method: str = "GET",
            headers: Optional[Dict[str, str]] = None
    ) -> BaseTool:
        """
        Cria ferramenta que chama um endpoint HTTP.

        Args:
            name: Nome da ferramenta
            description: Descrição
            endpoint_url: URL do endpoint
            method: Método HTTP (GET, POST, etc)
            headers: Headers customizados

        Returns:
            BaseTool que faz chamadas HTTP
        """
        import httpx

        async def api_call(**kwargs) -> str:
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    if method.upper() == "GET":
                        response = await client.get(
                            endpoint_url,
                            params=kwargs,
                            headers=headers or {},
                        )
                    elif method.upper() == "POST":
                        response = await client.post(
                            endpoint_url,
                            json=kwargs,
                            headers=headers or {},
                        )
                    else:
                        return f"Método HTTP '{method}' não suportado"

                response.raise_for_status()
                return response.text

            except httpx.HTTPError as e:
                return f"Erro na chamada API: {e}"

        return DynamicToolGenerator.from_function_spec(
            name=name,
            description=f"{description}\nEndpoint: {method} {endpoint_url}",
            func=api_call
        )

    @staticmethod
    def from_python_code(
            name: str,
            description: str,
            code: str,
            function_name: str = "execute"
    ) -> BaseTool:
        """
        Cria ferramenta a partir de código Python fornecido como string.

        ATENÇÃO: Use com cuidado! Executar código arbitrário é perigoso.
        Recomenda-se usar apenas em ambientes controlados ou com validação rigorosa.

        Args:
            name: Nome da ferramenta
            description: Descrição
            code: Código Python completo
            function_name: Nome da função a ser chamada

        Returns:
            BaseTool que executa o código
        """

        def execute_code(**kwargs) -> str:
            try:
                # Cria namespace isolado
                namespace = {"__name__": "__dynamic_tool__"}

                # Executa código no namespace
                exec(code, namespace)

                # Obtém função
                if function_name not in namespace:
                    return f"Erro: Função '{function_name}' não encontrada no código"

                func = namespace[function_name]

                # Executa função com argumentos
                result = func(**kwargs)

                return str(result)

            except Exception as e:
                logger.error(f"[ActionModule] Erro ao executar código dinâmico: {e}", exc_info=True)
                return f"Erro na execução: {e}"

        return DynamicToolGenerator.from_function_spec(
            name=name,
            description=f"{description}\n⚠️ Ferramenta gerada dinamicamente",
            func=execute_code
        )


# ==================== REGISTRO DE FERRAMENTAS ====================

class ActionRegistry:
    """
    Registro centralizado de todas as ferramentas disponíveis.

    Gerencia:
    - Registro e desregistro de ferramentas
    - Categorização
    - Controle de permissões
    - Rate limiting
    - Telemetria
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        self._call_history: List[ToolCall] = []
        self._rate_limits: Dict[str, List[float]] = {}  # tool_name -> timestamps

    def register(
            self,
            tool: BaseTool,
            category: ToolCategory = ToolCategory.CUSTOM,
            permission_level: PermissionLevel = PermissionLevel.SAFE,
            rate_limit_per_minute: Optional[int] = None,
            requires_confirmation: bool = False,
            tags: Optional[List[str]] = None
    ) -> None:
        """
        Registra uma ferramenta no sistema.

        Args:
            tool: Ferramenta LangChain
            category: Categoria da ferramenta
            permission_level: Nível de permissão
            rate_limit_per_minute: Limite de chamadas por minuto (None = sem limite)
            requires_confirmation: Se requer confirmação do usuário antes de executar
            tags: Tags para busca e organização
        """
        name = tool.name

        if name in self._tools:
            logger.warning(f"[ActionModule] Ferramenta '{name}' já registrada. Substituindo...")

        self._tools[name] = tool
        self._metadata[name] = ToolMetadata(
            name=name,
            category=category,
            description=tool.description or "",
            permission_level=permission_level,
            rate_limit_per_minute=rate_limit_per_minute,
            requires_confirmation=requires_confirmation,
            tags=tags or []
        )

        logger.info(f"[ActionModule] Ferramenta registrada: {name} [{category.value}]")

    def unregister(self, tool_name: str) -> None:
        """Remove uma ferramenta do registro."""
        if tool_name in self._tools:
            del self._tools[tool_name]
            del self._metadata[tool_name]
            logger.info(f"[ActionModule] Ferramenta removida: {tool_name}")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Obtém uma ferramenta pelo nome."""
        return self._tools.get(name)

    def get_metadata(self, name: str) -> Optional[ToolMetadata]:
        """Obtém metadados de uma ferramenta."""
        return self._metadata.get(name)

    def list_tools(
            self,
            category: Optional[ToolCategory] = None,
            permission_level: Optional[PermissionLevel] = None,
            tags: Optional[List[str]] = None
    ) -> List[BaseTool]:
        """
        Lista ferramentas com filtros opcionais.

        Args:
            category: Filtrar por categoria
            permission_level: Filtrar por nível de permissão
            tags: Filtrar por tags (ferramenta deve ter pelo menos uma das tags)

        Returns:
            Lista de ferramentas que atendem aos critérios
        """
        tools = []

        for name, tool in self._tools.items():
            metadata = self._metadata[name]

            # Aplica filtros
            if category and metadata.category != category:
                continue

            if permission_level and metadata.permission_level != permission_level:
                continue

            if tags and not any(tag in metadata.tags for tag in tags):
                continue

            tools.append(tool)

        return tools

    def check_rate_limit(self, tool_name: str) -> bool:
        """
        Verifica se a ferramenta atingiu o rate limit.

        Returns:
            True se pode ser chamada, False se atingiu o limite
        """
        metadata = self._metadata.get(tool_name)
        if not metadata or not metadata.rate_limit_per_minute:
            return True  # Sem rate limit

        now = time.time()
        one_minute_ago = now - 60

        # Limpa timestamps antigos
        if tool_name not in self._rate_limits:
            self._rate_limits[tool_name] = []

        self._rate_limits[tool_name] = [
            ts for ts in self._rate_limits[tool_name]
            if ts > one_minute_ago
        ]

        # Verifica limite
        current_calls = len(self._rate_limits[tool_name])
        return current_calls < metadata.rate_limit_per_minute

    def record_call(
            self,
            tool_name: str,
            duration: float,
            success: bool,
            error: Optional[str] = None,
            input_args: Optional[Dict[str, Any]] = None
    ) -> None:
        """Registra uma chamada de ferramenta para telemetria."""
        now = time.time()

        # Adiciona ao rate limit tracking
        if tool_name not in self._rate_limits:
            self._rate_limits[tool_name] = []
        self._rate_limits[tool_name].append(now)

        # Registra histórico
        call = ToolCall(
            tool_name=tool_name,
            timestamp=now,
            duration_seconds=duration,
            success=success,
            error=error,
            input_args=input_args or {}
        )
        self._call_history.append(call)

        # Limita histórico a 1000 últimas chamadas
        if len(self._call_history) > 1000:
            self._call_history = self._call_history[-1000:]

        # Métricas Prometheus
        metadata = self._metadata.get(tool_name)
        category = metadata.category.value if metadata else "unknown"
        outcome = "success" if success else "error"

        _TOOL_CALLS.labels(tool_name, category, outcome).inc()
        _TOOL_LATENCY.labels(tool_name, category).observe(duration)

    def get_statistics(self) -> Dict[str, Any]:
        """Retorna estatísticas de uso de ferramentas."""
        total_calls = len(self._call_history)
        successful_calls = sum(1 for c in self._call_history if c.success)

        tool_usage = {}
        for call in self._call_history:
            if call.tool_name not in tool_usage:
                tool_usage[call.tool_name] = {
                    "total": 0,
                    "success": 0,
                    "avg_duration": 0.0
                }
            tool_usage[call.tool_name]["total"] += 1
            if call.success:
                tool_usage[call.tool_name]["success"] += 1

        # Calcula duração média
        for tool_name, stats in tool_usage.items():
            calls = [c for c in self._call_history if c.tool_name == tool_name]
            avg_dur = sum(c.duration_seconds for c in calls) / len(calls) if calls else 0.0
            stats["avg_duration"] = round(avg_dur, 3)

        return {
            "total_tools_registered": len(self._tools),
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "success_rate": round(successful_calls / total_calls, 3) if total_calls > 0 else 0.0,
            "tool_usage": tool_usage
        }


# ==================== INSTÂNCIA GLOBAL ====================

# Registro global de ferramentas
action_registry = ActionRegistry()


# ==================== FUNÇÕES DE CONVENIÊNCIA ====================

def register_tool(
        tool: BaseTool,
        category: ToolCategory = ToolCategory.CUSTOM,
        **kwargs
) -> None:
    """Atalho para registrar ferramenta no registro global."""
    action_registry.register(tool, category=category, **kwargs)


def create_tool_from_function(
        name: str,
        description: str,
        func: Callable,
        category: ToolCategory = ToolCategory.CUSTOM,
        **kwargs
) -> BaseTool:
    """
    Cria e registra ferramenta a partir de função Python.

    Returns:
        A ferramenta criada
    """
    tool = DynamicToolGenerator.from_function_spec(name, description, func)
    register_tool(tool, category=category, **kwargs)
    return tool


def get_all_tools() -> List[BaseTool]:
    """Retorna todas as ferramentas registradas."""
    return list(action_registry._tools.values())


def get_tools_by_category(category: ToolCategory) -> List[BaseTool]:
    """Retorna ferramentas de uma categoria específica."""
    return action_registry.list_tools(category=category)
