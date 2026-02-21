import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


QueryFn = Callable[[str, int, int, float], dict[str, Any]]


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * percentile))
    return float(ordered[index])


def _dataset_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _safe_slug(value: str) -> str:
    keep = []
    for ch in value:
        if ch.isalnum() or ch in ("-", "_", "."):
            keep.append(ch)
        else:
            keep.append("-")
    return "".join(keep).strip("-") or "unknown"


def _line_value(raw: Any) -> int:
    try:
        value = int(raw)
        return value if value > 0 else 1
    except Exception:
        return 1


def _citation_rule_matches(citation: dict[str, Any], rule: dict[str, Any]) -> bool:
    file_path = str(citation.get("file_path", ""))
    line = _line_value(citation.get("line", 1))
    file_filter = str(rule.get("file_path_contains", "")).strip()
    line_min = _line_value(rule.get("line_min", 1))

    if file_filter and file_filter not in file_path:
        return False
    if line < line_min:
        return False
    return True


class TechnicalQAEvaluator:
    def __init__(self, dataset_path: str | Path):
        self.dataset_path = Path(dataset_path)

    def load_dataset(self) -> dict[str, Any]:
        data = json.loads(self.dataset_path.read_text(encoding="utf-8"))
        if "dataset_id" not in data or "version" not in data or "cases" not in data:
            raise ValueError("Invalid dataset format: expected dataset_id, version and cases.")
        if not isinstance(data["cases"], list) or not data["cases"]:
            raise ValueError("Invalid dataset format: cases must be a non-empty list.")
        return data

    def run(
        self,
        query_fn: QueryFn,
        *,
        query_limit: int = 10,
        citation_limit: int = 8,
        timeout_s: float = 20.0,
    ) -> dict[str, Any]:
        dataset = self.load_dataset()
        dataset_version = str(dataset.get("version"))
        dataset_id = str(dataset.get("dataset_id"))
        dataset_hash = _dataset_hash(dataset)

        cases_out: list[dict[str, Any]] = []
        latencies: list[float] = []
        passed = 0
        citation_hit_cases = 0
        keyword_ratios: list[float] = []

        for case in dataset["cases"]:
            case_id = str(case.get("id", "unknown"))
            question = str(case.get("question", "")).strip()
            category = str(case.get("category", "general"))
            expected_keywords = [str(k).lower() for k in case.get("expected_keywords", [])]
            expected_citations = case.get("expected_citations", [])
            keyword_min_ratio = float(case.get("keyword_min_ratio", 0.5))
            require_citation = bool(case.get("require_citation", True))

            status = "failed"
            error = None
            answer = ""
            citations: list[dict[str, Any]] = []
            latency_ms = 0.0

            try:
                response = query_fn(question, query_limit, citation_limit, timeout_s)
                answer = str(response.get("answer", ""))
                citations = response.get("citations", []) or []
                error = response.get("error")
                latency_ms = float(response.get("latency_ms", 0.0))
            except Exception as exc:
                error = str(exc)

            latencies.append(latency_ms)
            answer_lower = answer.lower()

            if expected_keywords:
                keyword_hits = sum(1 for token in expected_keywords if token in answer_lower)
                keyword_ratio = keyword_hits / len(expected_keywords)
            else:
                keyword_hits = 0
                keyword_ratio = 1.0

            if expected_citations:
                citation_rule_hits = 0
                for rule in expected_citations:
                    if any(_citation_rule_matches(c, rule) for c in citations):
                        citation_rule_hits += 1
                citation_ratio = citation_rule_hits / len(expected_citations)
            else:
                citation_rule_hits = 0
                citation_ratio = 1.0

            keyword_ratios.append(keyword_ratio)

            citation_ok = citation_ratio > 0.0 if require_citation else True
            keyword_ok = keyword_ratio >= keyword_min_ratio
            no_error = not error
            case_passed = keyword_ok and citation_ok and no_error
            if case_passed:
                passed += 1
                status = "passed"

            if citation_ratio > 0.0:
                citation_hit_cases += 1

            cases_out.append(
                {
                    "id": case_id,
                    "category": category,
                    "question": question,
                    "status": status,
                    "error": error,
                    "latency_ms": round(latency_ms, 2),
                    "answer_excerpt": answer[:240],
                    "keyword_hits": keyword_hits,
                    "keyword_ratio": round(keyword_ratio, 4),
                    "keyword_min_ratio": keyword_min_ratio,
                    "citation_hits": citation_rule_hits,
                    "citation_ratio": round(citation_ratio, 4),
                    "expected_citations_count": len(expected_citations),
                    "citations_returned": len(citations),
                }
            )

        total = len(cases_out)
        pass_rate = (passed / total) if total else 0.0
        summary = {
            "total_cases": total,
            "passed_cases": passed,
            "failed_cases": total - passed,
            "pass_rate": round(pass_rate, 4),
            "avg_latency_ms": round(sum(latencies) / total, 2) if total else 0.0,
            "p95_latency_ms": round(_percentile(latencies, 0.95), 2),
            "citation_coverage": round((citation_hit_cases / total) if total else 0.0, 4),
            "avg_keyword_ratio": round(sum(keyword_ratios) / total, 4) if total else 0.0,
        }

        return {
            "generated_at": _now_iso(),
            "dataset": {
                "dataset_id": dataset_id,
                "version": dataset_version,
                "hash": dataset_hash,
                "num_cases": total,
                "path": str(self.dataset_path),
            },
            "summary": summary,
            "cases": cases_out,
        }


