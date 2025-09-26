
import ast
import logging
import os
import time
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Protocol

from prometheus_client import Counter, Histogram

from app.core.memory_core import memory_core  # Importa o memory_core para acessar experiências
from app.db.graph import graph_db
from app.core.resilience import resilient, CircuitBreaker

logger = logging.getLogger(__name__)

CODEBASE_DIR = "/app"

# Metrics
_KG_QUERIES = Counter("kg_queries_total", "Total de queries ao grafo", ["operation", "outcome", "exception_type"])
_KG_LATENCY = Histogram("kg_query_latency_seconds", "Latência por query ao grafo", ["operation", "outcome"])

_CB = CircuitBreaker(failure_threshold=3, recovery_timeout=15)


class GraphPort(Protocol):
    def query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:  # pragma: no cover - interface
        ...


class Neo4jRepository:
    def __init__(self, port: GraphPort):
        self.port = port

    def _do_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.port.query(query, params=params or {})

    def query(self, operation: str, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
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
        self.functions: List[Dict[str, Any]] = []
        self.classes: List[Dict[str, Any]] = []
        self.calls: List[Dict[str, Any]] = []
        self._current_function: str | None = None

    def visit_ClassDef(self, node: ast.ClassDef):
        self.classes.append({'name': node.name, 'line': node.lineno})
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.functions.append({'name': node.name, 'line': node.lineno})
        previous_function = self._current_function
        self._current_function = node.name
        self.generic_visit(node)
        self._current_function = previous_function

    def visit_Call(self, node: ast.Call):
        callee_name = None
        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            callee_name = node.func.attr

        if self._current_function and callee_name:
            self.calls.append({
                'caller': self._current_function,
                'callee': callee_name,
            })
        self.generic_visit(node)


def _parse_python_file(file_path: str) -> CodeParser | None:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source_code = f.read()
        tree = ast.parse(source_code)
        parser = CodeParser(file_path)
        parser.visit(tree)
        return parser
    except Exception as e:
        logger.error(f"Falha ao fazer o parse do arquivo {file_path}: {e}", exc_info=True)
        return None


def _create_code_entities_in_graph(parser: CodeParser):
    file_path = parser.file_path
    repo.query("merge_file", "MERGE (f:File:CodeFile {path: $path})", params={"path": file_path})

    for func in parser.functions:
        repo.query(
            "merge_function",
            "MATCH (f:File:CodeFile {path: $file_path}) MERGE (func:Function:CodeFunction {name: $name, file_path: $file_path}) MERGE (f)-[:CONTAINS]->(func)",
            params={"file_path": file_path, "name": func['name']}
        )
    for cls in parser.classes:
        repo.query(
            "merge_class",
            "MATCH (f:File:CodeFile {path: $file_path}) MERGE (c:Class:CodeClass {name: $name, file_path: $file_path}) MERGE (f)-[:CONTAINS]->(c)",
            params={"file_path": file_path, "name": cls['name']}
        )



def consolidate_experiences_into_graph(limit: int = 10) -> dict:
    """
    Busca as experiências mais recentes da memória episódica, extrai conhecimento
    e o insere no grafo semântico (Neo4j).
    """
    logger.info(f"Iniciando a consolidação de conhecimento a partir de {limit} experiências.")

    recalled_experiences = memory_core.recall(query="ação do sistema", n_results=limit)

    if not recalled_experiences:
        summary = "Nenhuma experiência encontrada para consolidação."
        logger.warning(summary)
        return {"message": "Processo de consolidação concluído.", "summary": summary}

    nodes_created = 0
    relationships_created = 0

    for exp_dict in recalled_experiences:
        # Não tentamos mais converter para um objeto Pydantic `Experience`.
        # Em vez disso, trabalhamos diretamente com o dicionário retornado pelo `memory_core`,
        # que é mais robusto e evita o erro de validação do campo "distance".
        exp_id = exp_dict.get("id")
        exp_metadata = exp_dict.get("metadata", {})
        exp_type = exp_metadata.get("type", "unknown")
        exp_content = exp_dict.get("content", "")
        exp_timestamp = exp_metadata.get("timestamp", "")

        if not exp_id:
            continue

        repo.query(
            "merge_experience",
            """
            MERGE (e:Experience {id: $id})
            ON CREATE SET e.type = $type, e.content = $content, e.timestamp = $timestamp
            """,
            params={"id": exp_id, "type": exp_type, "content": exp_content, "timestamp": exp_timestamp}
        )
        nodes_created += 1

        if "summary" in exp_metadata:
            summary_text = exp_metadata["summary"]
            summary_node_id = f"summary_{exp_id}"

            repo.query(
                "merge_summary",
                """
                MATCH (exp:Experience {id: $exp_id})
                MERGE (s:Summary {id: $summary_id, text: $text})
                MERGE (exp)-[:HAS_SUMMARY]->(s)
                """,
                params={"exp_id": exp_id, "summary_id": summary_node_id, "text": summary_text}
            )
            nodes_created += 1
            relationships_created += 1

    summary = f"Consolidação concluída. {len(recalled_experiences)} experiências processadas. {nodes_created} nós e {relationships_created} relações criadas/mescladas no grafo."
    logger.info(summary)

    return {"message": "Processo de consolidação concluído.", "summary": summary}


def index_codebase() -> dict:
    """
    Orquestra a análise completa da base de código e a (re)criação do
    grafo de conhecimento estático.
    """
    logger.info(f"Iniciando varredura e análise da base de código em '{CODEBASE_DIR}'...")

    logger.info("Limpando entidades de código antigas do grafo...")
    repo.query("cleanup_code_entities", "MATCH (n) WHERE n:CodeFunction OR n:CodeClass OR n:CodeFile DETACH DELETE n")

    total_files, total_funcs, total_classes = 0, 0, 0
    all_calls_to_process: List[Dict[str, Any]] = []

    logger.info("Primeira passada: Analisando arquivos e criando nós de entidade...")
    for root, _, files in os.walk(CODEBASE_DIR):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                parser = _parse_python_file(file_path)

                if parser:
                    _create_code_entities_in_graph(parser)
                    for call in parser.calls:
                        all_calls_to_process.append({
                            "caller_name": call['caller'],
                            "callee_name": call['callee'],
                            "file_path": file_path
                        })

                    total_files += 1
                    total_funcs += len(parser.functions)
                    total_classes += len(parser.classes)

    logger.info("Segunda passada: Criando relações de chamada entre funções...")
    result = repo.query(
        "merge_calls",
        """
        UNWIND $calls as call
        MATCH (caller:Function:CodeFunction {name: call.caller_name, file_path: call.file_path})
        MATCH (callee:Function:CodeFunction {name: call.callee_name})
        MERGE (caller)-[r:CALLS]->(callee)
        RETURN count(r) as created_relationships
        """,
        params={"calls": all_calls_to_process}
    )
    total_calls = sum(res.get('created_relationships', 0) for res in result) if result else 0

    summary = f"Análise de código concluída. {total_files} arquivos | {total_funcs} funções | {total_classes} classes | {total_calls} chamadas internas criadas."
    logger.info(summary)

    return {"message": "Indexação e análise da base de código concluídas.", "summary": summary}
