import json
import logging
from pathlib import Path
from typing import List

from langchain.tools import tool, BaseTool
from pydantic import BaseModel, Field, validator

from app.core import filesystem_manager
from app.core.action_module import (
    action_registry,
    create_tool_from_function,
    ToolCategory,
    PermissionLevel
)
from app.core.context_manager import context_manager
from app.core.enums import AgentType  # <-- Corrigido
from app.core.faulty_tools import get_faulty_tools
from app.core.memory_core import memory_core
from app.core.python_sandbox import python_sandbox
from app.db.graph import graph_db

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path("/app/workspace").resolve()
ALLOWED_EXTENSIONS = {".txt", ".py", ".json", ".md", ".csv"}
MAX_FILE_SIZE = 1024 * 1024  # 1 MB


class WriteFileInput(BaseModel):
    file_path: str = Field(description="O caminho do arquivo, relativo ao workspace.")
    content: str = Field(description="O conteúdo a ser escrito no arquivo.")
    overwrite: bool = Field(default=False, description="Se deve sobrescrever o arquivo.")

    @validator("file_path")
    def validate_path_is_safe(cls, v: str) -> str:
        absolute_path = (WORKSPACE_ROOT / v).resolve()
        try:
            absolute_path.relative_to(WORKSPACE_ROOT)
            return v
        except ValueError:
            raise ValueError(f"Acesso negado. O caminho '{v}' está fora do diretório permitido.")


@tool(args_schema=WriteFileInput)
def write_file(file_path: str, content: str, overwrite: bool = False) -> str:
    """Escreve conteúdo em um arquivo dentro do workspace seguro."""
    try:
        target_path = (WORKSPACE_ROOT / file_path).resolve()
        target_path.relative_to(WORKSPACE_ROOT)  # Re-valida para segurança

        if target_path.suffix not in ALLOWED_EXTENSIONS:
            return f"Erro: Extensão de arquivo não permitida. Permitidas: {', '.join(ALLOWED_EXTENSIONS)}"
        if len(content.encode("utf-8")) > MAX_FILE_SIZE:
            return f"Erro: Conteúdo excede o tamanho máximo de {MAX_FILE_SIZE} bytes."
        if target_path.exists() and not overwrite:
            return f"Erro: O arquivo '{file_path}' já existe. Use overwrite=True."

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        return f"Arquivo '{file_path}' salvo com sucesso."
    except ValueError as e:
        return f"Erro de validação: {e}"
    except Exception as e:
        return f"Erro inesperado: {e}"


# ... (outras ferramentas permanecem as mesmas) ...

@tool
def read_file(file_path: str) -> str:
    """Lê o conteúdo de um arquivo no projeto."""
    return filesystem_manager.read_file(file_path)


@tool
def list_directory(path: str = ".") -> str:
    """Lista arquivos e pastas no workspace."""
    return filesystem_manager.list_directory(path)


@tool
def recall_experiences(query: str) -> str:
    """Busca na memória por experiências passadas relevantes."""
    experiences = memory_core.recall(query=query, n_results=3)
    return json.dumps(experiences, indent=2, ensure_ascii=False)


@tool
def analyze_memory_for_failures(last_n_experiences: int = 20) -> str:
    """Examina as N experiências mais recentes para identificar padrões de falhas."""
    experiences = memory_core.recall(query="falha", n_results=last_n_experiences)
    failures = [exp for exp in experiences if exp.get("metadata", {}).get("type") == "action_failure"]
    if not failures:
        return "Análise concluída. Nenhuma falha significativa encontrada."
    summary = f"Análise de {len(failures)} falhas recentes:\n"
    for fail in failures:
        tool_used = fail.get("metadata", {}).get("tool_used", "N/A")
        error = fail.get("content", "Erro desconhecido")
        summary += f"- Ferramenta '{tool_used}' falhou com o erro: {error}\n"
    return summary


# --- Sprint 8: Ferramentas de Memória Semântica (Grafo de Conhecimento) ---