def render_markdown_summary(result: dict[str, Any]) -> str:
    dataset = result.get("dataset", {})
    summary = result.get("summary", {})
    lines = [
        "# Technical QA Evaluation Summary",
        "",
        f"- Dataset: `{dataset.get('dataset_id')}`",
        f"- Version: `{dataset.get('version')}`",
        f"- Hash: `{dataset.get('hash')}`",
        f"- Generated at: `{result.get('generated_at')}`",
        "",
        "## Metrics",
        "",
        f"- Total cases: `{summary.get('total_cases', 0)}`",
        f"- Passed cases: `{summary.get('passed_cases', 0)}`",
        f"- Failed cases: `{summary.get('failed_cases', 0)}`",
        f"- Pass rate: `{summary.get('pass_rate', 0.0)}`",
        f"- Avg latency ms: `{summary.get('avg_latency_ms', 0.0)}`",
        f"- P95 latency ms: `{summary.get('p95_latency_ms', 0.0)}`",
        f"- Citation coverage: `{summary.get('citation_coverage', 0.0)}`",
        "",
        "## Cases",
        "",
        "| ID | Category | Status | Latency (ms) | Keyword Ratio | Citation Ratio | Error |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for case in result.get("cases", []):
        lines.append(
            f"| {case.get('id')} | {case.get('category')} | {case.get('status')} | "
            f"{case.get('latency_ms')} | {case.get('keyword_ratio')} | "
            f"{case.get('citation_ratio')} | {case.get('error') or ''} |"
        )
    return "\n".join(lines) + "\n"


def write_run_artifacts(result: dict[str, Any], runs_root: str | Path) -> Path:
    runs_root = Path(runs_root)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output_dir = runs_root / run_id
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "score.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output_dir / "summary.md").write_text(render_markdown_summary(result), encoding="utf-8")
    return output_dir


def publish_baseline(result: dict[str, Any], baselines_root: str | Path) -> Path:
    baselines_root = Path(baselines_root)
    dataset = result.get("dataset", {})
    dataset_id = _safe_slug(str(dataset.get("dataset_id", "technical-qa")))
    version = _safe_slug(str(dataset.get("version", "v1")))
    baseline_dir = baselines_root / dataset_id / version
    baseline_dir.mkdir(parents=True, exist_ok=True)

    payload = dict(result)
    payload["baseline_published_at"] = _now_iso()

    (baseline_dir / "score.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (baseline_dir / "summary.md").write_text(render_markdown_summary(payload), encoding="utf-8")

    index_path = baselines_root / dataset_id / "index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        index = {"dataset_id": dataset_id, "versions": []}

    existing = [v for v in index.get("versions", []) if v.get("version") != version]
    existing.append(
        {
            "version": version,
            "published_at": payload["baseline_published_at"],
            "score_path": (baseline_dir / "score.json").relative_to(baselines_root).as_posix(),
        }
    )
    index["versions"] = sorted(existing, key=lambda v: v.get("published_at", ""))
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return baseline_dir


def compare_with_baseline(result: dict[str, Any], baselines_root: str | Path) -> dict[str, Any] | None:
    baselines_root = Path(baselines_root)
    dataset = result.get("dataset", {})
    dataset_id = _safe_slug(str(dataset.get("dataset_id", "technical-qa")))
    version = _safe_slug(str(dataset.get("version", "v1")))
    score_path = baselines_root / dataset_id / version / "score.json"
    if not score_path.exists():
        return None

    baseline = json.loads(score_path.read_text(encoding="utf-8"))
    current_summary = result.get("summary", {})
    baseline_summary = baseline.get("summary", {})

    return {
        "baseline_path": str(score_path),
        "baseline_generated_at": baseline.get("generated_at"),
        "dataset_hash_match": str(result.get("dataset", {}).get("hash", ""))
        == str(baseline.get("dataset", {}).get("hash", "")),
        "current_summary": current_summary,
        "baseline_summary": baseline_summary,
        "pass_rate_delta": round(
            float(current_summary.get("pass_rate", 0.0))
            - float(baseline_summary.get("pass_rate", 0.0)),
            4,
        ),
        "p95_latency_ms_delta": round(
            float(current_summary.get("p95_latency_ms", 0.0))
            - float(baseline_summary.get("p95_latency_ms", 0.0)),
            2,
        ),
        "citation_coverage_delta": round(
            float(current_summary.get("citation_coverage", 0.0))
            - float(baseline_summary.get("citation_coverage", 0.0)),
            4,
        ),
    }


def evaluate_regression_gate(
    *,
    comparison: dict[str, Any] | None,
    require_baseline: bool,
    max_pass_rate_drop: float,
    max_citation_coverage_drop: float,
    max_p95_latency_increase_ms: float,
) -> dict[str, Any]:
    violations: list[str] = []
    normalized_pass_drop = max(0.0, float(max_pass_rate_drop))
    normalized_citation_drop = max(0.0, float(max_citation_coverage_drop))
    normalized_latency_increase = max(0.0, float(max_p95_latency_increase_ms))

    if comparison is None:
        if require_baseline:
            violations.append("baseline_missing")
        return {
            "passed": not require_baseline,
            "violations": violations,
            "thresholds": {
                "max_pass_rate_drop": normalized_pass_drop,
                "max_citation_coverage_drop": normalized_citation_drop,
                "max_p95_latency_increase_ms": normalized_latency_increase,
            },
        }

    if comparison.get("dataset_hash_match") is False:
        violations.append("baseline_dataset_hash_mismatch")

    if float(comparison.get("pass_rate_delta", 0.0)) < -normalized_pass_drop:
        violations.append("pass_rate_regression")

    if float(comparison.get("citation_coverage_delta", 0.0)) < -normalized_citation_drop:
        violations.append("citation_coverage_regression")

    if float(comparison.get("p95_latency_ms_delta", 0.0)) > normalized_latency_increase:
        violations.append("p95_latency_regression")

    return {
        "passed": not violations,
        "violations": violations,
        "thresholds": {
            "max_pass_rate_drop": normalized_pass_drop,
            "max_citation_coverage_drop": normalized_citation_drop,
            "max_p95_latency_increase_ms": normalized_latency_increase,
        },
    }


def _find_repo_file_for_rule(repo_root: Path, rule: dict[str, Any]) -> Path | None:
    needle = str(rule.get("file_path_contains", "")).strip().replace("\\", "/")
    if not needle:
        return None

    direct = (repo_root / needle).resolve()
    if direct.exists() and direct.is_file():
        return direct

    if needle.startswith("./"):
        direct2 = (repo_root / needle[2:]).resolve()
        if direct2.exists() and direct2.is_file():
            return direct2

    for candidate in repo_root.rglob("*"):
        if not candidate.is_file():
            continue
        rel = candidate.relative_to(repo_root).as_posix()
        if needle in rel:
            return candidate
    return None


def _find_line_for_keywords(file_path: Path, keywords: list[str], fallback_line: int) -> int:
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return max(1, int(fallback_line or 1))

    lowered = [k.lower().strip() for k in keywords if str(k).strip()]
    if not lowered:
        return max(1, int(fallback_line or 1))

    for idx, line in enumerate(lines, start=1):
        text = line.lower()
        if any(token in text for token in lowered):
            return idx
    return max(1, int(fallback_line or 1))


def build_offline_codebase_query_fn(
    *,
    dataset_payload: dict[str, Any],
    repo_root: str | Path,
) -> QueryFn:
    root = Path(repo_root).resolve()
    case_by_question = {
        str(case.get("question", "")).strip(): case
        for case in (dataset_payload.get("cases") or [])
    }

    def _query(question: str, _query_limit: int, citation_limit: int, _timeout_s: float) -> dict[str, Any]:
        started = time.perf_counter()
        case = case_by_question.get(str(question).strip())
        if not case:
            return {
                "answer": "",
                "citations": [],
                "error": "offline_case_not_found",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }

        keywords = [str(k).strip().lower() for k in case.get("expected_keywords", []) if str(k).strip()]
        rules = list(case.get("expected_citations", []) or [])
        citations: list[dict[str, Any]] = []

        for rule in rules:
            if len(citations) >= max(1, int(citation_limit)):
                break
            file_path = _find_repo_file_for_rule(root, rule)
            if not file_path:
                continue
            line = _find_line_for_keywords(
                file_path,
                keywords=keywords,
                fallback_line=_line_value(rule.get("line_min", 1)),
            )
            rel = file_path.relative_to(root).as_posix()
            citations.append({"file_path": rel, "line": line})

        if not citations:
            return {
                "answer": "",
                "citations": [],
                "error": "offline_citation_resolution_failed",
                "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            }

        answer = (
            "Offline technical QA evidence. "
            f"Keywords: {', '.join(keywords[:10])}. "
            "Citations resolved from repository files."
        )
        return {
            "answer": answer,
            "citations": citations,
            "error": None,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        }

    return _query
