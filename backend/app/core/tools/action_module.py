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
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal  # noqa: F401

import structlog
from langchain.tools import BaseTool, tool
from prometheus_client import Counter, Histogram

from app.core.infrastructure.logging_config import TRACE_ID, USER_ID
from app.core.infrastructure.python_sandbox import python_sandbox
from app.repositories.observability_repository import record_audit_event_direct

try:
    from opentelemetry import trace  # type: ignore

    _OTEL = True
    _tracer = trace.get_tracer(__name__)
except Exception:
    _OTEL = False
    from contextlib import nullcontext

    _tracer = None
import inspect

from pydantic import BaseModel

logger = structlog.get_logger(__name__)

# ==================== MÉTRICAS ====================

_TOOL_CALLS = Counter(
    "action_module_tool_calls_total",
    "Total de chamadas de ferramentas",
    ["tool_name", "category", "outcome"],
)

_TOOL_LATENCY = Histogram(
    "action_module_tool_latency_seconds",
    "Latência de execução de ferramentas",
    ["tool_name", "category"],
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
    DYNAMIC = "dynamic"


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
    rate_limit_per_minute: int | None = None
    requires_confirmation: bool = False
    tags: list[str] = field(default_factory=list)
    namespace: str | None = None
    code_signature: str | None = None
    created_by: str | None = None
    created_at: str | None = None
    llm_model: str | None = None
    evolution_attempt_id: str | None = None


@dataclass
class ToolCall:
    """Registro de uma chamada de ferramenta."""

    tool_name: str
    timestamp: float
    duration_seconds: float
    success: bool
    error: str | None = None
    input_args: dict[str, Any] = field(default_factory=dict)


# ==================== GERADOR DE FERRAMENTAS ====================


class DynamicToolGenerator:
    """
    Gera ferramentas dinamicamente a partir de especificações.

    Permite criar ferramentas Python em runtime sem precisar
    escrever código manualmente.
    """

    @staticmethod
    def from_function_spec(
        name: str, description: str, func: Callable, args_schema: type[BaseModel] | None = None
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
                        cm = (
                            _tracer.start_as_current_span("tool.execute")
                            if _OTEL
                            else nullcontext()
                        )
                        async with cm as span:  # type: ignore
                            if _OTEL and span is not None:
                                try:
                                    tid = TRACE_ID.get()
                                    sid = USER_ID.get()
                                    if tid and tid != "-":
                                        span.set_attribute("janus.trace_id", tid)
                                    if sid and sid != "-":
                                        span.set_attribute("janus.user_id", sid)
                                    span.set_attribute("tool.name", name)
                                except Exception:
                                    pass
                            return await func(*args, **kwargs)
                else:

                    @tool(description=description, args_schema=args_schema)
                    def dynamic_tool(*args, **kwargs):
                        cm = (
                            _tracer.start_as_current_span("tool.execute")
                            if _OTEL
                            else nullcontext()
                        )
                        with cm as span:  # type: ignore
                            if _OTEL and span is not None:
                                try:
                                    tid = TRACE_ID.get()
                                    sid = USER_ID.get()
                                    if tid and tid != "-":
                                        span.set_attribute("janus.trace_id", tid)
                                    if sid and sid != "-":
                                        span.set_attribute("janus.user_id", sid)
                                    span.set_attribute("tool.name", name)
                                except Exception:
                                    pass
                            return func(*args, **kwargs)
            elif is_async:

                @tool(description=description)
                async def dynamic_tool(*args, **kwargs):
                    cm = _tracer.start_as_current_span("tool.execute") if _OTEL else nullcontext()
                    async with cm as span:  # type: ignore
                        if _OTEL and span is not None:
                            try:
                                tid = TRACE_ID.get()
                                sid = USER_ID.get()
                                if tid and tid != "-":
                                    span.set_attribute("janus.trace_id", tid)
                                if sid and sid != "-":
                                    span.set_attribute("janus.user_id", sid)
                                span.set_attribute("tool.name", name)
                            except Exception:
                                pass
                        return await func(*args, **kwargs)
            else:

                @tool(description=description)
                def dynamic_tool(*args, **kwargs):
                    cm = _tracer.start_as_current_span("tool.execute") if _OTEL else nullcontext()
                    with cm as span:  # type: ignore
                        if _OTEL and span is not None:
                            try:
                                tid = TRACE_ID.get()
                                sid = USER_ID.get()
                                if tid and tid != "-":
                                    span.set_attribute("janus.trace_id", tid)
                                if sid and sid != "-":
                                    span.set_attribute("janus.user_id", sid)
                                span.set_attribute("tool.name", name)
                            except Exception:
                                pass
                        return func(*args, **kwargs)

            # Renomeia a ferramenta para o nome desejado
            dynamic_tool.name = name
            dynamic_tool.__name__ = name

            logger.info("log_info", message=f"[ActionModule] Ferramenta dinâmica criada: {name}")
            return dynamic_tool

        except Exception as e:
            logger.error("log_error", message=f"[ActionModule] Erro ao criar ferramenta '{name}': {e}", exc_info=True)
            raise

    @staticmethod
    def from_api_endpoint(
        name: str,
        description: str,
        endpoint_url: str,
        method: str = "GET",
        headers: dict[str, str] | None = None,
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
                from app.core.security.egress_policy import enforce_tool_http_egress

                safe_target = enforce_tool_http_egress(endpoint_url, tool=name)
                if not safe_target:
                    return "URL bloqueada por política de egress/SSRF"

                effective_headers = dict(headers or {})
                effective_headers["Host"] = safe_target.original_host

                async with httpx.AsyncClient(timeout=30) as client:
                    if method.upper() == "GET":
                        response = await client.get(
                            safe_target.fetch_url,
                            params=kwargs,
                            headers=effective_headers,
                            follow_redirects=False,
                        )
                    elif method.upper() == "POST":
                        response = await client.post(
                            safe_target.fetch_url,
                            json=kwargs,
                            headers=effective_headers,
                            follow_redirects=False,
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
            func=api_call,
        )

    @staticmethod
    def from_python_code(
        name: str, description: str, code: str, function_name: str = "execute"
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
                # Executa código no sandbox seguro
                # Passa os argumentos como contexto
                result = python_sandbox.execute(
                    code,
                    context=kwargs,
                    call_function=function_name,
                    call_args=kwargs,
                )

                if not result.success:
                    logger.error("log_error", message=f"[ActionModule] Erro na execução sandbox: {result.error}")
                    return f"Erro na execução: {result.error}"

                # Se houver stdout, retorna
                if result.output and result.output.strip():
                    # Se esperar que a função execute dentro do sandbox, precisamos ver se ela foi chamada.
                    # O sandbox atual executa o código top-level.
                    # Se o código define uma função, ela estará em 'variables'.
                    return result.output.strip()

                # Se a função não foi encontrada mas houve output, retorne o output (comportamento de script)
                if result.output:
                    return result.output.strip()

                return f"Erro: Function '{function_name}' not found or produced no output."

            except Exception as e:
                logger.error("log_error", message=f"[ActionModule] Erro ao executar código dinâmico: {e}", exc_info=True)
                return f"Erro na execução: {e}"

        return DynamicToolGenerator.from_function_spec(
            name=name, description=f"{description}\n🛡️ Sandbox Ativado", func=execute_code
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
        self._tools: dict[str, BaseTool] = {}
        self._metadata: dict[str, ToolMetadata] = {}
        self._namespaces: dict[str, str] = {}
        self._previous_versions: dict[str, BaseTool] = {}
        self._call_history: list[ToolCall] = []
        self._rate_limits: dict[tuple[str, str], list[float]] = {}  # (user_id, tool_name) -> timestamps

    def register(
        self,
        tool: BaseTool,
        category: ToolCategory = ToolCategory.CUSTOM,
        permission_level: PermissionLevel = PermissionLevel.SAFE,
        namespace: str = "core",
        code_signature: str | None = None,
        rate_limit_per_minute: int | None = None,
        requires_confirmation: bool = False,
        tags: list[str] | None = None,
        **kwargs,
    ) -> None:
        """
        Registra uma ferramenta no sistema.

        Args:
            tool: Ferramenta LangChain
            category: Categoria da ferramenta
            permission_level: Nível de permissão
            namespace: Namespace de isolamento (core, evolution, user)
            code_signature: Assinatura SHA-256 do código (para verificação futura)
            rate_limit_per_minute: Limite de chamadas por minuto (None = sem limite)
            requires_confirmation: Se requer confirmação do usuário antes de executar
            tags: Tags para busca e organização
        """
        name = tool.name

        if name in self._tools:
            existing_tool = self._tools[name]
            same_instance = existing_tool is tool
            log_fn = logger.debug if same_instance else logger.info
            log_fn(
                "action_module_tool_reregistered",
                tool_name=name,
                same_instance=same_instance,
                namespace=namespace,
                category=category.value,
            )

        if namespace == "evolution" and code_signature is not None and name in self._tools:
            self._previous_versions[name] = self._tools[name]

        self._tools[name] = tool
        self._namespaces[name] = namespace
        self._metadata[name] = ToolMetadata(
            name=name,
            category=category,
            description=tool.description or "",
            permission_level=permission_level,
            namespace=namespace,
            code_signature=code_signature,
            rate_limit_per_minute=rate_limit_per_minute,
            requires_confirmation=requires_confirmation,
            tags=tags or [],
        )

        if namespace == "evolution":
            meta = self._metadata[name]
            meta.created_by = "evolution_manager"
            meta.created_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
            meta.llm_model = getattr(kwargs.get('tool_spec', {}), 'get', lambda *a: None)('model', None)
            meta.evolution_attempt_id = getattr(kwargs, 'get', lambda *a: None)('attempt_id', None)

        logger.info(
            "action_module_tool_registered",
            tool_name=name,
            namespace=namespace,
            category=category.value,
        )

    def unregister(self, tool_name: str) -> None:
        """Remove uma ferramenta do registro."""
        if tool_name in self._tools:
            del self._tools[tool_name]
            del self._metadata[tool_name]
            self._namespaces.pop(tool_name, None)
            logger.info("action_module_tool_unregistered", tool_name=tool_name)

    def get_tool(self, name: str) -> BaseTool | None:
        """Obtém uma ferramenta pelo nome."""
        return self._tools.get(name)

    def get_metadata(self, name: str) -> ToolMetadata | None:
        """Obtém metadados de uma ferramenta."""
        return self._metadata.get(name)

    def get_tool_provenance(self, name: str) -> dict[str, Any] | None:
        meta = self._metadata.get(name)
        if meta is None:
            return None
        return {
            "name": name,
            "namespace": getattr(meta, "namespace", "core"),
            "code_signature": getattr(meta, "code_signature", None),
            "created_by": getattr(meta, "created_by", None),
            "created_at": getattr(meta, "created_at", None),
            "llm_model": getattr(meta, "llm_model", None),
            "evolution_attempt_id": getattr(meta, "evolution_attempt_id", None),
        }

    def list_tools(
        self,
        category: ToolCategory | None = None,
        permission_level: PermissionLevel | None = None,
        tags: list[str] | None = None,
    ) -> list[BaseTool]:
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

        for name, tool_instance in self._tools.items():
            metadata = self._metadata[name]

            # Aplica filtros
            if category and metadata.category != category:
                continue

            if permission_level and metadata.permission_level != permission_level:
                continue

            if tags and not any(tag in metadata.tags for tag in tags):
                continue

            tools.append(tool_instance)

        return tools

    def _rate_limit_key(self, tool_name: str, user_id: str | None = None) -> tuple[str, str]:
        effective_user_id = str(user_id) if user_id else USER_ID.get()
        if not effective_user_id or effective_user_id == "-":
            effective_user_id = "global"
        return (effective_user_id, tool_name)

    def check_rate_limit(self, tool_name: str, user_id: str | None = None) -> bool:
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
        key = self._rate_limit_key(tool_name, user_id)
        if key not in self._rate_limits:
            self._rate_limits[key] = []

        self._rate_limits[key] = [
            ts for ts in self._rate_limits[key] if ts > one_minute_ago
        ]

        # Verifica limite
        current_calls = len(self._rate_limits[key])
        return current_calls < metadata.rate_limit_per_minute

    def record_call(
        self,
        tool_name: str,
        duration: float,
        success: bool,
        error: str | None = None,
        input_args: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> None:
        """Registra uma chamada de ferramenta para telemetria."""
        now = time.time()

        # Adiciona ao rate limit tracking
        key = self._rate_limit_key(tool_name, user_id)
        if key not in self._rate_limits:
            self._rate_limits[key] = []
        self._rate_limits[key].append(now)

        # Registra histórico
        call = ToolCall(
            tool_name=tool_name,
            timestamp=now,
            duration_seconds=duration,
            success=success,
            error=error,
            input_args=input_args or {},
        )
        self._call_history.append(call)

        # Limita histórico a 1000 últimas chamadas
        if len(self._call_history) > 1000:
            self._call_history = self._call_history[-1000:]

        # Métricas Prometheus
        metadata = self._metadata.get(tool_name)
        category = metadata.category.value if metadata else "unknown"
        outcome = "success" if success else "error"
        try:
            cm = _tracer.start_as_current_span("tool.call") if _OTEL else nullcontext()
            with cm as span:  # type: ignore
                if _OTEL and span is not None:
                    try:
                        tid = TRACE_ID.get()
                        sid = USER_ID.get()
                        if tid and tid != "-":
                            span.set_attribute("janus.trace_id", tid)
                        if sid and sid != "-":
                            span.set_attribute("janus.user_id", sid)
                        span.set_attribute("tool.name", tool_name)
                        span.set_attribute("tool.outcome", outcome)
                        span.set_attribute("tool.duration_seconds", float(duration))
                    except Exception:
                        pass
        except Exception:
            pass

        _TOOL_CALLS.labels(tool_name, category, outcome).inc()
        _TOOL_LATENCY.labels(tool_name, category).observe(duration)
        try:
            effective_user_id = user_id or USER_ID.get()
            record_audit_event_direct(
                {
                    "user_id": effective_user_id,
                    "endpoint": f"tool:{tool_name}",
                    "action": "tool_call",
                    "tool": tool_name,
                    "status": outcome,
                    "latency_ms": int(duration * 1000),
                    "trace_id": TRACE_ID.get(),
                }
            )
        except Exception:
            pass

    def get_statistics(self) -> dict[str, Any]:
        """Retorna estatísticas de uso de ferramentas."""
        total_calls = len(self._call_history)
        successful_calls = sum(1 for c in self._call_history if c.success)

        tool_usage = {}
        for call in self._call_history:
            if call.tool_name not in tool_usage:
                tool_usage[call.tool_name] = {"total": 0, "success": 0, "avg_duration": 0.0}
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
            "tool_usage": tool_usage,
        }

    def register_tool(
        self,
        tool: BaseTool,
        namespace: str = "core",
        category: ToolCategory = ToolCategory.CUSTOM,
        permission_level: PermissionLevel = PermissionLevel.SAFE,
        rate_limit_per_minute: int | None = None,
        requires_confirmation: bool = False,
        tags: list[str] | None = None,
        code_signature: str | None = None,
    ) -> None:
        """
        Registra uma ferramenta com isolamento de namespace.

        Valida que o namespace 'evolution' não pode sobrescrever ferramentas do namespace 'core'.

        Args:
            tool: Ferramenta LangChain
            namespace: Namespace de isolamento (core, evolution, user)
            category: Categoria da ferramenta
            permission_level: Nível de permissão
            rate_limit_per_minute: Limite de chamadas por minuto
            requires_confirmation: Se requer confirmação do usuário
            tags: Tags para busca e organização
            code_signature: Assinatura SHA-256 do código (para verificação futura)

        Raises:
            ValueError: Se tentar registrar em 'evolution' uma ferramenta já existente em 'core'
        """
        name = tool.name

        if namespace == "evolution" and name in self._namespaces and self._namespaces[name] == "core":
            raise ValueError(
                f"Cannot register tool '{name}' in 'evolution' namespace: "
                f"it already exists in 'core' namespace. Evolution cannot overwrite core tools."
            )

        self.register(
            tool=tool,
            category=category,
            permission_level=permission_level,
            namespace=namespace,
            code_signature=code_signature,
            rate_limit_per_minute=rate_limit_per_minute,
            requires_confirmation=requires_confirmation,
            tags=tags,
        )

    def resolve_tool(self, name: str, namespace_hint: str | None = None) -> BaseTool | None:
        """
        Busca hierárquica de ferramenta: evolution → core → user.

        Se namespace_hint for fornecido, prioriza o namespace indicado
        antes de seguir a ordem hierárquica padrão.

        Args:
            name: Nome da ferramenta
            namespace_hint: Namespace sugerido para busca prioritária

        Returns:
            A ferramenta encontrada ou None
        """
        priority_order = ["evolution", "core", "user"]

        if namespace_hint and namespace_hint in priority_order:
            priority_order.remove(namespace_hint)
            priority_order.insert(0, namespace_hint)

        for ns in priority_order:
            if name in self._namespaces and self._namespaces[name] == ns:
                return self._tools.get(name)

        return self._tools.get(name)

    def list_by_namespace(self, namespace: str) -> list[BaseTool]:
        """
        Lista todas as ferramentas em um namespace específico.

        Args:
            namespace: Namespace a ser consultado

        Returns:
            Lista de ferramentas no namespace
        """
        tools: list[BaseTool] = []
        for name, ns in self._namespaces.items():
            if ns == namespace:
                tool = self._tools.get(name)
                if tool is not None:
                    tools.append(tool)
        return tools

    def get_namespace(self, name: str) -> str | None:
        """
        Retorna o namespace de uma ferramenta.

        Args:
            name: Nome da ferramenta

        Returns:
            Namespace da ferramenta ou None se não encontrada
        """
        return self._namespaces.get(name)

    def verify_tool_signature(self, name: str) -> bool:
        """
        Verifica a assinatura SHA-256 da ferramenta.

        (Placeholder - implementação futura)

        Args:
            name: Nome da ferramenta

        Returns:
            True se a assinatura for válida
        """
        return True

    def rollback_tool(self, name: str) -> bool:
        """
        Reverte uma ferramenta para a versão anterior.

        Args:
            name: Nome da ferramenta

        Returns:
            True se o rollback foi bem-sucedido
        """
        if name not in self._tools or name not in self._previous_versions:
            return False

        previous_tool = self._previous_versions.pop(name)
        self._tools[name] = previous_tool

        if name in self._metadata:
            self._metadata[name].code_signature = None

        logger.info(
            "tool_rolled_back",
            tool_name=name,
            namespace=self._namespaces.get(name),
        )
        return True


# ==================== INSTÂNCIA GLOBAL ====================

# Registro global de ferramentas
action_registry = ActionRegistry()


# ==================== FUNÇÕES DE CONVENIÊNCIA ====================


def register_tool(tool: BaseTool, category: ToolCategory = ToolCategory.CUSTOM, namespace: str = "core", **kwargs) -> None:
    """Atalho para registrar ferramenta no registro global."""
    action_registry.register(tool, category=category, namespace=namespace, **kwargs)


def create_tool_from_function(
    name: str,
    description: str,
    func: Callable,
    category: ToolCategory = ToolCategory.CUSTOM,
    **kwargs,
) -> BaseTool:
    """
    Cria e registra ferramenta a partir de função Python.

    Returns:
        A ferramenta criada
    """
    tool = DynamicToolGenerator.from_function_spec(name, description, func)
    register_tool(tool, category=category, **kwargs)
    return tool


def get_all_tools() -> list[BaseTool]:
    """Retorna todas as ferramentas registradas."""
    return list(action_registry._tools.values())


def get_tools_by_category(category: ToolCategory) -> list[BaseTool]:
    """Retorna ferramentas de uma categoria específica."""
    return action_registry.list_tools(category=category)
