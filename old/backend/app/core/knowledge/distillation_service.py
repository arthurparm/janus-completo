import json
import structlog
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.models.schemas import TaskState

logger = structlog.get_logger(__name__)


class DistillationService:
    """
    Serviço responsável por destilar conhecimento de tarefas bem-sucedidas.
    Filtra, sanitiza e persiste traces de raciocínio de alta qualidade
    para futuro fine-tuning (Dataset Auto-Curated).
    """

    # Regex para detecção de segredos comuns (API Keys, Tokens)
    SECRET_PATTERNS = [
        r"sk-[a-zA-Z0-9]{48}",  # OpenAI classic key prefix
        r"sk-proj-[a-zA-Z0-9-_]{20,}",  # OpenAI project
        r"(api_key|access_token|secret|token)[-_'\"]?\s*[:=]\s*['\"]?[a-zA-Z0-9-_]{20,}['\"]?",  # Genérico
        r"Bearer [a-zA-Z0-9-_]{20,}",  # Auth Headers
    ]

    def __init__(self, dataset_path: str = "data/training_data.jsonl"):
        self.dataset_path = Path(dataset_path)
        self._lock = threading.Lock()

        # Garante que o diretório existe
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)

    def process_task(self, state: TaskState) -> bool:
        """
        Avalia e, se aprovado, salva a tarefa no dataset de destilação.
        Retorna True se foi salvo, False caso contrário.
        """
        try:
            # 1. Filtro de Qualidade
            if not self._is_high_quality(state):
                logger.debug("log_debug", message=f"Tarefa {state.task_id} ignorada pelo filtro de qualidade.")
                return False

            # 2. Extração e Sanitização
            training_example = self._extract_training_example(state)
            if not training_example:
                return False

            # 3. Persistência (Thread-Safe)
            self._append_to_dataset(training_example)

            logger.info("log_info", message=f"Conhecimento destilado com sucesso: {state.task_id}",
                extra={"reasoning_len": len(training_example["reasoning"])}
            )
            return True

        except Exception as e:
            logger.error("log_error", message=f"Falha ao destilar tarefa {state.task_id}: {e}", exc_info=True)
            return False

    def _is_high_quality(self, state: TaskState) -> bool:
        """
        Verifica se a tarefa atende aos critérios de qualidade para destilação.
        """
        # Deve ter sido bem sucedida
        pass_status = (state.status or "").lower() in ["completed", "success", "done"]
        if not pass_status:
            return False

        # Deve ter raciocínio (Chain of Thought)
        reasoning = self._extract_reasoning(state)

        # Heurística: Raciocínio muito curto (< 50 chars) geralmente é "Thinking..." ou lixo
        if not reasoning or len(reasoning) < 50:
            return False

        # Deve ter um objetivo claro e um resultado
        if not state.original_goal:
            return False

        return True

    def _extract_reasoning(self, state: TaskState) -> str | None:
        """
        Percorre o histórico ou eventos para encontrar o melhor trace de raciocínio.
        Prioriza eventos de agentes 'thinker' ou 'coder'.
        """
        # Tenta pegar do último evento com reasoning preenchido
        for event in reversed(state.history):
            if event.reasoning:
                return event.reasoning
        return None

    def _extract_training_example(self, state: TaskState) -> Dict[str, Any] | None:
        """
        Transforma o TaskState em um formato compatível com Fine-Tuning.
        """
        reasoning = self._extract_reasoning(state)
        if not reasoning:
            return None

        # Sanitiza os campos
        instruction = self._sanitize(state.original_goal)
        input_context = self._sanitize(state.data_payload.context or "")

        output_content = ""
        # Tenta pegar a resposta final (código ou texto)
        if state.data_payload.code:
            output_content = state.data_payload.code
        elif state.data_payload.response:
             output_content = state.data_payload.response
        else:
             # Fallback: tentar pegar notes do ultimo evento
             if state.history:
                 output_content = state.history[-1].notes

        output_content = self._sanitize(output_content)
        reasoning = self._sanitize(reasoning)

        return {
            "instruction": instruction,
            "input": input_context[:2000], # Trucando contexto excessivo p/ economizar
            "output": output_content,
            "reasoning": reasoning,
            "metadata": {
                "task_id": state.task_id,
                "agent_flow": [e.agent_role for e in state.history],
                "collected_at": datetime.utcnow().isoformat()
            }
        }

    def _sanitize(self, text: str) -> str:
        """
        Remove informações sensíveis do texto usando Regex.
        """
        if not text:
            return ""

        sanitized = text
        for pattern in self.SECRET_PATTERNS:
            sanitized = re.sub(pattern, "[REDACTED_SECRET]", sanitized, flags=re.IGNORECASE)

        return sanitized

    def _append_to_dataset(self, entry: Dict[str, Any]):
        """
        Adiciona a entrada ao arquivo JSONL com lock de thread.
        """
        line = json.dumps(entry, ensure_ascii=False)

        with self._lock:
            with open(self.dataset_path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
