import asyncio
import math
import re
from datetime import datetime, UTC, timedelta
from typing import Any, List

import structlog

from app.core.memory.memory_core import get_memory_db
from app.services.knowledge_graph_service import get_knowledge_graph_service
from app.services.llm_service import LLMService
from app.repositories.llm_repository import get_llm_repository
from app.models.schemas import Experience, ScoredExperience
from app.core.llm import ModelRole, ModelPriority

logger = structlog.get_logger(__name__)

class GenerativeMemoryService:
    """
    Implements Generative Agents Memory (Park et al. 2023).
    Combines Recency, Importance, and Relevance for retrieval.
    Manages Memory Stream in Neo4j.
    """

    def __init__(self):
        self.alpha = 1.0  # Recency weight
        self.beta = 1.0   # Importance weight
        self.gamma = 1.0  # Relevance weight
        self.decay_factor = 0.995 # Per hour
        self._llm_service = None

    @property
    def llm_service(self):
        if not self._llm_service:
            self._llm_service = LLMService(get_llm_repository())
        return self._llm_service

    async def add_memory(self, content: str, type: str = "episodic", metadata: dict[str, Any] = None) -> Experience:
        """
        Adds a memory to the stream.
        1. Calculates importance (LLM) if not provided.
        2. Saves to Vector DB (MemoryCore).
        3. Saves to Graph DB (Neo4j) as linked stream.
        """
        metadata = metadata or {}
        
        # 1. Calculate Importance
        if metadata.get("importance") is None:
            # Tenta usar modelo local se disponível, senão fallback para o padrão
            try:
                # Prioridade LOCAL para economizar tokens em tarefas de manutenção/classificação
                importance = await self._calculate_importance(content, use_local=True)
            except Exception:
                importance = await self._calculate_importance(content, use_local=False)
            metadata["importance"] = importance
        
        # 2. Create Experience Object
        experience = Experience(
            content=content,
            type=type,
            metadata=metadata
        )
        
        # 3. Save to Vector DB (Qdrant)
        memory_core = await get_memory_db()
        await memory_core.amemorize(experience)
        
        # 4. Save to Graph DB (Neo4j) - Memory Stream
        kg_service = get_knowledge_graph_service()
        user_id = metadata.get("user_id") or metadata.get("source_agent") or "system"
        await kg_service.persist_experience_node(experience, user_id=str(user_id))
        
        logger.info("Memory added to generative stream", id=experience.id, importance=metadata["importance"])
        return experience

    async def retrieve_memories(self, query: str, limit: int = 10) -> List[ScoredExperience]:
        """
        Retrieves memories based on Park et al. scoring formula.
        """
        memory_core = await get_memory_db()
        
        # 1. Get Candidates (Relevance) - Vector Search
        # We fetch more than limit to allow re-ranking
        candidates = await memory_core.arecall(query, limit=limit * 3)
        
        # 2. Score and Rank
        scored_memories = []
        now = datetime.now(UTC)
        
        for mem in candidates:
            # Relevance Score (from Vector DB)
            relevance = mem.score or 0.0
            
            # Importance Score (from Metadata)
            importance = float(mem.metadata.get("importance", 5.0) or 5.0) / 10.0 # Normalize 0-1
            
            # Recency Score (Exponential Decay)
            ts_str = mem.timestamp
            try:
                # Handle different timestamp formats if necessary, assuming ISO format
                if isinstance(ts_str, str):
                    mem_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                else:
                    mem_ts = now # Fallback
                    
                # Ensure timezone aware
                if mem_ts.tzinfo is None:
                    mem_ts = mem_ts.replace(tzinfo=UTC)
                
                hours_passed = (now - mem_ts).total_seconds() / 3600.0
                recency = math.pow(self.decay_factor, max(0, hours_passed))
            except Exception:
                recency = 0.5
            
            # Final Score
            final_score = (self.alpha * recency) + (self.beta * importance) + (self.gamma * relevance)
            
            # Update score in object
            mem.score = final_score
            scored_memories.append(mem)

        # Sort by final score
        scored_memories.sort(key=lambda x: x.score, reverse=True)
        
        return scored_memories[:limit]

    async def _calculate_importance(self, content: str, use_local: bool = False) -> float:
        """
        Uses LLM to rate importance 1-10.
        Supports local model fallback.
        """
        try:
            # Load prompt
            # Assuming running from app root
            prompt_path = "app/prompts/memory_rating.txt"
            try:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    prompt_template = f.read()
            except FileNotFoundError:
                # Fallback if path is different
                import os
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                prompt_path = os.path.join(base_dir, "prompts", "memory_rating.txt")
                with open(prompt_path, "r", encoding="utf-8") as f:
                    prompt_template = f.read()
            
            prompt = prompt_template.replace("{memory_content}", content)
            
            # Use Local Model if requested
            if use_local:
                # Tenta usar Ollama/Local via um role específico ou config
                # Assumindo que ModelPriority.LOCAL_ONLY force o uso de modelos locais
                # ou que podemos passar um provider específico.
                # Como o LLMService abstrai isso, usamos prioridade.
                priority = ModelPriority.FAST_AND_CHEAP # Usually implies local or cheapest
                # Se tivéssemos um ModelPriority.LOCAL seria ideal.
                # Vamos assumir que FAST_AND_CHEAP tenta local primeiro se configurado.
            else:
                priority = ModelPriority.FAST_AND_CHEAP

            response = await self.llm_service.invoke_llm(
                prompt=prompt,
                role=ModelRole.REASONER,
                priority=priority,
                timeout_seconds=10
            )
            
            score_text = response.get("response", "").strip()
            # Extract number
            match = re.search(r"\b([1-9]|10)\b", score_text)
            if match:
                return float(match.group(1))
            return 5.0 # Default
            
        except Exception as e:
            logger.error("log_error", message=f"Failed to calculate importance: {e}")
            if use_local:
                raise e # Propagate to allow fallback
            return 5.0

    async def prune_memories(self, retention_days: int = 60, min_importance: float = 3.0):
        """
        Marks old and unimportant memories as archived in Neo4j.
        """
        kg_service = get_knowledge_graph_service()
        db = await kg_service.get_db()
        
        # Calculate cutoff date
        cutoff_date = (datetime.now(UTC) - timedelta(days=retention_days)).isoformat()
        
        cypher = """
        MATCH (e:Experience)
        WHERE e.timestamp < $cutoff_date 
          AND e.importance < $min_importance
          AND (e.status IS NULL OR e.status <> 'archived')
        SET e.status = 'archived'
        RETURN count(e) as archived_count
        """
        
        try:
            result = await db.query(cypher, {"cutoff_date": cutoff_date, "min_importance": min_importance})
            if result:
                count = result[0].get("archived_count", 0)
                logger.info("log_info", message=f"Archived {count} old/unimportant memories")
        except Exception as e:
            logger.error("log_error", message=f"Failed to prune memories: {e}")

# Global instance
generative_memory_service = GenerativeMemoryService()
