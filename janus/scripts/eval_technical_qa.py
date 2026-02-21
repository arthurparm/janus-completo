import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.technical_qa_eval_service import (
    TechnicalQAEvaluator,
    build_offline_codebase_query_fn,
    compare_with_baseline,
    evaluate_regression_gate,
    publish_baseline,
    write_run_artifacts,
)


def _call_code_query_endpoint(
    *,
    base_url: str,
    endpoint_path: str,
    question: str,
    query_limit: int,
    citation_limit: int,
    timeout_s: float,
) -> dict[str, Any]:
    url = f"{base_url.rstrip('/')}/{endpoint_path.lstrip('/')}"
    payload = json.dumps(
        {
            "question": question,
            "limit": int(query_limit),
            "citation_limit": int(citation_limit),
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/json"},
    )

    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            body = response.read().decode("utf-8")
            parsed = json.loads(body) if body else {}
            return {
                "answer": parsed.get("answer", ""),
                "citations": parsed.get("citations", []) or [],
                "error": None,
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "answer": "",
            "citations": [],
            "error": f"http_{exc.code}:{body[:180]}",
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }
    except Exception as exc:
        return {
            "answer": "",
            "citations": [],
            "error": str(exc),
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }


def _build_parser() -> argparse.ArgumentParser:
    repo_root = Path(__file__).resolve().parents[1]
    workspace_root = repo_root.parent
    default_dataset = repo_root / "evals" / "technical-qa" / "datasets" / "technical-qa.v1.json"
    default_runs_root = repo_root / "evals" / "technical-qa" / "runs"
    default_baselines_root = repo_root / "evals" / "technical-qa" / "baselines"

    parser = argparse.ArgumentParser(
        description="Runs the technical QA evaluation dataset and writes score artifacts."
    )
    parser.add_argument("--dataset", default=str(default_dataset))
    parser.add_argument(
        "--mode",
        choices=["live", "offline-codebase"],
        default="live",
        help="live: call API endpoint; offline-codebase: resolve citations directly from repository.",
    )
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--endpoint-path", default="/api/v1/knowledge/query/code")
    parser.add_argument("--repo-root", default=str(workspace_root))
    parser.add_argument("--query-limit", type=int, default=10)
    parser.add_argument("--citation-limit", type=int, default=8)
    parser.add_argument("--timeout-s", type=float, default=20.0)
    parser.add_argument("--runs-root", default=str(default_runs_root))
    parser.add_argument("--baselines-root", default=str(default_baselines_root))
    parser.add_argument("--publish-baseline", action="store_true")
    parser.add_argument("--compare-baseline", action="store_true")
    parser.add_argument("--gate-on-regression", action="store_true")
    parser.add_argument("--require-baseline", action="store_true")
    parser.add_argument("--max-pass-rate-drop", type=float, default=0.02)
    parser.add_argument("--max-citation-coverage-drop", type=float, default=0.02)
    parser.add_argument("--max-p95-latency-increase-ms", type=float, default=250.0)
    parser.add_argument("--min-pass-rate", type=float, default=0.0)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    evaluator = TechnicalQAEvaluator(args.dataset)
    dataset_payload = evaluator.load_dataset()

    if args.mode == "offline-codebase":
        query_fn = build_offline_codebase_query_fn(
            dataset_payload=dataset_payload,
            repo_root=args.repo_root,
        )
    else:
        query_fn = lambda question, query_limit, citation_limit, timeout_s: _call_code_query_endpoint(
            base_url=args.base_url,
            endpoint_path=args.endpoint_path,
            question=question,
            query_limit=query_limit,
            citation_limit=citation_limit,
            timeout_s=timeout_s,
        )

    result = evaluator.run(
        query_fn=query_fn,
        query_limit=args.query_limit,
        citation_limit=args.citation_limit,
        timeout_s=args.timeout_s,
    )

    if args.compare_baseline:
        comparison = compare_with_baseline(result, args.baselines_root)
        if comparison:
            result["comparison"] = comparison
        elif args.require_baseline:
            result["comparison"] = {"baseline_missing": True}

    if args.gate_on_regression:
        gate = evaluate_regression_gate(
            comparison=result.get("comparison"),
            require_baseline=bool(args.require_baseline),
            max_pass_rate_drop=float(args.max_pass_rate_drop),
            max_citation_coverage_drop=float(args.max_citation_coverage_drop),
            max_p95_latency_increase_ms=float(args.max_p95_latency_increase_ms),
        )
        result["baseline_gate"] = gate

    run_dir = write_run_artifacts(result, args.runs_root)
    print(f"Run artifacts written to: {run_dir}")
    print(f"Score file: {run_dir / 'score.json'}")
    print(f"Summary file: {run_dir / 'summary.md'}")

    if args.publish_baseline:
        baseline_dir = publish_baseline(result, args.baselines_root)
        print(f"Baseline published to: {baseline_dir}")

    pass_rate = float(result.get("summary", {}).get("pass_rate", 0.0))
    if pass_rate < float(args.min_pass_rate):
        print(
            f"Pass rate {pass_rate:.4f} is lower than min-pass-rate {float(args.min_pass_rate):.4f}"
        )
        return 2
    if args.gate_on_regression:
        gate = result.get("baseline_gate") or {}
        if not bool(gate.get("passed", True)):
            print(f"Regression gate failed: {gate.get('violations', [])}")
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