@tool
def query_knowledge_graph(query: str) -> str:
    """
    Consulta o grafo de conhecimento semântico para obter informações estruturadas.

    Use esta ferramenta para:
    - Encontrar conceitos relacionados
    - Descobrir padrões e conexões entre entidades
    - Acessar conhecimento consolidado de experiências passadas

    O grafo contém entidades (Concept, Entity, Tool, Error, etc) e seus relacionamentos.

    Exemplo: "Quais ferramentas estão relacionadas a erros de timeout?"
    """
    try:
        from app.core.knowledge_graph_manager import knowledge_graph_manager

        result = knowledge_graph_manager.semantic_search(query, limit=5)

        if not result:
            return "Nenhum conhecimento relevante encontrado no grafo."

        response = f"Conhecimento encontrado ({len(result)} resultados):\n\n"
        for item in result:
            response += f"- {item.get('summary', item)}\n"

        return response

    except Exception as e:
        return f"Erro ao consultar grafo de conhecimento: {e}"


@tool
def find_related_concepts(concept: str, max_depth: int = 2) -> str:
    """
    Encontra conceitos relacionados a partir de um conceito inicial.

    Explora o grafo de conhecimento para descobrir conexões e relacionamentos.

    Args:
        concept: Conceito inicial (ex: "Python", "erro de timeout", "API")
        max_depth: Profundidade máxima da busca (padrão: 2)

    Retorna conceitos conectados e seus relacionamentos.
    """
    try:
        # Consulta Neo4j para encontrar conceitos relacionados
        query = """
        MATCH path = (c:Concept {name: $concept})-[*1..%d]-(related)
        RETURN related.name as concept,
               type(last(relationships(path))) as relationship,
               length(path) as distance
        ORDER BY distance
        LIMIT 10
        """ % max_depth

        results = graph_db.query(query, {"concept": concept})

        if not results:
            return f"Nenhum conceito relacionado encontrado para '{concept}'."

        response = f"Conceitos relacionados a '{concept}':\n\n"
        for row in results:
            response += f"- {row['concept']} (relação: {row['relationship']}, distância: {row['distance']})\n"

        return response

    except Exception as e:
        logger.error(f"Erro ao buscar conceitos relacionados: {e}", exc_info=True)
        return f"Erro ao buscar conceitos relacionados: {e}"


@tool
def get_entity_details(entity_name: str) -> str:
    """
    Obtém detalhes completos sobre uma entidade no grafo de conhecimento.

    Args:
        entity_name: Nome da entidade (ferramenta, conceito, erro, etc)

    Retorna:
        - Propriedades da entidade
        - Relacionamentos com outras entidades
        - Contexto e metadados
    """
    try:
        query = """
        MATCH (e)
        WHERE e.name = $entity_name OR e.id = $entity_name
        OPTIONAL MATCH (e)-[r]->(related)
        RETURN e as entity,
               collect({type: type(r), target: related.name}) as relationships
        LIMIT 1
        """

        results = graph_db.query(query, {"entity_name": entity_name})

        if not results or not results[0]["entity"]:
            return f"Entidade '{entity_name}' não encontrada no grafo."

        entity = results[0]["entity"]
        relationships = results[0]["relationships"]

        response = f"Detalhes da entidade '{entity_name}':\n\n"
        response += "Propriedades:\n"
        for key, value in entity.items():
            if key not in ["id", "elementId"]:
                response += f"  - {key}: {value}\n"

        if relationships and relationships[0]:
            response += "\nRelacionamentos:\n"
            for rel in relationships[:10]:  # Limita a 10
                if rel.get("target"):
                    response += f"  - {rel['type']} → {rel['target']}\n"

        return response

    except Exception as e:
        logger.error(f"Erro ao obter detalhes da entidade: {e}", exc_info=True)
        return f"Erro ao obter detalhes: {e}"


# --- Sprint 3: Ferramentas de Contexto Ambiental ---

