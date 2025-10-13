import json
import logging
from pathlib import Path
from typing import List

from langchain.tools import tool, BaseTool
from pydantic import BaseModel, Field, validator

from app.core.infrastructure import filesystem_manager
from app.core.tools.action_module import (
    action_registry,
    ToolCategory,
    PermissionLevel
)
from app.core.infrastructure.context_manager import context_manager
from app.core.infrastructure.enums import AgentType
from app.core.tools.faulty_tools import get_faulty_tools
from app.core.memory.memory_core import memory_core
from app.core.infrastructure.python_sandbox import python_sandbox
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


@tool  # Removido args_schema temporariamente para permitir que o wrapper funcione
def write_file(file_path: str, content: str, overwrite: bool = False) -> str:
    """
    Escreve conteúdo em um arquivo dentro do workspace seguro (/app/workspace).

    IMPORTANTE: Você DEVE fornecer os três parâmetros:
    - file_path: Caminho relativo ao workspace (ex: 'main.py', 'src/app.py', 'requirements.txt')
    - content: Conteúdo COMPLETO do arquivo a ser escrito (STRING obrigatória)
    - overwrite: Se True, sobrescreve arquivo existente. Se False e arquivo existe, retorna erro.

    Returns:
        Mensagem de sucesso ou erro

    Exemplo de uso correto:
        write_file(file_path="requirements.txt", content="flask==2.0.0\\nrequests==2.28.0\\nfastapi==0.104.0", overwrite=False)
        write_file(file_path="main.py", content="from flask import Flask\\n\\napp = Flask(__name__)\\n\\n@app.route('/')\\ndef home():\\n    return 'Hello World'", overwrite=False)
    """
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


@tool
def read_file(file_path: str) -> str:
    """
    Lê o conteúdo completo de um arquivo do sistema de arquivos.

    Use esta ferramenta para:
    - Ler código-fonte, arquivos de configuração, logs
    - Examinar conteúdo de arquivos de dados (JSON, CSV, TXT)
    - Verificar conteúdo antes de modificar

    Args:
        file_path: Caminho do arquivo a ser lido (ex: 'src/main.py', 'config.json')

    Returns:
        Conteúdo do arquivo ou mensagem de erro se não encontrado
    """
    return filesystem_manager.read_file(file_path)


class ListDirectoryInput(BaseModel):
    path: str = Field(default="/app/workspace",
                      description="Caminho do diretório a ser listado, relativo ao workspace (/app/workspace).")

    @validator("path")
    def validate_path_is_safe(cls, v: str) -> str:
        # Se o path for ".", converte para o workspace
        if v == ".":
            v = "/app/workspace"

        # Resolve o path absoluto
        if not v.startswith("/app/workspace"):
            v = f"/app/workspace/{v.lstrip('/')}"

        absolute_path = Path(v).resolve()
        try:
            absolute_path.relative_to(WORKSPACE_ROOT)
            return str(absolute_path)
        except ValueError:
            raise ValueError(f"Acesso negado. O caminho '{v}' está fora do diretório permitido (/app/workspace).")


