"""Treinamento neural do Janus.

O backend funcional atual treina, valida, versiona e persiste classificadores
Multinomial Naive Bayes. Tipos sem backend real permanecem no domínio interno
para evolução futura, mas falham explicitamente e não geram métricas simuladas.
"""

import hashlib
import json
import math
import re
import time
from collections import Counter as CollectionsCounter
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import structlog
from prometheus_client import Counter, Gauge, Histogram

from app.core.infrastructure.filesystem_manager import read_file, write_file
from app.core.infrastructure.prompt_loader import PROMPTS_DIR
from app.core.memory.memory_core import get_memory_db
from app.models.schemas import Experience, ExperienceMetadata

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
        self, experiences: Sequence[dict[str, Any] | Experience]
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
        self, experiences: Sequence[dict[str, Any] | Experience]
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
            content = exp.get("text") or exp.get("content") or exp.get("completion") or ""
            exp_type = exp.get("label") or exp.get("metadata", {}).get("type", "unknown")

            texts.append(str(content))
            labels.append(str(exp_type))

        logger.info("log_info", message=f"[DatasetPreparator] Preparados {len(texts)} exemplos para classificação")
        return texts, labels

    def prepare_for_prediction(
        self, experiences: Sequence[dict[str, Any] | Experience]
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

    def __init__(self) -> None:
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

            elapsed = time.perf_counter() - start_time
            result.training_time_seconds = elapsed

            # 5. Salva modelo
            if result.status == TrainingStatus.VALIDATING:
                result = await self._save_model(config, result)
                result.status = TrainingStatus.COMPLETED

            # Métricas
            _TRAINING_JOBS.labels(
                config.model_type.value,
                "success" if result.status == TrainingStatus.COMPLETED else "failure",
            ).inc()
            _TRAINING_LATENCY.observe(elapsed)

            if result.accuracy is not None:
                _MODEL_ACCURACY.labels(config.model_name, result.model_version).set(result.accuracy)

            if result.status == TrainingStatus.COMPLETED:
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
            recalled = await memory_db.arecall(query=query, limit=config.max_examples or 1000)
            experiences = [_experience_to_dict(experience) for experience in recalled]
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
        """Treina apenas backends realmente implementados."""
        logger.info("log_info", message=f"[NeuralTrainer] Treinando modelo {config.model_name}...")

        if config.model_type != ModelType.CLASSIFIER:
            return TrainingResult(
                model_name=config.model_name,
                model_version="0.0.0",
                status=TrainingStatus.FAILED,
                error=f"Backend de treinamento não implementado para {config.model_type.value}.",
            )

        texts, labels = dataset
        train_rows, validation_rows = self._split_classifier_rows(
            texts, labels, validation_split=config.validation_split
        )
        artifact = self._fit_multinomial_naive_bayes(train_rows)
        serialized = json.dumps(artifact, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        version = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:12]
        return TrainingResult(
            model_name=config.model_name,
            model_version=version,
            status=TrainingStatus.TRAINING,
            num_examples=len(train_rows) + len(validation_rows),
            metadata={
                "model_artifact": artifact,
                "validation_rows": validation_rows,
                "training_examples": len(train_rows),
                "validation_examples": len(validation_rows),
            },
        )

    async def _validate(self, config: TrainingConfig, result: TrainingResult) -> TrainingResult:
        """Valida performance do modelo em dataset de validação."""
        logger.info("log_info", message=f"[NeuralTrainer] Validando modelo {config.model_name}...")

        artifact = result.metadata.get("model_artifact")
        validation_rows = result.metadata.pop("validation_rows", [])
        if not isinstance(artifact, dict) or not validation_rows:
            result.status = TrainingStatus.FAILED
            result.error = "Artefato ou conjunto de validação ausente."
            return result

        metrics = self.evaluate_classifier_artifact(artifact, validation_rows)
        result.accuracy = metrics["accuracy"]
        result.loss = metrics["log_loss"]
        result.metadata["evaluation_metrics"] = metrics
        result.status = TrainingStatus.VALIDATING
        return result

    async def _save_model(self, config: TrainingConfig, result: TrainingResult) -> TrainingResult:
        """Salva modelo treinado em disco."""
        logger.info("log_info", message=f"[NeuralTrainer] Salvando modelo {config.model_name}...")

        # Cria o diretório apenas no momento de uso para evitar side effects em import-time
        # (ex.: ambientes de CI sem permissão de escrita em /app).
        model_dir_name = f"{config.model_name}_v{result.model_version}"
        model_path = self.models_dir / model_dir_name

        # Salva metadata do modelo
        metadata = {
            "model_name": config.model_name,
            "model_version": result.model_version,
            "model_type": config.model_type.value,
            "accuracy": result.accuracy,
            "loss": result.loss,
            "num_examples": result.num_examples,
            "training_time": result.training_time_seconds,
            "evaluation_metrics": result.metadata.get("evaluation_metrics", {}),
            "config": {
                "learning_rate": config.learning_rate,
                "batch_size": config.batch_size,
                "num_epochs": config.num_epochs,
            },
        }

        artifact = result.metadata.get("model_artifact")
        if not isinstance(artifact, dict):
            result.status = TrainingStatus.FAILED
            result.error = "Artefato treinado ausente."
            return result

        metadata_write = write_file(
            str(Path("models") / model_dir_name / "metadata.json"),
            json.dumps(metadata, ensure_ascii=False, indent=2),
            True,
        )
        artifact_write = write_file(
            str(Path("models") / model_dir_name / "model.json"),
            json.dumps(artifact, ensure_ascii=False, sort_keys=True),
            True,
        )
        writes = (metadata_write, artifact_write)
        if any(value.startswith(("Erro:", "[DRY_RUN]")) for value in writes):
            result.status = TrainingStatus.FAILED
            result.error = "Falha ao persistir artefato treinado."
            return result

        result.metadata["model_path"] = str(model_path)
        logger.info("log_info", message=f"[NeuralTrainer] Modelo salvo em: {model_path}")

        return result

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[\wÀ-ÿ]+", str(text).lower(), flags=re.UNICODE)

    @staticmethod
    def _split_classifier_rows(
        texts: list[str], labels: list[str], *, validation_split: float
    ) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for text, label in zip(texts, labels, strict=True):
            normalized_text = str(text).strip()
            normalized_label = str(label).strip()
            if normalized_text and normalized_label and normalized_label != "unknown":
                grouped[normalized_label].append(normalized_text)

        if len(grouped) < 2:
            raise ValueError("O classificador exige ao menos duas classes rotuladas.")
        if any(len(rows) < 2 for rows in grouped.values()):
            raise ValueError("Cada classe precisa de ao menos dois exemplos para treino e validação.")

        train_rows: list[tuple[str, str]] = []
        validation_rows: list[tuple[str, str]] = []
        effective_split = min(0.5, max(0.1, float(validation_split)))
        for label, rows in sorted(grouped.items()):
            ordered = sorted(
                rows,
                key=lambda value: hashlib.sha256(
                    f"{label}\0{value}".encode("utf-8")
                ).hexdigest(),
            )
            validation_count = max(1, min(len(ordered) - 1, round(len(ordered) * effective_split)))
            validation_rows.extend((text, label) for text in ordered[:validation_count])
            train_rows.extend((text, label) for text in ordered[validation_count:])
        return train_rows, validation_rows

    @classmethod
    def _fit_multinomial_naive_bayes(
        cls, rows: list[tuple[str, str]]
    ) -> dict[str, Any]:
        class_documents: CollectionsCounter[str] = CollectionsCounter()
        token_counts: dict[str, CollectionsCounter[str]] = defaultdict(CollectionsCounter)
        vocabulary: set[str] = set()
        for text, label in rows:
            tokens = cls._tokenize(text)
            if not tokens:
                continue
            class_documents[label] += 1
            token_counts[label].update(tokens)
            vocabulary.update(tokens)
        if len(class_documents) < 2 or not vocabulary:
            raise ValueError("Exemplos rotulados insuficientes após tokenização.")
        return {
            "schema_version": 1,
            "algorithm": "multinomial_naive_bayes",
            "class_documents": dict(sorted(class_documents.items())),
            "token_counts": {
                label: dict(sorted(counts.items())) for label, counts in sorted(token_counts.items())
            },
            "class_token_totals": {
                label: sum(counts.values()) for label, counts in sorted(token_counts.items())
            },
            "vocabulary": sorted(vocabulary),
        }

    @classmethod
    def _predict_classifier(
        cls, artifact: dict[str, Any], text: str
    ) -> tuple[str, dict[str, float]]:
        class_documents = artifact["class_documents"]
        token_counts = artifact["token_counts"]
        class_token_totals = artifact["class_token_totals"]
        vocabulary_size = max(1, len(artifact["vocabulary"]))
        total_documents = sum(int(value) for value in class_documents.values())
        tokens = cls._tokenize(text)
        scores: dict[str, float] = {}
        for label, document_count in class_documents.items():
            score = math.log(int(document_count) / total_documents)
            denominator = int(class_token_totals[label]) + vocabulary_size
            label_counts = token_counts[label]
            for token in tokens:
                score += math.log((int(label_counts.get(token, 0)) + 1) / denominator)
            scores[label] = score
        max_score = max(scores.values())
        weights = {label: math.exp(score - max_score) for label, score in scores.items()}
        total_weight = sum(weights.values())
        probabilities = {label: weight / total_weight for label, weight in weights.items()}
        predicted = max(probabilities, key=probabilities.__getitem__)
        return predicted, probabilities

    @classmethod
    def evaluate_classifier_artifact(
        cls, artifact: dict[str, Any], rows: list[tuple[str, str]]
    ) -> dict[str, float | int]:
        if not rows:
            raise ValueError("Nenhum exemplo rotulado disponível para avaliação.")
        labels = sorted(str(label) for label in artifact["class_documents"])
        true_positive = CollectionsCounter[str]()
        false_positive = CollectionsCounter[str]()
        false_negative = CollectionsCounter[str]()
        correct = 0
        log_loss = 0.0
        for text, expected in rows:
            predicted, probabilities = cls._predict_classifier(artifact, text)
            correct += int(predicted == expected)
            log_loss -= math.log(max(probabilities.get(expected, 0.0), 1e-15))
            for label in labels:
                if predicted == label and expected == label:
                    true_positive[label] += 1
                elif predicted == label:
                    false_positive[label] += 1
                elif expected == label:
                    false_negative[label] += 1

        def ratio(numerator: float, denominator: float) -> float:
            return numerator / denominator if denominator else 0.0

        precisions = [
            ratio(true_positive[label], true_positive[label] + false_positive[label])
            for label in labels
        ]
        recalls = [
            ratio(true_positive[label], true_positive[label] + false_negative[label])
            for label in labels
        ]
        f1_scores = [
            ratio(2 * precision * recall, precision + recall)
            for precision, recall in zip(precisions, recalls, strict=True)
        ]
        return {
            "accuracy": correct / len(rows),
            "precision_macro": sum(precisions) / len(labels),
            "recall_macro": sum(recalls) / len(labels),
            "f1_macro": sum(f1_scores) / len(labels),
            "log_loss": log_loss / len(rows),
            "examples_evaluated": len(rows),
        }

    async def _memorize_training(self, config: TrainingConfig, result: TrainingResult) -> None:
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
                    metadata=ExperienceMetadata.model_validate(
                        {
                            "origin": "neural_training",
                            "model_name": config.model_name,
                            "model_version": result.model_version,
                            "model_type": config.model_type.value,
                            "accuracy": result.accuracy,
                        }
                    ),
                )
            )
        except Exception as e:
            logger.warning("log_warning", message=f"Falha ao memorizar treino: {e}")


# ==================== INSTÂNCIA GLOBAL ====================

neural_trainer = NeuralTrainer()