@tool
def get_current_datetime() -> str:
    """Retorna a data e hora atual."""
    ctx = context_manager.get_current_context()
    return json.dumps(ctx.datetime_info, indent=2, ensure_ascii=False)


@tool
def get_system_info() -> str:
    """Retorna informações sobre o sistema operacional e ambiente."""
    ctx = context_manager.get_current_context()
    return json.dumps({
        "system": ctx.system_info,
        "environment": ctx.environment
    }, indent=2, ensure_ascii=False)


@tool
def search_web(query: str, max_results: int = 3) -> str:
    """
    Busca informações na web usando Tavily.
    Útil para obter informações atualizadas e contexto externo.
    """
    result = context_manager.search_web(query, max_results=max_results)
    return json.dumps(result.model_dump(), indent=2, ensure_ascii=False)


@tool
def get_enriched_context(query: str = "", include_web: bool = False) -> str:
    """
    Retorna contexto completo: data/hora, sistema e opcionalmente busca web.
    Use quando precisar de contexto ambiental completo para tomar decisões.
    """
    ctx = context_manager.get_enriched_context(
        query=query if query else None,
        include_web_search=include_web,
        max_web_results=3
    )
    return json.dumps(ctx, indent=2, ensure_ascii=False)


# --- Sprint 4: Sandbox Python Seguro ---

@tool
def execute_python_code(code: str) -> str:
    """
    Executa código Python de forma segura em um sandbox isolado.

    O sandbox tem as seguintes restrições:
    - Sem acesso ao filesystem
    - Sem acesso à network
    - Imports limitados (math, random, datetime, json, re, collections, itertools, functools, statistics)
    - Timeout de 5 segundos
    - Output limitado a 10000 caracteres

    Útil para: cálculos, processamento de dados, testes de lógica.

    Exemplo de uso:
    code = '''
result = sum([1, 2, 3, 4, 5])
print(f"A soma é: {result}")
'''
    """
    try:
        result = python_sandbox.execute(code)

        if result.success:
            response = {
                "success": True,
                "output": result.output,
                "execution_time": result.execution_time,
                "variables": {k: str(v) for k, v in (result.variables or {}).items()}
            }
        else:
            response = {
                "success": False,
                "error": result.error,
                "output": result.output,
                "execution_time": result.execution_time
            }

        return json.dumps(response, indent=2, ensure_ascii=False)

    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Erro inesperado: {str(e)}",
            "output": ""
        }, indent=2, ensure_ascii=False)


@tool
def execute_python_expression(expression: str) -> str:
    """
    Avalia uma expressão Python e retorna o resultado.

    Mais simples que execute_python_code, útil para cálculos rápidos.

    Exemplos:
    - "2 + 2" -> 4
    - "sum([1,2,3,4,5])" -> 15
    - "[x**2 for x in range(5)]" -> [0, 1, 4, 9, 16]
    """
    try:
        result = python_sandbox.execute_expression(expression)

        if result.success:
            return result.output
        else:
            return f"Erro: {result.error}"

    except Exception as e:
        return f"Erro inesperado: {str(e)}"


# --- Fábrica de Ferramentas ---

unified_tools: List[BaseTool] = [
    write_file,
    read_file,
    list_directory,
    recall_experiences,
    query_knowledge_graph,  # Sprint 8: Consulta grafo de conhecimento
    find_related_concepts,  # Sprint 8: Busca conceitos relacionados
    get_entity_details,  # Sprint 8: Detalhes de entidades
    get_current_datetime,
    get_system_info,
    search_web,
    get_enriched_context,
    execute_python_code,
    execute_python_expression
]

meta_agent_tools: List[BaseTool] = [
    analyze_memory_for_failures,
    recall_experiences,
    query_knowledge_graph,  # Sprint 8: Meta-agente pode consultar conhecimento consolidado
    get_current_datetime
]

# Sprint 5: Ferramentas para Agente Reflexion (inclui ferramentas defeituosas para treinamento)
reflexion_tools: List[BaseTool] = unified_tools + get_faulty_tools()