@tool(args_schema=ListDirectoryInput)
def list_directory(path: str = "/app/workspace") -> str:
    """
    Lista todos os arquivos e diretórios em um caminho específico dentro do workspace seguro.

    Use esta ferramenta para:
    - Explorar a estrutura de diretórios do projeto dentro de /app/workspace
    - Encontrar arquivos disponíveis antes de ler
    - Verificar se um arquivo ou pasta existe

    Args:
        path: Caminho do diretório dentro do workspace (padrão: "/app/workspace" para raiz do workspace)

    Returns:
        Lista formatada de arquivos e diretórios

    Exemplo de uso:
        list_directory(path="/app/workspace")
    """
    logger.info(f"[LIST_DIRECTORY] Chamada recebida - path={repr(path)}, type={type(path)}")

    try:
        # Garante que o path é seguro
        if path == ".":
            path = "/app/workspace"

        if not path.startswith("/app/workspace"):
            path = f"/app/workspace/{path.lstrip('/')}"

        logger.info(f"[LIST_DIRECTORY] Path processado: {path}")

        resolved_path = Path(path).resolve()
        logger.info(f"[LIST_DIRECTORY] Path resolvido: {resolved_path}")

        resolved_path.relative_to(WORKSPACE_ROOT)  # Valida segurança

        if not resolved_path.exists():
            logger.warning(f"[LIST_DIRECTORY] Diretório não existe: {resolved_path}")
            return f"Erro: O diretório '{path}' não existe."

        if not resolved_path.is_dir():
            return f"Erro: '{path}' não é um diretório."

        # Lista o conteúdo
        items = []
        for item in sorted(resolved_path.iterdir()):
            item_type = "DIR" if item.is_dir() else "FILE"
            items.append(f"[{item_type}] {item.name}")

        if not items:
            return f"O diretório '{path}' está vazio."

        logger.info(f"[LIST_DIRECTORY] Sucesso - {len(items)} itens encontrados")
        return f"Conteúdo de '{path}':\n" + "\n".join(items)

    except ValueError as e:
        logger.error(f"[LIST_DIRECTORY] Erro de validação: {e}")
        return f"Erro de validação: {e}"
    except Exception as e:
        logger.error(f"[LIST_DIRECTORY] Erro: {e}", exc_info=True)
        return f"Erro ao listar diretório: {e}"


