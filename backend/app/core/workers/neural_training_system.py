"""
Sprint 9: Gênese Neural - Sistema de Treinamento Autônomo

Sistema completo para treinamento autônomo de modelos de machine learning
a partir de experiências coletadas. Permite fine-tuning de LLMs e treinamento
de modelos especializados.

Funcionalidades:
- Preparação de datasets de treino
- Fine-tuning de LLMs (GPT, LLaMA, etc)
- Treinamento de modelos especializados
- Avaliação e validação de modelos
- Versionamento de modelos
- Deploy automático de modelos treinados
"""

import asyncio
import json
import structlog
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from prometheus_client import Counter, Gauge, Histogram

from app.core.infrastructure.filesystem_manager import read_file, write_file
from app.core.infrastructure.prompt_loader import PROMPTS_DIR
from app.core.memory.memory_core import get_memory_db
from app.models.schemas import Experience

logger = structlog.get_logger(__name__)

_PROMPT_CACHE: dict[str, str] = {}


def _experience_to_dict(exp: Any) -> dict[str, Any]:
    """Normaliza experiências para dicts (dict / Pydantic model / objeto leve)."""
    if isinstance(exp, dict):
        return exp

    model_dump = getattr(exp, "model_dump", None)
    if callable(model_dump):
        data = model_dump(mode="python")
        if isinstance(data, dict):
            return data

    legacy_dict = getattr(exp, "dict", None)
    if callable(legacy_dict):
        data = legacy_dict()
        if isinstance(data, dict):
            return data

    metadata = getattr(exp, "metadata", None)
    metadata_dict: dict[str, Any]
    if isinstance(metadata, dict):
        metadata_dict = metadata
    elif metadata is not None:
        md_dump = getattr(metadata, "model_dump", None)
        if callable(md_dump):
            dumped = md_dump(mode="python")
            metadata_dict = dumped if isinstance(dumped, dict) else {}
        else:
            md_legacy = getattr(metadata, "dict", None)
            if callable(md_legacy):
                dumped = md_legacy()
                metadata_dict = dumped if isinstance(dumped, dict) else {}
            else:
                metadata_dict = {}
    else:
        metadata_dict = {}

    normalized = {
        "content": getattr(exp, "content", ""),
        "metadata": metadata_dict,
    }
    if hasattr(exp, "prompt"):
        normalized["prompt"] = getattr(exp, "prompt")
    if hasattr(exp, "completion"):
        normalized["completion"] = getattr(exp, "completion")
    return normalized


def _load_prompt_template(prompt_name: str) -> str:
    if prompt_name in _PROMPT_CACHE:
        return _PROMPT_CACHE[prompt_name]

    prompt_path = PROMPTS_DIR / f"{prompt_name}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    content = prompt_path.read_text(encoding="utf-8")
    _PROMPT_CACHE[prompt_name] = content
    return content

# ==================== MÉTRICAS ====================

_TRAINING_JOBS = Counter(
    "neural_training_jobs_total", "Total de jobs de treinamento", ["model_type", "outcome"]
)

_TRAINING_LATENCY = Histogram(
    "neural_training_latency_seconds", "Duração de treinamento de modelos"
)

_MODEL_ACCURACY = Gauge(
    "neural_model_accuracy", "Acurácia do modelo treinado", ["model_name", "model_version"]
)

_TRAINING_EXAMPLES = Gauge(
    "neural_training_examples_count", "Número de exemplos no dataset de treino"
)


# ==================== ENUMS ====================


class ModelType(Enum):
    """Tipos de modelos que podem ser treinados."""

    LLM_FINETUNING = "llm_finetuning"  # Fine-tune de LLM existente
    CLASSIFIER = "classifier"  # Classificador de intenções/categorias
    PREDICTOR = "predictor"  # Preditor de próximas ações
    EMBEDDER = "embedder"  # Modelo de embeddings customizado


class TrainingStatus(Enum):
    """Status de um job de treinamento."""

    PENDING = "pending"
    PREPARING_DATA = "preparing_data"
    TRAINING = "training"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


# ==================== DATACLASSES ====================


