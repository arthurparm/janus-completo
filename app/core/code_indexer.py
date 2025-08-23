# app/core/code_indexer.py (Versão Final Otimizada)

import os
import ast
from app.db.graph import graph_db
import logging

logger = logging.getLogger(__name__)

CODEBASE_DIR = "/app"

class CodeParser(ast.NodeVisitor):
    def __init__(self, file_path):
        self.file_path = file_path
        self.functions = []
        self.classes = []
        self.calls = []
        self._current_function = None

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

def index_codebase() -> dict:
    logger.info(f"Iniciando varredura e análise da base de código em '{CODEBASE_DIR}'...")
    total_files, total_funcs, total_classes, total_calls = 0, 0, 0, 0
    all_calls_to_process = []

    # Limpeza do grafo
    logger.info("Limpando entidades de código antigas do grafo...")
    graph_db.query("MATCH (n) WHERE n:Function OR n:Class DETACH DELETE n")
    graph_db.query("MATCH ()-[r:CONTAINS|CALLS]->() DELETE r")

    # --- PRIMEIRA PASSADA: Criar todos os nós ---
    logger.info("Primeira passada: Analisando arquivos e criando nós de entidade...")
    for root, _, files in os.walk(CODEBASE_DIR):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source_code = f.read()
                    tree = ast.parse(source_code)
                    parser = CodeParser(file_path)
                    parser.visit(tree)

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

                    for call in parser.calls:
                        all_calls_to_process.append({
                            "caller_name": call['caller'],
                            "callee_name": call['callee'],
                            "file_path": file_path
                        })
                    total_files += 1
                    total_funcs += len(parser.functions)
                    total_classes += len(parser.classes)
                except Exception as e:
                    logger.error(f"Falha na primeira passada para o arquivo {file_path}: {e}", exc_info=True)

    # --- SEGUNDA PASSADA OTIMIZADA: Criar relações apenas para funções conhecidas ---
    logger.info("Segunda passada: Criando relações de chamada entre funções definidas no projeto...")
    # Esta consulta é mais eficiente. Ela opera como um JOIN em todo o conjunto de dados.
    # Ela encontra pares de funções (caller, callee) onde o nome da callee de uma chamada
    # corresponde ao nome de uma função existente no grafo.
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

    # O resultado será uma lista de contagens, somamos todas para ter o total.
    total_calls = sum(res['created_relationships'] for res in result)

    summary = f"Análise concluída. {total_files} arquivos | {total_funcs} funções | {total_classes} classes | {total_calls} chamadas internas criadas."
    logger.info(summary)
    
    # INTEGRAÇÃO: Janus registra sua própria ação na memória episódica
    try:
        from app.core.memory_core import memory_core
        from app.models.schemas import Experience
        
        index_experience = Experience(
            type="action_success",
            content=f"Indexação da base de código concluída com sucesso.",
            metadata={"summary": summary, "indexed_files": total_files}
        )
        memory_core.memorize(index_experience)
    except Exception as e:
        logger.error(f"Falha ao registrar a experiência de indexação na memória: {e}")

    return {"message": "Indexação e análise da base de código concluídas.", "summary": summary}