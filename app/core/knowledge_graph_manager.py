# app/core/knowledge_graph_manager.py
# RENOMEADO DE code_indexer.py para refletir seu novo e mais amplo escopo.

import os
import ast
import logging
from typing import List, Dict, Any

from app.db.graph import graph_db
from app.core.memory_core import memory_core # Importa o memory_core para acessar experiências
from app.models.schemas import Experience # Importa o schema de Experience

logger = logging.getLogger(__name__)

CODEBASE_DIR = "/app"

# --- Parte 1: Análise e Parsing de Código Estático ---
# A lógica de parsing foi mantida, mas será chamada por funções mais modulares.

class CodeParser(ast.NodeVisitor):
    """
    Visita os nós de uma Abstract Syntax Tree (AST) para extrair informações
    sobre classes, funções e chamadas de função.
    """
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
    """
    Lê e faz o parse de um único arquivo Python, retornando o objeto parser populado.
    """
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
    """
    Cria os nós de File, Function e Class no grafo a partir de um parser populado.
    """
    file_path = parser.file_path
    graph_db.query("MERGE (f:File {path: $path})", params={"path": file_path})

    for func in parser.functions:
        graph_db.query(
            "MATCH (f:File {path: $file_path}) MERGE (func:Function {name: $name, file_path: $file_path}) MERGE (f)-[:CONTAINS]->(func)",
            params={"file_path": file_path, "name": func['name']}
        )
    for cls in parser.classes:
        graph_db.query(
            "MATCH (f:File {path: $file_path}) MERGE (c:Class {name: $name, file_path: $file_path}) MERGE (f)-[:CONTAINS]->(c)",
            params={"file_path": file_path, "name": cls['name']}
        )

# --- Parte 2: A NOVA LÓGICA DE CONSOLIDAÇÃO DE CONHECIMENTO (SPRINT 8) ---

def consolidate_experiences_into_graph(limit: int = 10) -> dict:
    """
    Busca as experiências mais recentes da memória episódica, extrai conhecimento
    e o insere no grafo semântico (Neo4j).
    """
    logger.info(f"Iniciando a consolidação de conhecimento a partir de {limit} experiências.")

    # 1. Buscar experiências da memória episódica (Vector DB)
    # No futuro, esta query poderia ser mais inteligente (ex: "experiências do tipo 'action_success'").
    recalled_experiences = memory_core.recall(query="ação do sistema", n_results=limit)

    if not recalled_experiences:
        summary = "Nenhuma experiência encontrada para consolidação."
        logger.warning(summary)
        return {"message": "Processo de consolidação concluído.", "summary": summary}

    # 2. Processar cada experiência para criar nós e relações
    nodes_created = 0
    relationships_created = 0

    for exp_dict in recalled_experiences:
        exp = Experience(**exp_dict) # Converte o dicionário de volta para um objeto Pydantic

        # 3. Criar um nó central para a Experiência
        graph_db.query(
            """
            MERGE (e:Experience {id: $id})
            ON CREATE SET e.type = $type, e.content = $content, e.timestamp = $timestamp
            """,
            params={"id": exp.id, "type": exp.type, "content": exp.content, "timestamp": exp.timestamp}
        )
        nodes_created += 1

        # 4. Extrair entidades do metadata (exemplo simples)
        # Uma versão avançada usaria um LLM para extrair entidades do exp.content
        if "summary" in exp.metadata:
            # Exemplo: Se a experiência foi uma indexação, crie um nó para o sumário.
            summary_text = exp.metadata["summary"]
            summary_node_id = f"summary_{exp.id}"

            graph_db.query(
                """
                MATCH (exp:Experience {id: $exp_id})
                MERGE (s:Summary {id: $summary_id, text: $text})
                MERGE (exp)-[:HAS_SUMMARY]->(s)
                """,
                params={"exp_id": exp.id, "summary_id": summary_node_id, "text": summary_text}
            )
            nodes_created += 1
            relationships_created += 1

    summary = f"Consolidação concluída. {len(recalled_experiences)} experiências processadas. {nodes_created} nós e {relationships_created} relações criadas/mescladas no grafo."
    logger.info(summary)

    return {"message": "Processo de consolidação concluído.", "summary": summary}


# --- Parte 3: Função Principal Refatorada para Indexação de Código ---

def index_codebase() -> dict:
    """
    Orquestra a análise completa da base de código e a (re)criação do
    grafo de conhecimento estático.
    """
    logger.info(f"Iniciando varredura e análise da base de código em '{CODEBASE_DIR}'...")

    # Limpeza do grafo de código (deixa outras entidades como :Experience intactas)
    logger.info("Limpando entidades de código antigas do grafo...")
    graph_db.query("MATCH (n) WHERE n:Function OR n:Class OR n:File DETACH DELETE n")

    total_files, total_funcs, total_classes = 0, 0, 0
    all_calls_to_process: List[Dict[str, Any]] = []

    # PRIMEIRA PASSADA: Analisar arquivos e criar nós de entidade
    logger.info("Primeira passada: Analisando arquivos e criando nós de entidade...")
    for root, _, files in os.walk(CODEBASE_DIR):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                parser = _parse_python_file(file_path)

                if parser:
                    _create_code_entities_in_graph(parser)

                    # Armazena as chamadas para processamento na segunda passada
                    for call in parser.calls:
                        all_calls_to_process.append({
                            "caller_name": call['caller'],
                            "callee_name": call['callee'],
                            "file_path": file_path
                        })

                    total_files += 1
                    total_funcs += len(parser.functions)
                    total_classes += len(parser.classes)

    # SEGUNDA PASSADA: Criar relações de chamada
    logger.info("Segunda passada: Criando relações de chamada entre funções...")
    result = graph_db.query(
        """
        UNWIND $calls as call
        MATCH (caller:Function {name: call.caller_name, file_path: call.file_path})
        MATCH (callee:Function {name: call.callee_name})
        MERGE (caller)-[r:CALLS]->(callee)
        RETURN count(r) as created_relationships
        """,
        params={"calls": all_calls_to_process}
    )
    total_calls = sum(res.get('created_relationships', 0) for res in result) if result else 0

    summary = f"Análise de código concluída. {total_files} arquivos | {total_funcs} funções | {total_classes} classes | {total_calls} chamadas internas criadas."
    logger.info(summary)

    return {"message": "Indexação e análise da base de código concluídas.", "summary": summary}