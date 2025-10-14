import asyncio
import logging
from typing import Dict, Any, List, Optional
import json  # Adicionado para json.dumps

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from fastapi import Depends  # Adicionado para DI

from app.core.llm.llm_manager import get_llm, ModelRole, ModelPriority
from app.core.memory.memory_core import get_memory_db, MemoryCore  # Usar o getter

logger = logging.getLogger(__name__)


# --- Ferramentas de Raciocínio (Exemplos) ---

@tool
async def search_memory(query: str, limit: int = 5) -> str:
    """
    Busca na memória episódica por experiências relevantes.

    Args:
        query: A consulta em linguagem natural.
        limit: Número máximo de resultados.

    Returns:
        Uma string JSON com as experiências encontradas.
    """
    try:
        memory_db = await get_memory_db()  # Obtém a instância via getter
        results = await memory_db.arecall(query=query, limit=limit)
        return json.dumps(results)
    except Exception as e:
        logger.error(f"Erro ao buscar na memória: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


class ReasoningSession:
    """
    Gerencia uma sessão de raciocínio para um agente.
    """

    def __init__(self, llm_manager_instance, tools: List[Any]):
        self.llm = llm_manager_instance.get_llm(role=ModelRole.REASONING, priority=ModelPriority.HIGH_QUALITY)
        self.tools = tools
        self.prompt = PromptTemplate.from_template(
            """Você é um assistente de raciocínio. Responda à pergunta: {input}""")
        self.agent_executor = create_react_agent(self.llm, self.tools, self.prompt)

    async def solve_question(self, question: str) -> str:
        try:
            result = await self.agent_executor.invoke({"input": question})
            return result["output"]
        except Exception as e:
            logger.error(f"Erro na sessão de raciocínio: {e}", exc_info=True)
            return f"Erro ao processar a pergunta: {e}"

# --- Funções Legadas (para compatibilidade, a serem refatoradas) ---

# Esta função global `solve_question` ainda está aqui para compatibilidade
# mas deve ser removida ou refatorada para usar DI.
# Por enquanto, ela não será mais importada globalmente.

# A importação de `get_all_tools` também precisa ser resolvida via DI
# from app.core.tools import get_all_tools

# O `llm_instance` também precisa ser injetado
# from app.core.llm.llm_manager import get_llm

# Removendo a função global `solve_question` para evitar dependências globais
# e forçar o uso de `ReasoningSession` com DI.

# Removendo a importação de `memory_core` que causava o erro.
# A ferramenta `search_memory` agora usa `get_memory_db()` diretamente.
