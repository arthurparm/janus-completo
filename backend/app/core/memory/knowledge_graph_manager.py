import ast
import structlog
import os
import time
from typing import Any, Protocol

from prometheus_client import Counter, Histogram

from app.core.infrastructure.resilience import CircuitBreaker, resilient
from app.db.graph import graph_db

logger = structlog.get_logger(__name__)

CODEBASE_DIR = "/app"

# Metrics
_KG_QUERIES = Counter(
    "kg_queries_total", "Total de queries ao grafo", ["operation", "outcome", "exception_type"]
)
_KG_LATENCY = Histogram(
    "kg_query_latency_seconds", "Latência por query ao grafo", ["operation", "outcome"]
)

_CB = CircuitBreaker(failure_threshold=3, recovery_timeout=15)


class GraphPort(Protocol):
    def query(
        self, query: str, params: dict[str, Any] | None = None
    ) -> Any:  # pragma: no cover - interface
        ...


class Neo4jRepository:
    def __init__(self, port: GraphPort):
        self.port = port

    def _do_query(self, query: str, params: dict[str, Any] | None = None) -> Any:
        return self.port.query(query, params=params or {})

    def query(self, operation: str, query: str, params: dict[str, Any] | None = None) -> Any:
        wrapped = resilient(
            max_attempts=3,
            initial_backoff=0.25,
            max_backoff=2.0,
            circuit_breaker=_CB,
            retry_on=(Exception,),
            operation_name=f"kg_{operation}",
        )(self._do_query)
        start = time.perf_counter()
        try:
            result = wrapped(query, params)
            _KG_QUERIES.labels(operation, "success", "").inc()
            _KG_LATENCY.labels(operation, "success").observe(time.perf_counter() - start)
            return result
        except Exception as e:
            _KG_QUERIES.labels(operation, "failure", type(e).__name__).inc()
            _KG_LATENCY.labels(operation, "failure").observe(time.perf_counter() - start)
            raise


repo = Neo4jRepository(graph_db)


class CodeParser(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.functions: list[dict[str, Any]] = []
        self.classes: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []
        self._scope_stack: list[str] = []
        self._current_class: str | None = None
        self._current_function_name: str | None = None
        self._current_function_qualified: str | None = None

    def _qualify_name(self, name: str) -> str:
        if not self._scope_stack:
            return name
        return ".".join([*self._scope_stack, name])

    def _attribute_to_name(self, node: ast.AST) -> str | None:
        parts: list[str] = []
        current = node

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)
            return ".".join(reversed(parts))
        return None

    def visit_ClassDef(self, node: ast.ClassDef):
        class_qualified = self._qualify_name(node.name)
        self.classes.append({"name": node.name, "qualified_name": class_qualified, "line": node.lineno})
        previous_class = self._current_class
        self._scope_stack.append(node.name)
        self._current_class = class_qualified
        self.generic_visit(node)
        self._scope_stack.pop()
        self._current_class = previous_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        function_qualified = self._qualify_name(node.name)
        self.functions.append(
            {"name": node.name, "qualified_name": function_qualified, "line": node.lineno}
        )
        previous_name = self._current_function_name
        previous_qualified = self._current_function_qualified
        self._scope_stack.append(node.name)
        self._current_function_name = node.name
        self._current_function_qualified = function_qualified
        self.generic_visit(node)
        self._scope_stack.pop()
        self._current_function_name = previous_name
        self._current_function_qualified = previous_qualified

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        function_qualified = self._qualify_name(node.name)
        self.functions.append(
            {"name": node.name, "qualified_name": function_qualified, "line": node.lineno}
        )
        previous_name = self._current_function_name
        previous_qualified = self._current_function_qualified
        self._scope_stack.append(node.name)
        self._current_function_name = node.name
        self._current_function_qualified = function_qualified
        self.generic_visit(node)
        self._scope_stack.pop()
        self._current_function_name = previous_name
        self._current_function_qualified = previous_qualified

    def visit_Call(self, node: ast.Call):
        callee_name = None
        callee_qualified = None
        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
            callee_qualified = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee_name = node.func.attr
            attribute_name = self._attribute_to_name(node.func)
            if attribute_name:
                if (
                    self._current_class
                    and (attribute_name.startswith("self.") or attribute_name.startswith("cls."))
                ):
                    _, _, suffix = attribute_name.partition(".")
                    callee_qualified = f"{self._current_class}.{suffix}" if suffix else None
                else:
                    callee_qualified = attribute_name

        if self._current_function_name and callee_name:
            self.calls.append(
                {
                    "caller": self._current_function_name,
                    "caller_qualified": self._current_function_qualified
                    or self._current_function_name,
                    "callee": callee_name,
                    "callee_qualified": callee_qualified or callee_name,
                }
            )
        self.generic_visit(node)


