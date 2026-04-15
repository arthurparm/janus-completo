from __future__ import annotations

import argparse
import asyncio
import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

from app.core.kernel import Kernel


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark comparativo baseline vs experimental retrieval.")
    parser.add_argument(
        "--dataset",
        default="backend/evals/retrieval/datasets/turboquant_retrieval.v1.json",
    )
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--md-out", required=True)
    return parser


def _recall_at_k(expected_ids: set[str], predicted_ids: list[str], k: int) -> float:
    if not expected_ids:
        return 0.0
    return len(expected_ids.intersection(predicted_ids[:k])) / len(expected_ids)


def _ndcg_at_k(expected_ids: set[str], predicted_ids: list[str], k: int) -> float:
    dcg = 0.0
    for idx, predicted_id in enumerate(predicted_ids[:k], start=1):
        if predicted_id in expected_ids:
            dcg += 1.0 / math.log2(idx + 1)
    ideal_hits = min(len(expected_ids), k)
    if ideal_hits == 0:
        return 0.0
    idcg = sum(1.0 / math.log2(idx + 1) for idx in range(1, ideal_hits + 1))
    return dcg / idcg if idcg else 0.0


def _score_results(items: list[dict[str, Any]], expected_ids: set[str]) -> dict[str, float]:
    predicted_ids = [str(item.get("doc_id") or item.get("id")) for item in items]
    coverage_hits = sum(1 for item in items if str(item.get("doc_id") or item.get("id")) in expected_ids)
    return {
        "recall@5": _recall_at_k(expected_ids, predicted_ids, 5),
        "recall@10": _recall_at_k(expected_ids, predicted_ids, 10),
        "nDCG@10": _ndcg_at_k(expected_ids, predicted_ids, 10),
        "citation_coverage": coverage_hits / max(1, len(expected_ids)),
    }


async def _evaluate_case(knowledge: Any, case: dict[str, Any]) -> dict[str, Any]:
    operation = str(case["operation"])
    query = str(case["query"])
    expected_ids = {str(item) for item in case.get("expected_ids", [])}
    started = time.perf_counter()
    comparison = await knowledge.compare_retrieval(
        operation=operation,
        query=query,
        limit=int(case.get("limit", 5)),
        session_id=case.get("session_id"),
        role=case.get("role"),
        memory_type=case.get("memory_type"),
        origin=case.get("origin"),
        doc_id=case.get("doc_id"),
        knowledge_space_id=case.get("knowledge_space_id"),
        start_ts=case.get("start_ts"),
        end_ts=case.get("end_ts"),
        exclude_duplicate=bool(case.get("exclude_duplicate", False)),
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    active_scores = _score_results(comparison["active"], expected_ids)
    shadow_scores = _score_results(comparison["shadow"], expected_ids)
    return {
        "name": case["name"],
        "operation": operation,
        "latency_ms": elapsed_ms,
        "active": active_scores,
        "shadow": shadow_scores,
        "compare_diff": comparison["compare_diff"],
    }


def _summarize(cases: list[dict[str, Any]]) -> dict[str, Any]:
    active_recall = [case["active"]["recall@10"] for case in cases]
    shadow_recall = [case["shadow"]["recall@10"] for case in cases]
    active_coverage = [case["active"]["citation_coverage"] for case in cases]
    shadow_coverage = [case["shadow"]["citation_coverage"] for case in cases]
    latencies = [case["latency_ms"] for case in cases]
    comparison = {
        "recall_drop": (statistics.mean(active_recall) - statistics.mean(shadow_recall))
        if active_recall and shadow_recall
        else 0.0,
        "citation_drop": (statistics.mean(active_coverage) - statistics.mean(shadow_coverage))
        if active_coverage and shadow_coverage
        else 0.0,
        "p95_latency_ms": sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)] if latencies else 0.0,
        "error_rate": 0.0,
    }
    recommendation = "promote_candidate"
    if comparison["recall_drop"] > 0.02 or comparison["citation_drop"] > 0.02:
        recommendation = "reject"
    elif comparison["p95_latency_ms"] > 250.0:
        recommendation = "shadow_only"
    return {"cases": cases, "summary": comparison, "recommendation": recommendation}


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# TurboQuant Retrieval Benchmark",
        "",
        f"- Recommendation: `{payload['recommendation']}`",
        f"- Recall drop: `{payload['summary']['recall_drop']:.4f}`",
        f"- Citation drop: `{payload['summary']['citation_drop']:.4f}`",
        f"- P95 latency: `{payload['summary']['p95_latency_ms']:.2f} ms`",
        "",
        "## Cases",
    ]
    for case in payload["cases"]:
        lines.extend(
            [
                f"- `{case['name']}` ({case['operation']})",
                f"  active recall@10={case['active']['recall@10']:.4f}, "
                f"shadow recall@10={case['shadow']['recall@10']:.4f}, "
                f"overlap={case['compare_diff']['overlap_ratio']:.4f}",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


async def _run(args: argparse.Namespace) -> dict[str, Any]:
    dataset = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    kernel = Kernel.get_instance()
    await kernel.startup()
    try:
        knowledge = kernel.knowledge_facade
        assert knowledge is not None
        cases = [await _evaluate_case(knowledge, case) for case in dataset.get("cases", [])]
    finally:
        await kernel.shutdown()
    payload = _summarize(cases)
    json_path = Path(args.json_out)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_markdown(Path(args.md_out), payload)
    return payload


def main() -> int:
    args = _parser().parse_args()
    payload = asyncio.run(_run(args))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
