from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.v1.endpoints import deployment
from app.core.security.actor_context import ActorContext, ActorType, AuthMethod
from app.services import model_artifact_service
from app.services.bias_check_service import BiasCheckService
from app.services.model_artifact_service import ModelArtifactError, load_model_metadata


def _service_request():
    actor = ActorContext.authenticated(
        actor_id="janus-deployer",
        actor_type=ActorType.SERVICE,
        roles=("SERVICE",),
        auth_method=AuthMethod.CLIENT_CREDENTIALS,
        trace_id="trace-deploy",
        scopes=("deployment:execute",),
    )
    return SimpleNamespace(state=SimpleNamespace(actor_context=actor))


def _write_model(tmp_path, *, fairness: dict | None = None):
    model_dir = tmp_path / "classifier-v1"
    model_dir.mkdir()
    metadata = {
        "accuracy": 0.9,
        "evaluation_metrics": {"accuracy": 0.9, "examples_evaluated": 20},
    }
    if fairness is not None:
        metadata["fairness_evaluation"] = fairness
    (model_dir / "metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    (model_dir / "model.json").write_text("{}", encoding="utf-8")


def test_model_artifact_path_rejects_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr(model_artifact_service, "MODELS_BASE_DIR", tmp_path)

    with pytest.raises(ModelArtifactError, match="model_id"):
        load_model_metadata("../secrets")


def test_precheck_does_not_invent_bias_from_accuracy(monkeypatch, tmp_path):
    monkeypatch.setattr(model_artifact_service, "MODELS_BASE_DIR", tmp_path)
    _write_model(tmp_path)

    result = BiasCheckService().run_precheck("classifier-v1")

    assert result["precheck_passed"] is False
    assert result["bias_score"] is None
    assert result["evidence"]["performance_metrics_present"] is True
    assert result["evidence"]["fairness_metrics_present"] is False
    assert "accuracy is not a bias metric" in result["safety_warnings"][0]


def test_precheck_rejects_undeclared_fairness_claim(monkeypatch, tmp_path):
    monkeypatch.setattr(model_artifact_service, "MODELS_BASE_DIR", tmp_path)
    _write_model(tmp_path, fairness={"measured": True, "bias_score": 0.1})

    result = BiasCheckService().run_precheck("classifier-v1")

    assert result["precheck_passed"] is False
    assert result["bias_score"] is None
    assert result["evidence"]["fairness_metrics_present"] is False


def test_stage_request_rejects_invalid_percent_and_model_id():
    with pytest.raises(ValidationError):
        deployment.StageRequest(model_id="classifier-v1", rollout_percent=101)
    with pytest.raises(ValidationError):
        deployment.StageRequest(model_id="../classifier", rollout_percent=10)


@pytest.mark.asyncio
async def test_stage_rejects_missing_artifact_before_persistence(monkeypatch, tmp_path):
    monkeypatch.setattr(model_artifact_service, "MODELS_BASE_DIR", tmp_path)

    class _Inference:
        calls = 0

        def stage_model(self, *, model_id: str, rollout_percent: int):
            self.calls += 1
            return {"status": "staged"}

    inference = _Inference()
    with pytest.raises(HTTPException) as exc_info:
        await deployment.stage(
            deployment.StageRequest(model_id="missing-model", rollout_percent=10),
            _service_request(),
            inference,
        )

    assert exc_info.value.status_code == 400
    assert inference.calls == 0


@pytest.mark.asyncio
async def test_publish_never_marks_model_active_without_runtime_adapter(monkeypatch, tmp_path):
    monkeypatch.setattr(model_artifact_service, "MODELS_BASE_DIR", tmp_path)
    _write_model(
        tmp_path,
        fairness={"measured": True, "bias_score": 0.1, "dataset": "reviewed-v1"},
    )

    class _Inference:
        publish_calls = 0

        def precheck(self, *, model_id: str):
            return {"precheck_passed": True, "bias_score": 0.1}

        def publish_model(self, *, model_id: str):
            self.publish_calls += 1
            return {"status": "active"}

    inference = _Inference()
    with pytest.raises(HTTPException) as exc_info:
        await deployment.publish("classifier-v1", _service_request(), inference)

    assert exc_info.value.status_code == 501
    assert inference.publish_calls == 0


@pytest.mark.asyncio
async def test_publish_rejects_non_finite_accuracy(monkeypatch, tmp_path):
    monkeypatch.setattr(model_artifact_service, "MODELS_BASE_DIR", tmp_path)
    _write_model(tmp_path)
    metadata_path = tmp_path / "classifier-v1" / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["accuracy"] = "NaN"
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(HTTPException) as exc_info:
        await deployment.publish("classifier-v1", _service_request(), SimpleNamespace())

    assert exc_info.value.status_code == 400
    assert "finite" in exc_info.value.detail


@pytest.mark.asyncio
async def test_precheck_rejects_invalid_model_id_before_facade_call():
    class _Inference:
        calls = 0

        def precheck(self, *, model_id: str):
            self.calls += 1
            return {"precheck_passed": True}

    inference = _Inference()
    with pytest.raises(HTTPException) as exc_info:
        await deployment.precheck("../../etc", _service_request(), inference)

    assert exc_info.value.status_code == 400
    assert inference.calls == 0