def _parse_python_file(file_path: str) -> CodeParser | None:
    try:
        with open(file_path, encoding="utf-8") as f:
            source_code = f.read()
        tree = ast.parse(source_code)
        parser = CodeParser(file_path)
        parser.visit(tree)
        return parser
    except Exception as e:
        logger.error("log_error", message=f"Falha ao fazer o parse do arquivo {file_path}: {e}", exc_info=True)
        return None


def _create_code_entities_in_graph(parser: CodeParser):
    file_path = parser.file_path
    repo.query("merge_file", "MERGE (f:File:CodeFile {path: $path})", params={"path": file_path})

    for func in parser.functions:
        qualified = func.get("qualified_name") or func["name"]
        repo.query(
            "merge_function",
            """
            MATCH (f:File:CodeFile {path: $file_path})
            MERGE (func:Function:CodeFunction {name: $name, file_path: $file_path})
            SET func.full_name = $full_name
            MERGE (f)-[:CONTAINS]->(func)
            """,
            params={
                "file_path": file_path,
                "name": func["name"],
                "full_name": f"{file_path}::{qualified}",
            },
        )
    for cls in parser.classes:
        qualified = cls.get("qualified_name") or cls["name"]
        repo.query(
            "merge_class",
            """
            MATCH (f:File:CodeFile {path: $file_path})
            MERGE (c:Class:CodeClass {name: $name, file_path: $file_path})
            SET c.full_name = $full_name
            MERGE (f)-[:CONTAINS]->(c)
            """,
            params={
                "file_path": file_path,
                "name": cls["name"],
                "full_name": f"{file_path}::{qualified}",
            },
        )


async def aconsolidate_experiences_into_graph(limit: int = 10) -> dict:
    """
    Busca as experiências mais recentes da memória episódica, extrai conhecimento
    e o insere no grafo semântico (Neo4j) usando o Knowledge Consolidator Worker.
    Esta função agora é assíncrona.
    """
    logger.info("log_info", message=f"Iniciando a consolidação de conhecimento a partir de {limit} experiências.")

    try:
        # Lazy import para evitar carga na inicialização e dependências circulares
        from app.core.workers.knowledge_consolidator_worker import knowledge_consolidator

        stats = await knowledge_consolidator.consolidate_batch(limit=limit)

        summary = (
            f"Consolidação concluída. {stats['successful']}/{stats['total_processed']} "
            f"experiências processadas com sucesso. "
            f"{stats['total_entities']} entidades e {stats['total_relationships']} "
            f"relacionamentos criados no grafo em {stats['elapsed_seconds']:.2f}s."
        )
        if stats["failed"] > 0:
            summary += f" {stats['failed']} experiências falharam."

        logger.info(summary)

        return {"message": "Processo de consolidação concluído.", "summary": summary}

    except Exception as e:
        logger.error("log_error", message=f"Erro na consolidação de experiências: {e}", exc_info=True)
        return {"message": "Erro na consolidação de experiências.", "summary": f"Erro: {e!s}"}