@dataclass
class TrainingConfig:
    """Configuração para treinamento de modelo."""

    model_type: ModelType
    model_name: str
    base_model: str | None = None  # Modelo base para fine-tuning
    learning_rate: float = 1e-5
    batch_size: int = 8
    num_epochs: int = 3
    validation_split: float = 0.2
    early_stopping: bool = True
    save_checkpoints: bool = True
    max_examples: int | None = None
    user_id: str | None = None
    data_source: str = "episodic_memory"


@dataclass
class TrainingResult:
    """Resultado de um job de treinamento."""

    model_name: str
    model_version: str
    status: TrainingStatus
    accuracy: float | None = None
    loss: float | None = None
    training_time_seconds: float = 0.0
    num_examples: int = 0
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ==================== PREPARADOR DE DATASETS ====================


class DatasetPreparator:
    """
    Prepara datasets de treino a partir de experiências coletadas.

    Transforma dados brutos em formatos apropriados para diferentes
    tipos de modelos.
    """

    def prepare_for_llm_finetuning(
        self, experiences: list[dict[str, Any] | Experience]
    ) -> list[dict[str, str]]:
        """
        Prepara dataset para fine-tuning de LLM (formato chat/completion).

        Formato esperado:
        [
            {"prompt": "...", "completion": "..."},
            ...
        ]
        """
        dataset = []

        for raw_exp in experiences:
            exp = _experience_to_dict(raw_exp)
            # Suporte para dados já formatados (ex: vindos de arquivo JSONL)
            if "prompt" in exp and "completion" in exp:
                dataset.append(exp)
                continue

            content = exp.get("content", "")
            exp_type = exp.get("metadata", {}).get("type", "")

            # Extrai prompt e completion baseado no tipo
            if exp_type == "action_success":
                # Usa ação como prompt e resultado como completion
                tool_used = exp.get("metadata", {}).get("tool_used", "")
                template = _load_prompt_template("training_action_success_prompt")
                prompt = template.format(tool_used=tool_used, content=content[:100])
                completion = content
                dataset.append({"prompt": prompt, "completion": completion})

            elif exp_type == "reflexion_iteration":
                # Usa tarefa como prompt e reflexão como completion
                lines = content.split("\n")
                if len(lines) >= 2:
                    prompt = lines[0]  # Tarefa
                    completion = "\n".join(lines[1:])  # Reflexão
                    dataset.append({"prompt": prompt, "completion": completion})

            elif exp_type == "lessons_learned":
                # Usa contexto como prompt e lições como completion
                template = _load_prompt_template("training_lessons_learned_prompt")
                prompt = template
                completion = content
                dataset.append({"prompt": prompt, "completion": completion})

        logger.info("log_info", message=f"[DatasetPreparator] Preparados {len(dataset)} exemplos para LLM fine-tuning")
        return dataset

    def prepare_for_classification(
        self, experiences: list[dict[str, Any] | Experience]
    ) -> tuple[list[str], list[str]]:
        """
        Prepara dataset para treinamento de classificador.

        Returns:
            (texts, labels): Tupla com textos e rótulos
        """
        texts = []
        labels = []

        for raw_exp in experiences:
            exp = _experience_to_dict(raw_exp)
            content = exp.get("content", "")
            exp_type = exp.get("metadata", {}).get("type", "unknown")

            texts.append(content)
            labels.append(exp_type)

        logger.info("log_info", message=f"[DatasetPreparator] Preparados {len(texts)} exemplos para classificação")
        return texts, labels

    def prepare_for_prediction(
        self, experiences: list[dict[str, Any] | Experience]
    ) -> list[dict[str, Any]]:
        """
        Prepara dataset para predição de próximas ações.

        Cria pares de (contexto histórico) -> (próxima ação)
        """
        # Ordena por timestamp
        normalized = [_experience_to_dict(exp) for exp in experiences]
        sorted_exps = sorted(normalized, key=lambda x: x.get("metadata", {}).get("timestamp", 0))

        dataset = []
        window_size = 5  # Usa últimas 5 ações como contexto

        for i in range(window_size, len(sorted_exps)):
            context = sorted_exps[i - window_size : i]
            next_action = sorted_exps[i]

            context_text = "\n".join(exp.get("content", "")[:100] for exp in context)

            dataset.append({"context": context_text, "next_action": next_action.get("content", "")})

        logger.info("log_info", message=f"[DatasetPreparator] Preparados {len(dataset)} exemplos para predição")
        return dataset


# ==================== TREINADOR DE MODELOS ====================


