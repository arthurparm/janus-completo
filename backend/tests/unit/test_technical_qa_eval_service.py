import json
from pathlib import Path

from app.services.technical_qa_eval_service import (
    TechnicalQAEvaluator,
    build_offline_codebase_query_fn,
    compare_with_baseline,
    evaluate_regression_gate,
    publish_baseline,
    write_run_artifacts,
)


def _dataset_payload() -> dict:
    return {
        "dataset_id": "technical-qa",
        "version": "v1",
        "cases": [
            {
                "id": "T1",
                "category": "api",
                "question": "Where is query code endpoint",
                "expected_keywords": ["endpoint", "query"],
                "expected_citations": [
                    {"file_path_contains": "backend/app/api/v1/endpoints/knowledge.py", "line_min": 1}
                ],
            },
            {
                "id": "T2",
                "category": "service",
                "question": "Where is evaluator service",
                "expected_keywords": ["evaluator", "service"],
                "expected_citations": [
                    {
                        "file_path_contains": "backend/app/services/technical_qa_eval_service.py",
                        "line_min": 1,
                    }
                ],
            },
        ],
    }


def test_evaluator_run_and_metrics(tmp_path: Path):
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps(_dataset_payload(), indent=2), encoding="utf-8")

    evaluator = TechnicalQAEvaluator(dataset_path)

    def _query(question: str, _limit: int, _citation_limit: int, _timeout_s: float):
        if "query code" in question.lower():
            return {
                "answer": "This endpoint query returns citations.",
                "citations": [
                    {
                        "file_path": "backend/app/api/v1/endpoints/knowledge.py",
                        "line": 200,
                    }
                ],
                "error": None,
                "latency_ms": 120.0,
            }
        return {
            "answer": "Technical evaluator service baseline.",
            "citations": [
                {
                    "file_path": "backend/app/services/technical_qa_eval_service.py",
                    "line": 12,
                }
            ],
            "error": None,
            "latency_ms": 150.0,
        }

    result = evaluator.run(_query, query_limit=10, citation_limit=8, timeout_s=5.0)

    assert result["dataset"]["dataset_id"] == "technical-qa"
    assert result["dataset"]["version"] == "v1"
    assert result["summary"]["total_cases"] == 2
    assert result["summary"]["passed_cases"] == 2
    assert result["summary"]["pass_rate"] == 1.0
    assert result["summary"]["citation_coverage"] == 1.0


def test_artifacts_and_baseline_compare(tmp_path: Path):
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps(_dataset_payload(), indent=2), encoding="utf-8")
    evaluator = TechnicalQAEvaluator(dataset_path)

    result = evaluator.run(
        lambda *_args, **_kwargs: {
            "answer": "endpoint query evaluator service",
            "citations": [{"file_path": "backend/app/api/v1/endpoints/knowledge.py", "line": 10}],
            "error": None,
            "latency_ms": 100.0,
        }
    )

    runs_root = tmp_path / "runs"
    baselines_root = tmp_path / "baselines"

    run_dir = write_run_artifacts(result, runs_root)
    assert (run_dir / "score.json").exists()
    assert (run_dir / "summary.md").exists()

    baseline_dir = publish_baseline(result, baselines_root)
    assert (baseline_dir / "score.json").exists()
    assert (baseline_dir / "summary.md").exists()

    comparison = compare_with_baseline(result, baselines_root)
    assert comparison is not None
    assert comparison["pass_rate_delta"] == 0.0
    assert comparison["citation_coverage_delta"] == 0.0
    assert comparison["dataset_hash_match"] is True


def test_regression_gate_thresholds():
    comparison = {
        "pass_rate_delta": -0.05,
        "citation_coverage_delta": -0.03,
        "p95_latency_ms_delta": 400.0,
        "dataset_hash_match": True,
    }
    gate = evaluate_regression_gate(
        comparison=comparison,
        require_baseline=True,
        max_pass_rate_drop=0.02,
        max_citation_coverage_drop=0.02,
        max_p95_latency_increase_ms=250.0,
    )
    assert gate["passed"] is False
    assert "pass_rate_regression" in gate["violations"]
    assert "citation_coverage_regression" in gate["violations"]
    assert "p95_latency_regression" in gate["violations"]


def test_regression_gate_requires_baseline_when_missing():
    gate = evaluate_regression_gate(
        comparison=None,
        require_baseline=True,
        max_pass_rate_drop=0.01,
        max_citation_coverage_drop=0.01,
        max_p95_latency_increase_ms=100.0,
    )
    assert gate["passed"] is False
    assert gate["violations"] == ["baseline_missing"]


def test_offline_query_fn_uses_dataset_rules(tmp_path: Path):
    dataset = _dataset_payload()
    # Ensure citation path exists relative to simulated repo root
    target = tmp_path / "janus" / "app" / "api" / "v1" / "endpoints"
    target.mkdir(parents=True, exist_ok=True)
    (target / "knowledge.py").write_text("def query_code():\n    # endpoint query\n    pass\n", encoding="utf-8")
    (tmp_path / "janus" / "app" / "services").mkdir(parents=True, exist_ok=True)
    (tmp_path / "janus" / "app" / "services" / "technical_qa_eval_service.py").write_text(
        "class EvaluatorService:\n    pass\n", encoding="utf-8"
    )

    query_fn = build_offline_codebase_query_fn(dataset_payload=dataset, repo_root=tmp_path)
    response = query_fn(dataset["cases"][0]["question"], 10, 8, 5.0)

    assert response["error"] is None
    assert response["citations"]
    assert "keywords" in response["answer"].lower()
