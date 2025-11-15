import asyncio
import json
import structlog

from app.config import settings
from app.services.agent_service import AgentService
from app.services.memory_service import MemoryService
from app.repositories.knowledge_repository import KnowledgeRepository
from app.models.schemas import Experience

logger = structlog.get_logger(__name__)

class KnowledgeConsolidator:
    """
    Este worker transforma experiências brutas em conhecimento estruturado.
    Recebe suas dependências via DI para ser totalmente testável e desacoplado.
    """

    def __init__(
            self,
            agent_service: AgentService,
            memory_service: MemoryService,
            knowledge_repo: KnowledgeRepository
    ):
        self._agent_service = agent_service
        self._memory_service = memory_service
        self._knowledge_repo = knowledge_repo
        self.is_running = False
        self._task = None
        self.canonical_form_cache = {}

    async def start(self):
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._consolidation_cycle())
            logger.info("Knowledge Consolidator worker iniciado.")

    async def stop(self):
        if self.is_running and self._task:
            self.is_running = False
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
        # Coleta experiências recentes (MVP): usa busca ampla
        try:
            unprocessed_experiences = await self._memory_service.recall_experiences(query="consolidate", limit=50)
        except Exception:
            unprocessed_experiences = []
        if not unprocessed_experiences:
            logger.info("Nenhuma nova experiência para consolidar.")
            return

        logger.info(f"Processando {len(unprocessed_experiences)} experiências...")
        seen = set()
        for exp in unprocessed_experiences:
            try:
                exp_id = str(exp.get("id") or exp.get("experience_id") or "")
                if exp_id and exp_id in seen:
                    continue
                seen.add(exp_id)
                content = str(exp.get("content") or "")
                concepts = self._extract_concepts(content)
                if concepts:
                    await self._knowledge_repo.merge_experience_mentions(exp, concepts)
            except Exception as e:
                logger.debug("Falha ao consolidar experiência", exc_info=e)

    def _extract_concepts(self, text: str) -> list:
        # Extrai termos significativos (MVP): palavras alfanuméricas com tamanho >= 4
        import re
        tokens = re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9_\.]{4,}", text or "")
        # Normaliza e remove stopwords simples
        stop = {"para","como","quando","onde","porque","isso","dessa","nesta","with","that","this","from","into","have","been"}
        canon = []
        for t in tokens:
            tt = t.strip().lower().strip("._")
            if not tt or tt in stop:
                continue
            canon.append(tt)
        # Top-N únicos preservando ordem
        seen = set()
        result = []
        for w in canon:
            if w in seen:
                continue
            seen.add(w)
            result.append(w)
            if len(result) >= 20:
                break
        return result

    # O restante da lógica interna (extração, persistência) seria mantido,
    # mas adaptado para usar self._agent_service, self._memory_service, self._knowledge_repo
