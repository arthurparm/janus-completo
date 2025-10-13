from typing import List, Dict, Any, Optional
import structlog

from app.repositories.knowledge_repository import knowledge_repository
from app.services.code_analysis_service import code_analysis_service
from app.core.workers.knowledge_consolidator import knowledge_consolidator
from app.db.graph import graph_db  # Apenas para merge_node/rel, que poderiam ir para o repo

logger = structlog.get_logger(__name__)

CODEBASE_DIR = "/app"


class KnowledgeService:
    """
    Camada de serviço para o Grafo de Conhecimento.
    Orquestra a lógica de negócio, delegando o acesso a dados para o repositório.
    """

    async def get_stats(self) -> Dict[str, Any]:
        logger.info("Buscando estatísticas do grafo via serviço.")
        stats = await knowledge_repository.get_node_and_relationship_stats()
        return {
            "total_nodes": sum(i.get("count", 0) for i in stats["nodes"]),
            "total_relationships": sum(i.get("count", 0) for i in stats["relationships"]),
            "node_types": stats["nodes"],
            "relationship_types": stats["relationships"],
        }

    async def get_code_entities(self, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        logger.info("Buscando entidades de código via serviço.", file_path=file_path)
        return await knowledge_repository.find_code_entities(file_path)

    async def get_function_calls(self, function_name: Optional[str] = None) -> List[Dict[str, Any]]:
        logger.info("Buscando chamadas de função via serviço.", function_name=function_name)
        return await knowledge_repository.find_function_calls(function_name)

    async def get_entity_details(self, entity_name: str) -> Optional[Dict[str, Any]]:
        logger.info("Buscando detalhes de entidade via serviço.", entity_name=entity_name)
        details = await knowledge_repository.find_entity_details(entity_name)
        if not details:
            return None
        return details

    async def trigger_consolidation(self, limit: int) -> Dict[str, Any]:
        logger.info(f"Disparando consolidação de conhecimento para {limit} experiências via serviço.")
        await knowledge_consolidator.run_consolidation()
        return {"message": "Processo de consolidação disparado com sucesso."}

    async def index_codebase(self) -> Dict[str, Any]:
        logger.info(f"Iniciando orquestração de indexação da base de código em '{CODEBASE_DIR}'...")

        await knowledge_repository.clear_code_entities()
        logger.info("Entidades de código antigas removidas.")

        python_files = code_analysis_service.find_python_files(CODEBASE_DIR)
        total_files, total_funcs, total_classes = 0, 0, 0
        all_calls = []

        logger.info(f"Analisando {len(python_files)} arquivos...")
        for file_path in python_files:
            parser = code_analysis_service.parse_python_file(file_path)
            if parser:
                await self._create_code_entities_from_parser(parser)
                for call in parser.calls:
                    all_calls.append(
                        {"caller_name": call['caller'], "callee_name": call['callee'], "file_path": file_path})
                total_files += 1
                total_funcs += len(parser.functions)
                total_classes += len(parser.classes)

        logger.info(f"Mesclando {len(all_calls)} relações de chamada...")
        await knowledge_repository.bulk_merge_calls(all_calls)

        summary = f"Indexação concluída. {total_files} arquivos | {total_funcs} funções | {total_classes} classes | {len(all_calls)} chamadas internas criadas."
        logger.info(summary)
        return {"message": "Indexação da base de código concluída.", "summary": summary}

    async def _create_code_entities_from_parser(self, parser):
        file_path = parser.file_path
        driver = await graph_db.get_driver()
        async with driver.session() as session:
            async with session.begin_transaction() as tx:
                file_id = await graph_db.merge_node(tx, label="File:CodeFile", name=file_path)
                for func in parser.functions:
                    func_id = await graph_db.merge_node(tx, label="Function:CodeFunction", name=func['name'])
                    await graph_db.merge_relationship(tx, source_id=file_id, target_id=func_id, rel_type="CONTAINS")
                for cls in parser.classes:
                    cls_id = await graph_db.merge_node(tx, label="Class:CodeClass", name=cls['name'])
                    await graph_db.merge_relationship(tx, source_id=file_id, target_id=cls_id, rel_type="CONTAINS")

    async def clear_graph(self) -> int:
        logger.warning("Limpando todo o grafo de conhecimento via serviço.")
        return await knowledge_repository.clear_all_data()


knowledge_service = KnowledgeService()
