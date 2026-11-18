import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.learning import TrainRequest
from app.core.workers.neural_training_system import (
    ModelType,
    NeuralTrainer,
    TrainingConfig,
    TrainingStatus,
)
from app.repositories import learning_repository as learning_repository_module
from app.repositories.learning_repository import LearningRepository
from app.services.learning_service import LearningService, TrainingFailedError


def _classifier_dataset() -> tuple[list[str], list[str]]:
    return (
        [
            "falha critica no banco",
            "erro de conexao no banco",
            "consulta executada com sucesso",
            "operacao concluida corretamente",
            "timeout ao gravar dados",
            "resultado validado com sucesso",
        ],
        ["failure", "failure", "success", "success", "failure", "success"],
    )


def test_classifier_training_uses_real_artifact_and_holdout_metrics() -> None:
    trainer = NeuralTrainer()
    config = TrainingConfig(
        model_type=ModelType.CLASSIFIER,
        model_name="janus-test-classifier",
        validation_split=0.34,
    )

    trained = asyncio.run(trainer._train(config, _classifier_dataset()))
    validated = asyncio.run(trainer._validate(config, trained))

    assert validated.status == TrainingStatus.VALIDATING
    assert validated.model_version != "1.0.0"
    assert validated.metadata["model_artifact"]["algorithm"] == "multinomial_naive_bayes"
    metrics = validated.metadata["evaluation_metrics"]
    assert metrics["examples_evaluated"] == 2
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert metrics["log_loss"] >= 0.0


def test_unimplemented_training_backend_fails_instead_of_simulating() -> None:
    trainer = NeuralTrainer()
    config = TrainingConfig(
        model_type=ModelType.LLM_FINETUNING,
        model_name="unsupported",
    )

    result = asyncio.run(trainer._train(config, []))

    assert result.status == TrainingStatus.FAILED
    assert result.accuracy is None
    assert "não implementado" in str(result.error)


def test_public_training_contract_advertises_only_real_backend() -> None:
    assert TrainRequest.model_validate({"model_type": "CLASSIFIER"}).model_type.value == "classifier"
    with pytest.raises(ValidationError):
        TrainRequest.model_validate({"model_type": "llm_finetuning"})


def test_learning_health_and_stats_do_not_fabricate_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        learning_repository_module,
        "read_file",
        lambda _path: "Erro: dataset ausente",
    )
    repository = LearningRepository()
    service = LearningService(repository)

    health = service.get_health_status()
    stats = service.get_learning_statistics()

    assert health["status"] == "degraded"
    assert health["training_capacity_available"] is False
    assert health["data_quality"]["score"] is None
    assert health["data_quality"]["available"] is False
    assert stats["avg_training_time_minutes"] is None


def test_classifier_evaluation_reads_real_artifact_and_labeled_examples(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    trainer = NeuralTrainer()
    texts, labels = _classifier_dataset()
    artifact = trainer._fit_multinomial_naive_bayes(list(zip(texts, labels, strict=True)))
    model_dir = tmp_path / "models" / "classifier-v1"
    model_dir.mkdir(parents=True)
    (model_dir / "model.json").write_text(json.dumps(artifact), encoding="utf-8")
    dataset = "\n".join(
        json.dumps({"text": text, "label": label, "prompt": text, "completion": text})
        for text, label in zip(texts, labels, strict=True)
    )
    monkeypatch.setattr(learning_repository_module, "WORKSPACE_DIR", tmp_path)
    monkeypatch.setattr(learning_repository_module, "read_file", lambda _path: dataset)

    result = LearningRepository().evaluate_classifier("classifier-v1", limit=4)

    assert result["examples_evaluated"] == 4
    assert result["metrics"]["accuracy"] == 1.0


class _TrainingPreflightRepository:
    def get_dataset_version_info(self) -> dict[str, Any]:
        return {"version": None, "num_examples": 0}

    def get_dataset_quality(self) -> dict[str, Any]:
        return {"labeled_examples": 0, "training_ready": False}


def test_training_preflight_rejects_missing_labeled_dataset() -> None:
    service = LearningService(_TrainingPreflightRepository())  # type: ignore[arg-type]

    with pytest.raises(TrainingFailedError, match="duas classes"):
        asyncio.run(service.trigger_training("classifier", {}))
