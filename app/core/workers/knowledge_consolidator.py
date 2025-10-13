import asyncio
import json
import structlog

from app.config import settings
from app.core.agents.agent_manager import agent_manager, AgentType
from app.core.memory.memory_core import memory_core
from app.db.graph import graph_db
from app.models.schemas import Experience

logger = structlog.get_logger(__name__)


class KnowledgeConsolidator:
    """
    Este worker transforma experiências brutas da Memória Episódica (Qdrant)
    em conhecimento estruturado e canonizado na Memória Semântica (Neo4j),
    usando uma ontologia dinâmica.
    """

    def __init__(self):
        self.is_running = False
        self._task = None
        self.canonical_form_cache = {}  # Cache em memória para acelerar a canonização

    async def start(self):
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._consolidation_cycle())
            logger.info("Knowledge Consolidator worker iniciado.")

    async def stop(self):
        if self.is_running and self._task:
            self.is_running = False
            self.canonical_form_cache.clear()
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("Knowledge Consolidator worker parado.")

    async def _consolidation_cycle(self):
        while self.is_running:
            try:
                logger.info("Iniciando ciclo de consolidação de conhecimento.")
                await self.run_consolidation()
                logger.info("Ciclo de consolidação de conhecimento concluído.")
            except Exception as e:
                logger.error("Erro durante o ciclo de consolidação.", exc_info=e)

            self.canonical_form_cache.clear()
            await asyncio.sleep(settings.KNOWLEDGE_CONSOLIDATOR_INTERVAL_SECONDS)

    async def run_consolidation(self):
        unprocessed_experiences = await self._collect_unprocessed_experiences()
        if not unprocessed_experiences:
            logger.info("Nenhuma nova experiência para consolidar.")
            return

        structured_knowledge_list = await self._process_experiences(unprocessed_experiences)
        if not structured_knowledge_list:
            logger.info("Nenhum conhecimento estruturado foi extraído.")
            return

        await self._persist_knowledge(structured_knowledge_list)
        await self._mark_experiences_as_processed(unprocessed_experiences)

    async def _get_canonical_form(self, term: str, session) -> str:
        if not term or not isinstance(term, str):
            return None
        term_lower = term.lower()
        if term_lower in self.canonical_form_cache:
            return self.canonical_form_cache[term_lower]

        query = "MATCH (s:Entity {name: $term})-[:IS_SYNONYM_OF]->(c:Entity) RETURN c.name as canonical_name"
        result = await session.run(query, term=term_lower)
        record = await result.single()
        if record and record["canonical_name"]:
            canonical_form = record["canonical_name"]
            self.canonical_form_cache[term_lower] = canonical_form
            return canonical_form

        prompt = f'Qual é a forma canônica (singular, em inglês, se aplicável) para o termo "{term_lower}"? Responda apenas com o termo canônico.'
        response = await agent_manager.arun_agent(question=prompt, request=None, agent_type=AgentType.META_AGENT)

        canonical_form = term_lower
        if response and response.get("answer"):
            llm_canon = response["answer"].strip().lower()
            if llm_canon:
                canonical_form = llm_canon

        if canonical_form != term_lower:
            await graph_db.merge_relationship(tx=session, source_label="Entity", source_name=term_lower,
                                              target_label="Entity", target_name=canonical_form,
                                              rel_type="IS_SYNONYM_OF")
            logger.info(f'Novo sinônimo aprendido: "{term_lower}" -> "{canonical_form}"')

        self.canonical_form_cache[term_lower] = canonical_form
        return canonical_form

    async def _persist_knowledge(self, structured_knowledge_list):
        logger.info(f"Persistindo {len(structured_knowledge_list)} grafos de conhecimento com ontologia dinâmica.")
        driver = await graph_db.get_driver()
        async with driver.session() as session:
            for knowledge_graph in structured_knowledge_list:
                if not isinstance(knowledge_graph, dict) or "nodes" not in knowledge_graph:
                    continue

                async with session.begin_transaction() as tx:
                    try:
                        node_map = {}
                        # 1. Criar/Mesclar Nós
                        for i, node_data in enumerate(knowledge_graph.get("nodes", [])):
                            label = node_data.get("label", "Entity")
                            name = node_data.get("name")
                            if not name:
                                continue

                            canonical_name = await self._get_canonical_form(name, tx)
                            if not canonical_name:
                                continue

                            node_id = await graph_db.merge_node(tx, label=label, name=canonical_name)
                            node_map[i] = node_id

                        # 2. Criar/Mesclar Relacionamentos
                        for rel_data in knowledge_graph.get("relationships", []):
                            rel_type = rel_data.get("type")
                            source_idx, target_idx = rel_data.get("source_index"), rel_data.get("target_index")

                            if not all([rel_type, source_idx is not None, target_idx is not None]):
                                continue

                            source_id = node_map.get(source_idx)
                            target_id = node_map.get(target_idx)

                            if source_id and target_id:
                                await graph_db.merge_relationship(tx, source_id=source_id, target_id=target_id,
                                                                  rel_type=rel_type)

                        await tx.commit()
                    except Exception as e:
                        logger.error("Erro ao persistir grafo. Revertendo transação.", exc_info=e)
                        await tx.rollback()

    def _create_extraction_prompt(self, experience: Experience) -> str:
        return f"""Você é um Arquiteto de Grafo de Conhecimento. Sua tarefa é analisar a seguinte 'experiência' de um agente de IA e convertê-la em um grafo estruturado em JSON.

        **Diretriz Principal:** Seja semanticamente rico e preciso nos tipos de relacionamento. Se um relacionamento como 'SUGGESTS' ou 'CAUSES' descreve melhor a conexão entre duas entidades do que um genérico 'RELATES_TO', use-o. O sistema aprenderá e registrará automaticamente qualquer novo tipo de relacionamento que você criar.

        **Esquema de Saída (JSON):**
        - `nodes`: uma lista de nós. Cada nó deve ter `label` e `name`.
        - `relationships`: uma lista de relacionamentos. Cada rel deve ter `source_index`, `target_index`, e `type` (um verbo em maiúsculas, como `USES_SKILL`).

        **Experiência para Análise:**
        - **Tipo:** {experience.type}
        - **Conteúdo:** {experience.content}
        - **Metadados:** {experience.metadata}

        **Instruções:**
        1.  **Abstraia a Tarefa:** Generalize a intenção para um nó `Task`.
        2.  **Analise o Sucesso:** Se bem-sucedida, crie um `Workflow` com `Steps` e `Skills`.
        3.  **Analise a Falha:** Se falhou, extraia o insight para um nó `Reflection` e conecte-o à causa do problema.

        Responda APENAS com o objeto JSON final.
        """

    async def _collect_unprocessed_experiences(self):
        return await memory_core.asearch(
            query_text="",
            filters={"must_not": [{"key": "metadata.consolidated", "match": {"value": True}}]},
            limit=25
        )

    async def _process_experiences(self, experiences):
        tasks = [self._extract_knowledge_from_experience(exp) for exp in experiences]
        results = await asyncio.gather(*tasks)
        return [res for res in results if res]

    async def _extract_knowledge_from_experience(self, experience: Experience):
        prompt = self._create_extraction_prompt(experience)
        try:
            response = await agent_manager.arun_agent(question=prompt, request=None, agent_type=AgentType.META_AGENT)
            if not response or "answer" not in response:
                return None
            json_string = response["answer"].strip().replace("```json", "").replace("```", "")
            return json.loads(json_string)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Falha ao extrair/parsear conhecimento da experiência.", exc_info=e)
            return None

    async def _mark_experiences_as_processed(self, experiences):
        logger.info(f"Marcando {len(experiences)} experiências como processadas.")
        for exp in experiences:
            if exp.metadata is None: exp.metadata = {}
            exp.metadata['consolidated'] = True
            await memory_core.amemorize(exp)


knowledge_consolidator = KnowledgeConsolidator()