def get_tools_for_agent(agent_type: AgentType) -> List[BaseTool]:
    """Retorna a lista de ferramentas apropriada para o tipo de agente."""
    if agent_type == AgentType.META_AGENT:
        return meta_agent_tools
    elif agent_type == AgentType.REFLEXION_AGENT:
        return reflexion_tools
    return unified_tools


# ==================== SPRINT 6: REGISTRO NO ACTION MODULE ====================

def _register_all_tools_in_action_module():
    """
    Registra todas as ferramentas existentes no Action Module para
    gerenciamento centralizado e telemetria.
    """
    # Ferramentas de filesystem
    action_registry.register(
        write_file,
        category=ToolCategory.FILESYSTEM,
        permission_level=PermissionLevel.WRITE,
        rate_limit_per_minute=30
    )
    action_registry.register(
        read_file,
        category=ToolCategory.FILESYSTEM,
        permission_level=PermissionLevel.READ_ONLY
    )
    action_registry.register(
        list_directory,
        category=ToolCategory.FILESYSTEM,
        permission_level=PermissionLevel.READ_ONLY
    )

    # Ferramentas de memória
    action_registry.register(
        recall_experiences,
        category=ToolCategory.DATABASE,
        permission_level=PermissionLevel.READ_ONLY,
        tags=["memory", "episodic"]
    )
    action_registry.register(
        analyze_memory_for_failures,
        category=ToolCategory.DATABASE,
        permission_level=PermissionLevel.READ_ONLY,
        tags=["memory", "analysis", "meta"]
    )

    # Ferramentas de memória semântica (Sprint 8)
    action_registry.register(
        query_knowledge_graph,
        category=ToolCategory.DATABASE,
        permission_level=PermissionLevel.READ_ONLY,
        tags=["memory", "semantic", "knowledge", "graph"]
    )
    action_registry.register(
        find_related_concepts,
        category=ToolCategory.DATABASE,
        permission_level=PermissionLevel.READ_ONLY,
        tags=["memory", "semantic", "concepts", "relationships"]
    )
    action_registry.register(
        get_entity_details,
        category=ToolCategory.DATABASE,
        permission_level=PermissionLevel.READ_ONLY,
        tags=["memory", "semantic", "entities"]
    )

    # Ferramentas de contexto ambiental (Sprint 3)
    action_registry.register(
        get_current_datetime,
        category=ToolCategory.SYSTEM,
        permission_level=PermissionLevel.READ_ONLY,
        tags=["context", "time"]
    )
    action_registry.register(
        get_system_info,
        category=ToolCategory.SYSTEM,
        permission_level=PermissionLevel.READ_ONLY,
        tags=["context", "system"]
    )
    action_registry.register(
        search_web,
        category=ToolCategory.WEB,
        permission_level=PermissionLevel.SAFE,
        rate_limit_per_minute=20,
        tags=["context", "search", "external"]
    )
    action_registry.register(
        get_enriched_context,
        category=ToolCategory.WEB,
        permission_level=PermissionLevel.SAFE,
        rate_limit_per_minute=10,
        tags=["context", "enriched"]
    )

    # Ferramentas de sandbox Python (Sprint 4)
    action_registry.register(
        execute_python_code,
        category=ToolCategory.COMPUTATION,
        permission_level=PermissionLevel.SAFE,
        rate_limit_per_minute=30,
        tags=["python", "sandbox", "computation"]
    )
    action_registry.register(
        execute_python_expression,
        category=ToolCategory.COMPUTATION,
        permission_level=PermissionLevel.SAFE,
        rate_limit_per_minute=60,
        tags=["python", "sandbox", "computation"]
    )

    # Ferramentas defeituosas (Sprint 5) - apenas para Reflexion
    for faulty_tool in get_faulty_tools():
        action_registry.register(
            faulty_tool,
            category=ToolCategory.CUSTOM,
            permission_level=PermissionLevel.SAFE,
            tags=["faulty", "training", "reflexion"]
        )


# Executa registro automático ao importar o módulo
_register_all_tools_in_action_module()
