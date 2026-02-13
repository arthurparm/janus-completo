import json
from pathlib import Path

from app.services.technical_qa_eval_service import (
    TechnicalQAEvaluator,
    compare_with_baseline,
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
                "question": "Where is query code endpoint?",
                "expected_keywords": ["endpoint", "query"],
                "expected_citations": [
                    {"file_path_contains": "janus/app/api/v1/endpoints/knowledge.py", "line_min": 1}
                ],
            },
            {
                "id": "T2",
                "category": "service",
                "question": "Where is evaluator service?",
                "expected_keywords": ["evaluator", "service"],
                "expected_citations": [
                    {
                        "file_path_contains": "janus/app/services/technical_qa_eval_service.py",
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
                        "file_path": "janus/app/api/v1/endpoints/knowledge.py",
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
                    "file_path": "janus/app/services/technical_qa_eval_service.py",
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
            "citations": [{"file_path": "janus/app/api/v1/endpoints/knowledge.py", "line": 10}],
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