@tool
async def recall_experiences(query: str) -> str:
    """
    Busca na memória episódica por experiências passadas relevantes usando similaridade semântica.

    Use esta ferramenta para:
    - Lembrar de ações similares executadas anteriormente
    - Recuperar contexto de tarefas passadas
    - Aprender com sucessos e falhas anteriores
    - Encontrar exemplos de como resolver um problema

    Args:
        query: Descrição do que você quer lembrar (ex: "como escrever arquivos", "erros com API")

    Returns:
        JSON com até 3 experiências mais relevantes encontradas
    """
    try:
        experiences = await memory_core.arecall(query=query, n_results=3)
        return json.dumps(experiences, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error recalling experiences: {e}", exc_info=True)
        return f"Erro ao buscar experiências na memória: {e}"


@tool
async def analyze_memory_for_failures(last_n_experiences: int = 100) -> str:
    """
    Analisa as N experiências mais recentes armazenadas na memória episódica
    para identificar padrões de falhas, erros recorrentes e problemas do sistema.

    Use esta ferramenta quando precisar:
    - Detectar padrões de falhas recorrentes
    - Identificar ferramentas problemáticas
    - Analisar erros recentes do sistema
    - Fazer diagnóstico de problemas

    Args:
        last_n_experiences: Número de experiências a analisar (padrão: 100)

    Returns:
        Resumo das falhas encontradas ou mensagem indicando ausência de falhas.
    """
    try:
        experiences = await memory_core.arecall(query="falha erro error exception", n_results=last_n_experiences)
        failures = [exp for exp in experiences if exp.get("metadata", {}).get("type") == "action_failure"]
        if not failures:
            return f"Análise concluída. Nenhuma falha significativa encontrada nas últimas {last_n_experiences} experiências."

        summary = f"Análise de {len(failures)} falhas encontradas nas últimas {last_n_experiences} experiências:\n\n"

        # Agrupa falhas por ferramenta
        failures_by_tool = {}
        for fail in failures:
            tool_used = fail.get("metadata", {}).get("tool_used", "N/A")
            if tool_used not in failures_by_tool:
                failures_by_tool[tool_used] = []
            failures_by_tool[tool_used].append(fail)

        # Gera resumo por ferramenta
        for tool, tool_failures in sorted(failures_by_tool.items(), key=lambda x: len(x[1]), reverse=True):
            summary += f"\n🔴 Ferramenta '{tool}' - {len(tool_failures)} falha(s):\n"
            for fail in tool_failures[:3]:  # Mostra até 3 exemplos
                error = fail.get("content", "Erro desconhecido")[:150]
                timestamp = fail.get("metadata", {}).get("timestamp", "N/A")
                summary += f"  - [{timestamp}] {error}\n"
            if len(tool_failures) > 3:
                summary += f"  ... e mais {len(tool_failures) - 3} falha(s)\n"

        return summary
    except Exception as e:
        logger.error(f"Error analyzing memory for failures: {e}", exc_info=True)
        return f"Erro ao analisar memória para falhas: {e}"


# --- Sprint 8: Ferramentas de Memória Semântica (Grafo de Conhecimento) ---

@tool
def query_knowledge_graph(query: str) -> str:
    """
    Consulta o grafo de conhecimento semântico (Neo4j) para obter informações estruturadas
    sobre conceitos, ferramentas, erros e relacionamentos consolidados de experiências passadas.

    Use esta ferramenta quando precisar:
    - Encontrar conceitos relacionados a uma tecnologia, ferramenta ou problema
    - Descobrir padrões e conexões entre entidades do sistema
    - Acessar conhecimento consolidado e estruturado
    - Investigar causas conhecidas de problemas recorrentes
    - Entender relacionamentos entre componentes do sistema

    O grafo contém nós de tipos: Concept, Tool, Error, Solution, Pattern, Technology
    E relacionamentos: USES, RELATES_TO, CAUSES, SOLVES, DEPENDS_ON, IMPLEMENTS

    Args:
        query: Consulta em linguagem natural (ex: "Quais ferramentas causam erros de timeout?")

    Returns:
        Resultados estruturados do grafo de conhecimento
    """
    try:
        from app.core.memory.knowledge_graph_manager import knowledge_graph_manager

        result = knowledge_graph_manager.semantic_search(query, limit=10)

        if not result:
            return f"Nenhum conhecimento relevante encontrado no grafo para a consulta: '{query}'"

        response = f"📊 Conhecimento encontrado no grafo ({len(result)} resultados):\n\n"
        for idx, item in enumerate(result, 1):
            response += f"{idx}. {item.get('summary', item)}\n"

        return response

    except Exception as e:
        logger.error(f"Erro ao consultar grafo de conhecimento: {e}", exc_info=True)
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
    """
    Retorna a data e hora atual do sistema com informações detalhadas.

    Use esta ferramenta para:
    - Saber a data/hora atual para timestamping
    - Verificar dia da semana, mês, ano
    - Obter informações temporais para contexto

    Returns:
        JSON com data, hora, timestamp, dia da semana, etc
    """
    ctx = context_manager.get_current_context()
    return json.dumps(ctx.datetime_info, indent=2, ensure_ascii=False)


@tool
def get_system_info() -> str:
    """
    Retorna informações detalhadas sobre o sistema operacional e ambiente de execução.

    Use esta ferramenta para:
    - Verificar plataforma (Windows, Linux, Mac)
    - Obter versão do Python
    - Consultar variáveis de ambiente
    - Adaptar comportamento ao sistema

    Returns:
        JSON com informações do sistema operacional e ambiente
    """
    ctx = context_manager.get_current_context()
    return json.dumps({
        "system": ctx.system_info,
        "environment": ctx.environment
    }, indent=2, ensure_ascii=False)


@tool
def search_web(query: str, max_results: int = 3) -> str:
    """
    Busca informações atualizadas na web usando Tavily Search API.

    Use esta ferramenta quando precisar:
    - Informações atualizadas sobre eventos recentes
    - Documentação técnica online
    - Verificar fatos ou dados atuais
    - Pesquisar soluções para problemas

    Args:
        query: Termo de busca (ex: "Python async best practices 2024")
        max_results: Número máximo de resultados (padrão: 3)

    Returns:
        JSON com resultados da busca web
    """
    result = context_manager.search_web(query, max_results=max_results)
    return json.dumps(result.model_dump(), indent=2, ensure_ascii=False)


@tool
def get_enriched_context(query: str = "", include_web: bool = False) -> str:
    """
    Retorna contexto ambiental completo: data/hora, sistema e opcionalmente busca web.

    Use esta ferramenta quando precisar:
    - Contexto completo do ambiente de execução
    - Combinar informações locais e web
    - Tomar decisões baseadas em contexto amplo

    Args:
        query: Consulta para busca web opcional
        include_web: Se True, inclui resultados de busca web

    Returns:
        JSON com contexto completo (datetime, system, environment, web results se solicitado)
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
