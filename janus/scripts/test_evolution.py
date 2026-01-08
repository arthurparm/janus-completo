
import asyncio
import logging
from app.core.evolution.evolution_manager import EvolutionManager
from app.services.llm_service import LLMService
from app.repositories.llm_repository import LLMRepository
from app.services.tool_service import get_tool_service
from app.repositories.tool_repository import ToolRepository

# Setup Logging
logging.basicConfig(level=logging.INFO)

async def test_evolution():
    print(">>> Initializing Services...")
    llm_repo = LLMRepository()
    llm_service = LLMService(llm_repo)
    tool_repo = ToolRepository()
    tool_service = ToolService(tool_repo)
    
    manager = EvolutionManager(llm_service, tool_service)
    
    request = "Listar filas do RabbitMQ retornando nome e total de mensagens"
    print(f">>> Requesting Evolution: {request}")
    
    try:
        result = await manager.evolve_tool(request)
        print("\n>>> SUCCESS! Tool Evolved:")
        print(result)
    except Exception as e:
        print(f"\n>>> FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_evolution())