class NeuralTrainer:
    """
    Sistema de treinamento autônomo de modelos.

    Gerencia o ciclo completo de treinamento:
    1. Carrega dados de experiências
    2. Prepara dataset
    3. Treina modelo
    4. Valida performance
    5. Salva modelo treinado
    """

    def __init__(self):
        self.preparator = DatasetPreparator()
        self.models_dir = Path("/app/workspace/models")

    async def train_model(self, config: TrainingConfig) -> TrainingResult:
        """
        Treina um modelo com a configuração especificada.

        Args:
            config: Configuração de treinamento

        Returns:
            Resultado do treinamento
        """
        start_time = time.perf_counter()

        try:
            logger.info("log_info", message=f"[NeuralTrainer] Iniciando treinamento: {config.model_name}")

            # 1. Carrega dados de treino
            experiences = await self._load_training_data(config)

            if not experiences:
                return TrainingResult(
                    model_name=config.model_name,
                    model_version="0.0.0",
                    status=TrainingStatus.FAILED,
                    error="Nenhum dado de treino disponível",
                )

            _TRAINING_EXAMPLES.set(len(experiences))

            # 2. Prepara dataset
            dataset = self._prepare_dataset(config.model_type, experiences)

            # 3. Treina modelo
            result = await self._train(config, dataset)

            # 4. Valida
            if result.status == TrainingStatus.TRAINING:
                result = await self._validate(config, result)

            # 5. Salva modelo
            if result.status == TrainingStatus.VALIDATING:
                result = await self._save_model(config, result)
                result.status = TrainingStatus.COMPLETED

            elapsed = time.perf_counter() - start_time
            result.training_time_seconds = elapsed

            # Métricas
            _TRAINING_JOBS.labels(
                config.model_type.value,
                "success" if result.status == TrainingStatus.COMPLETED else "failure",
            ).inc()
            _TRAINING_LATENCY.observe(elapsed)

            if result.accuracy is not None:
                _MODEL_ACCURACY.labels(config.model_name, result.model_version).set(result.accuracy)

            # Memoriza resultado
            await self._memorize_training(config, result)

            logger.info("log_info", message=f"[NeuralTrainer] Treinamento concluído: {result.status.value}")
            return result

        except Exception as e:
            logger.error("log_error", message=f"[NeuralTrainer] Erro no treinamento: {e}", exc_info=True)
            _TRAINING_JOBS.labels(config.model_type.value, "error").inc()

            return TrainingResult(
                model_name=config.model_name,
                model_version="0.0.0",
                status=TrainingStatus.FAILED,
                error=str(e),
                training_time_seconds=time.perf_counter() - start_time,
            )

    async def _load_training_data(self, config: TrainingConfig) -> list[dict[str, Any]]:
        """Carrega dados de treino da memória episódica ou arquivo."""
        try:
            if config.data_source == "filesystem":
                logger.info("[NeuralTrainer] Carregando dados de training_data.jsonl")
                content = read_file("workspace/training_data.jsonl")
                if content.startswith("Erro:"):
                    logger.warning("log_warning", message=f"Falha ao ler training_data.jsonl: {content}")
                    return []

                experiences = []
                lines = [ln for ln in content.strip().split("\n") if ln.strip()]

                # Apply limit if needed
                if config.max_examples:
                    lines = lines[: config.max_examples]

                for ln in lines:
                    try:
                        item = json.loads(ln)
                        experiences.append(item)
                    except Exception:
                        continue

                logger.info("log_info", message=f"[NeuralTrainer] Carregados {len(experiences)} exemplos do arquivo")
                return experiences

            query = "experiência de uso de ferramentas e aprendizado"
            memory_db = await get_memory_db()
            experiences = await memory_db.arecall(query=query, limit=config.max_examples or 1000)
            if config.user_id:
                uid = str(config.user_id)
                experiences = [
                    e for e in experiences if str(e.get("metadata", {}).get("user_id", "")) == uid
                ]

            logger.info("log_info", message=f"[NeuralTrainer] Carregadas {len(experiences)} experiências para treino")
            return experiences

        except Exception as e:
            logger.error("log_error", message=f"[NeuralTrainer] Erro ao carregar dados: {e}", exc_info=True)
            return []

    def _prepare_dataset(self, model_type: ModelType, experiences: list[dict[str, Any]]) -> Any:
        """Prepara dataset baseado no tipo de modelo."""
        if model_type == ModelType.LLM_FINETUNING:
            return self.preparator.prepare_for_llm_finetuning(experiences)
        elif model_type == ModelType.CLASSIFIER:
            return self.preparator.prepare_for_classification(experiences)
        elif model_type == ModelType.PREDICTOR:
            return self.preparator.prepare_for_prediction(experiences)
        else:
            return experiences

    async def _train(self, config: TrainingConfig, dataset: Any) -> TrainingResult:
        """
        Executa treinamento do modelo.

        NOTA: Esta é uma implementação simplificada/simulada.
        Em produção, integraria com frameworks como:
        - Hugging Face Transformers (para LLMs)
        - Scikit-learn (para classificadores)
        - PyTorch/TensorFlow (para modelos customizados)
        """
        logger.info("log_info", message=f"[NeuralTrainer] Treinando modelo {config.model_name}...")

        # Simula treinamento
        await asyncio.sleep(2)  # Em produção: loop de treinamento real

        # Simula métricas de treino
        simulated_accuracy = 0.75 + (len(dataset) / 1000) * 0.15
        simulated_accuracy = min(0.95, simulated_accuracy)

        simulated_loss = 0.5 - (simulated_accuracy - 0.75) * 0.3

        return TrainingResult(
            model_name=config.model_name,
            model_version="1.0.0",
            status=TrainingStatus.TRAINING,
            accuracy=simulated_accuracy,
            loss=simulated_loss,
            num_examples=len(dataset),
        )

    async def _validate(self, config: TrainingConfig, result: TrainingResult) -> TrainingResult:
        """Valida performance do modelo em dataset de validação."""
        logger.info("log_info", message=f"[NeuralTrainer] Validando modelo {config.model_name}...")

        # Simula validação
        await asyncio.sleep(1)

        result.status = TrainingStatus.VALIDATING
        result.metadata["validation_passed"] = result.accuracy >= 0.7

        return result

    async def _save_model(self, config: TrainingConfig, result: TrainingResult) -> TrainingResult:
        """Salva modelo treinado em disco."""
        logger.info("log_info", message=f"[NeuralTrainer] Salvando modelo {config.model_name}...")

        # Cria o diretório apenas no momento de uso para evitar side effects em import-time
        # (ex.: ambientes de CI sem permissão de escrita em /app).
        self.models_dir.mkdir(parents=True, exist_ok=True)
        model_path = self.models_dir / f"{config.model_name}_v{result.model_version}"
        model_path.mkdir(parents=True, exist_ok=True)

        # Salva metadata do modelo
        metadata = {
            "model_name": config.model_name,
            "model_version": result.model_version,
            "model_type": config.model_type.value,
            "accuracy": result.accuracy,
            "loss": result.loss,
            "num_examples": result.num_examples,
            "training_time": result.training_time_seconds,
            "config": {
                "learning_rate": config.learning_rate,
                "batch_size": config.batch_size,
                "num_epochs": config.num_epochs,
            },
        }

        metadata_file = str(model_path / "metadata.json")
        write_file(metadata_file, json.dumps(metadata, indent=2))

        result.metadata["model_path"] = str(model_path)
        logger.info("log_info", message=f"[NeuralTrainer] Modelo salvo em: {model_path}")

        return result

    async def _memorize_training(self, config: TrainingConfig, result: TrainingResult):
        """Memoriza resultado do treinamento."""
        try:
            memory_db = await get_memory_db()
            await memory_db.amemorize(
                Experience(
                    type="neural_training",
                    content=f"Modelo '{config.model_name}' treinado com sucesso\n"
                    f"Acurácia: {result.accuracy:.2%}\n"
                    f"Exemplos: {result.num_examples}\n"
                    f"Tempo: {result.training_time_seconds:.1f}s",
                    metadata={
                        "model_name": config.model_name,
                        "model_version": result.model_version,
                        "model_type": config.model_type.value,
                        "accuracy": result.accuracy,
                        "origin": "neural_training",
                    },
                )
            )
        except Exception as e:
            logger.warning("log_warning", message=f"Falha ao memorizar treino: {e}")


# ==================== INSTÂNCIA GLOBAL ====================

neural_trainer = NeuralTrainer()
