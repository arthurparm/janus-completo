from typing import List, Dict, Any, Optional
import structlog
from fastapi import Request

from app.repositories.knowledge_repository import KnowledgeRepository
from app.services.code_analysis_service import code_analysis_service
from app.core.workers.knowledge_consolidator import knowledge_consolidator

logger = structlog.get_logger(__name__)

CODEBASE_DIR = "/app"

class KnowledgeService:
    """
    Camada de serviço para o Grafo de Conhecimento.
    Orquestra a lógica de negócio, recebendo suas dependências via DI.
    """
    def __init__(self, repo: KnowledgeRepository):
        self._repo = repo

    async def get_stats(self) -> Dict[str, Any]:
        stats = await self._repo.get_node_and_relationship_stats()
        return {
            "total_nodes": sum(i.get("count", 0) for i in stats["nodes"]),
            "total_relationships": sum(i.get("count", 0) for i in stats["relationships"]),
            "node_types": stats["nodes"],
            "relationship_types": stats["relationships"],
        }

    async def get_code_entities(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        return await self._repo.find_code_entities(file_path)

    async def get_entity_details(self, entity_name: str) -> Optional[Dict[str, Any]]:
        details = await self._repo.find_entity_details(entity_name)
        if not details:
            return None
        return details

    async def trigger_consolidation(self, limit: int) -> Dict[str, Any]:
        await knowledge_consolidator.run_consolidation()
        return {"message": "Processo de consolidação disparado com sucesso."}

    async def index_codebase(self) -> Dict[str, Any]:
        logger.info(f"Iniciando orquestração de indexação da base de código em '{CODEBASE_DIR}'...")
        await self._repo.clear_code_entities()

        python_files = code_analysis_service.find_python_files(CODEBASE_DIR)
        total_files, total_funcs, total_classes, all_calls = 0, 0, 0, []

        for file_path in python_files:
            parser = code_analysis_service.parse_python_file(file_path)
            if parser:
                await self._repo.save_code_structure(parser)
                for call in parser.calls:
                    all_calls.append(
                        {"caller_name": call['caller'], "callee_name": call['callee'], "file_path": file_path})
                total_files += 1
                total_funcs += len(parser.functions)
                total_classes += len(parser.classes)

        await self._repo.bulk_merge_calls(all_calls)

        summary = f"Indexação concluída. {total_files} arquivos | {total_funcs} funções | {total_classes} classes | {len(all_calls)} chamadas internas criadas."
        return {"message": "Indexação da base de código concluída.", "summary": summary}

    async def clear_graph(self) -> int:
        return await self._repo.clear_all_data()

# Padrão de Injeção de Dependência: Getter para o serviço
def get_knowledge_service(request: Request) -> KnowledgeService:
    return request.app.state.knowledge_service