def index_codebase() -> dict:
    """
    Orquestra a análise completa da base de código e a (re)criação do
    grafo de conhecimento estático.
    """
    logger.info("log_info", message=f"Iniciando varredura e análise da base de código em '{CODEBASE_DIR}'...")

    def _ensure_indexes():
        idx_queries = [
            "CREATE INDEX codefile_path_idx IF NOT EXISTS FOR (f:CodeFile) ON (f.path)",
            "CREATE INDEX file_path_idx IF NOT EXISTS FOR (f:File) ON (f.path)",
            "CREATE INDEX function_name_idx IF NOT EXISTS FOR (f:Function) ON (f.name)",
            "CREATE INDEX class_name_idx IF NOT EXISTS FOR (c:Class) ON (c.name)",
            "CREATE INDEX function_name_file_idx IF NOT EXISTS FOR (f:Function) ON (f.name, f.file_path)",
            "CREATE INDEX class_name_file_idx IF NOT EXISTS FOR (c:Class) ON (c.name, c.file_path)",
            "CREATE INDEX codefunction_name_file_idx IF NOT EXISTS FOR (f:CodeFunction) ON (f.name, f.file_path)",
            "CREATE INDEX codeclass_name_file_idx IF NOT EXISTS FOR (c:CodeClass) ON (c.name, c.file_path)",
        ]
        for q in idx_queries:
            try:
                repo.query("ensure_index", q)
            except Exception:
                pass

    _ensure_indexes()

    logger.info("Limpando entidades de código antigas do grafo...")
    repo.query(
        "cleanup_code_entities",
        "MATCH (n) WHERE n:CodeFunction OR n:CodeClass OR n:CodeFile DETACH DELETE n",
    )

    total_files, total_funcs, total_classes = 0, 0, 0
    all_calls_to_process: list[dict[str, Any]] = []

    logger.info("Primeira passada: Analisando arquivos e criando nós de entidade...")
    for root, _, files in os.walk(CODEBASE_DIR):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                parser = _parse_python_file(file_path)

                if parser:
                    _create_code_entities_in_graph(parser)
                    for call in parser.calls:
                        all_calls_to_process.append(
                            {
                                "caller_name": call["caller"],
                                "caller_qualified": call.get("caller_qualified"),
                                "callee_name": call["callee"],
                                "callee_qualified": call.get("callee_qualified"),
                                "file_path": file_path,
                            }
                        )

                    total_files += 1
                    total_funcs += len(parser.functions)
                    total_classes += len(parser.classes)

    logger.info("Segunda passada: Criando relações de chamada entre funções...")
    result = repo.query(
        "merge_calls",
        """
        UNWIND $calls as call
        MATCH (caller:Function:CodeFunction {file_path: call.file_path})
        WHERE (call.caller_qualified IS NOT NULL AND caller.full_name = call.file_path + "::" + call.caller_qualified)
           OR caller.name = call.caller_name
        OPTIONAL MATCH (callee_same_full:Function:CodeFunction {file_path: call.file_path})
        WHERE call.callee_qualified IS NOT NULL
          AND callee_same_full.full_name = call.file_path + "::" + call.callee_qualified
        WITH caller, call, head(collect(callee_same_full)) as callee_same_full
        OPTIONAL MATCH (callee_same_name:Function:CodeFunction {name: call.callee_name, file_path: call.file_path})
        WITH caller, call, callee_same_full, head(collect(callee_same_name)) as callee_same_name
        OPTIONAL MATCH (callee_any_full:Function:CodeFunction)
        WHERE call.callee_qualified IS NOT NULL
          AND callee_any_full.full_name ENDS WITH ("::" + call.callee_qualified)
        WITH caller, call, callee_same_full, callee_same_name, head(collect(callee_any_full)) as callee_any_full
        OPTIONAL MATCH (callee_any_name:Function:CodeFunction {name: call.callee_name})
        WITH caller, coalesce(callee_same_full, callee_same_name, callee_any_full, head(collect(callee_any_name))) as callee
        WHERE callee IS NOT NULL
        MERGE (caller)-[r:CALLS]->(callee)
        RETURN count(r) as created_relationships
        """,
        params={"calls": all_calls_to_process},
    )
    total_calls = sum(res.get("created_relationships", 0) for res in result) if result else 0

    summary = f"Análise de código concluída. {total_files} arquivos | {total_funcs} funções | {total_classes} classes | {total_calls} chamadas internas criadas."
    logger.info(summary)

    return {"message": "Indexação e análise da base de código concluídas.", "summary": summary}


class KnowledgeGraphManager:
    """
    Gerencia operações de alto nível no Grafo de Conhecimento.
    """

    def __init__(self):
        pass

    async def semantic_search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Realiza uma busca 'semântica' (por enquanto baseada em texto) no grafo.
        """
        cypher_query = """
        MATCH (n)
        WHERE (n:Concept OR n:Tool OR n:Error OR n:Solution OR n:Technology)
          AND (toLower(n.name) CONTAINS toLower($query) OR toLower(n.description) CONTAINS toLower($query))
        RETURN n.name as name, labels(n)[0] as type, n.description as summary
        LIMIT $limit
        """
        try:
            # Use graph_db directly to ensure async awaits work correctly
            # graph_db is the singleton from app.db.graph
            if not graph_db:
                logger.warning("GraphDB not initialized for semantic_search")
                return []

            results = await graph_db.query(
                cypher_query, params={"query": query, "limit": limit}, operation="semantic_search"
            )
            return results if results else []
        except Exception as e:
            logger.error("log_error", message=f"Erro no semantic_search: {e}")
            return []


# Singleton instance
knowledge_graph_manager = KnowledgeGraphManager()
