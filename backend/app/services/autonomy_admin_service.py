from __future__ import annotations

import hashlib
import json
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import structlog
from fastapi import Request

from app.core.llm import ModelPriority, ModelRole
from app.db.graph import get_graph_db
from app.models.schemas import GraphRelationship
from app.repositories.autonomy_admin_repository import AutonomyAdminRepository
from app.services.knowledge_service import KnowledgeService
from app.services.llm_service import LLMService
from app.services.meta_agent_service import get_meta_agent_service

logger = structlog.get_logger(__name__)


class AutonomyAdminServiceError(Exception):
    pass


class AutonomyAdminService:
    DAILY_CAP = 10
    MAX_FILE_SIZE_BYTES = 512 * 1024
    MAX_FILES_PER_RUN = 1200
    MAX_RUN_SECONDS = 90
    ALLOW_INCREMENTAL_FULL_FALLBACK = True
    ALLOWED_ROOTS = ("backend/app", "frontend/src/app", "app")
    IGNORE_DIR_MARKERS = (
        "/node_modules/",
        "/.git/",
        "/.venv/",
        "/dist/",
        "/build/",
        "/__pycache__/",
        "/.playwright-cli/",
        "/outputs/",
        "/output/",
    )
    SELF_MEMORY_RELATION_ALLOWLIST = (
        GraphRelationship.RELATES_TO.value,
        GraphRelationship.CALLS.value,
        GraphRelationship.IMPORTS.value,
        GraphRelationship.DEFINES.value,
        GraphRelationship.USES.value,
        GraphRelationship.DEPENDS_ON.value,
        GraphRelationship.INHERITS_FROM.value,
        GraphRelationship.IMPLEMENTS.value,
        GraphRelationship.CONTAINS.value,
        GraphRelationship.HAS_PROPERTY.value,
        GraphRelationship.MENTIONS.value,
    )

    def __init__(self, llm_service: LLMService, knowledge_service: KnowledgeService):
        self._repo = AutonomyAdminRepository()
        self._llm_service = llm_service
        self._knowledge_service = knowledge_service
        self._meta = get_meta_agent_service()
        # backend/app/services -> backend/app -> backend -> repo
        self._repo_root = Path(__file__).resolve().parents[3]

    def _normalize_repo_path(self, raw_path: str | Path | None) -> str | None:
        if not raw_path:
            return None
        raw = str(raw_path).strip()
        if not raw:
            return None
        candidate = Path(raw)
        if candidate.is_absolute():
            try:
                return candidate.resolve().relative_to(self._repo_root.resolve()).as_posix()
            except Exception:
                return None
        return candidate.as_posix().lstrip("./")

    def _is_allowed_file_path(self, rel_path: str | None) -> bool:
        if not rel_path:
            return False
        rel = rel_path.strip()
        if not rel:
            return False
        if not any(rel.startswith(prefix + "/") or rel == prefix for prefix in self.ALLOWED_ROOTS):
            return False
        if "/app/" not in f"/{rel}/":
            return False
        marker_hit = any(marker in f"/{rel}/" for marker in self.IGNORE_DIR_MARKERS)
        return not marker_hit

    def _repo_relative_if_allowed(self, path: Path) -> str | None:
        try:
            rel = self._normalize_repo_path(path.resolve())
        except Exception:
            return None
        if not self._is_allowed_file_path(rel):
            return None
        return rel

    @staticmethod
    def _fingerprint(parts: list[str]) -> str:
        normalized = "|".join(p.strip().lower() for p in parts if p is not None)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    async def _classify_sprint_type(self, finding: dict[str, Any]) -> tuple[str, str | None, bool, str | None, str | None]:
        category = str(finding.get("category") or "geral").strip().lower()
        area = str(finding.get("area") or "").strip() or None

        # Local-only first
        fallback_used = False
        provider = None
        model = None
        prompt = (
            "Classifique a melhoria técnica abaixo em um tipo curto de sprint (2-4 palavras) "
            "e área (opcional). Responda JSON: {\"sprint_type\": \"...\", \"area\": \"...\"}.\n\n"
            f"Categoria: {category}\n"
            f"Título: {finding.get('title')}\n"
            f"Descrição: {finding.get('description')}"
        )

        try:
            result = await self._llm_service.invoke_llm(
                prompt=prompt,
                role=ModelRole.ORCHESTRATOR,
                priority=ModelPriority.LOCAL_ONLY,
                timeout_seconds=30,
                task_type="autonomy_sprint_classification",
            )
            provider = str(result.get("provider") or "")
            model = str(result.get("model") or "")
            parsed = json.loads(str(result.get("response") or "{}"))
            sprint_type = str(parsed.get("sprint_type") or "").strip()
            area_out = str(parsed.get("area") or "").strip() or area
            if sprint_type:
                return sprint_type[:200], area_out, fallback_used, provider, model
        except Exception:
            pass

        # Fallback allowed
        try:
            fallback_used = True
            result = await self._llm_service.invoke_llm(
                prompt=prompt,
                role=ModelRole.ORCHESTRATOR,
                priority=ModelPriority.FAST_AND_CHEAP,
                timeout_seconds=30,
                task_type="autonomy_sprint_classification",
            )
            provider = str(result.get("provider") or "")
            model = str(result.get("model") or "")
            parsed = json.loads(str(result.get("response") or "{}"))
            sprint_type = str(parsed.get("sprint_type") or "").strip()
            area_out = str(parsed.get("area") or "").strip() or area
            if sprint_type:
                return sprint_type[:200], area_out, fallback_used, provider, model
        except Exception:
            pass

        # Deterministic fallback
        mapping = {
            "reliability": "Correcao Confiabilidade",
            "performance": "Correcao Performance",
            "security": "Correcao Seguranca",
            "quality": "Qualidade Codigo",
            "coverage": "Cobertura QA",
            "qa": "Qualidade QA",
        }
        sprint_type = mapping.get(category, "Melhoria Continua")
        return sprint_type, area, fallback_used, provider, model

    def _find_latest_json(self, pattern: str) -> Path | None:
        files = list(self._repo_root.glob(pattern))
        if not files:
            return None
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files[0]

    def _load_json_if_exists(self, path: Path | None) -> dict[str, Any] | None:
        if path is None or not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    async def _collect_findings(self) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []

        # Meta-agent report
        report = self._meta.get_latest_report()
        if report:
            data = report.to_dict() if hasattr(report, "to_dict") else {}
            for issue in data.get("issues_detected", []) or []:
                findings.append(
                    {
                        "source": "meta_agent",
                        "source_kind": "meta_issue",
                        "category": str(issue.get("category") or "reliability"),
                        "title": str(issue.get("title") or "Issue detectada"),
                        "description": str(issue.get("description") or ""),
                        "area": str(issue.get("category") or "") or None,
                        "severity": str(issue.get("severity") or "medium"),
                        "source_ref": f"meta:{data.get('cycle_id')}",
                        "payload": issue,
                    }
                )
            for rec in data.get("recommendations", []) or []:
                findings.append(
                    {
                        "source": "meta_agent",
                        "source_kind": "meta_recommendation",
                        "category": str(rec.get("category") or "quality"),
                        "title": str(rec.get("title") or "Recomendacao"),
                        "description": str(rec.get("description") or ""),
                        "area": str(rec.get("category") or "") or None,
                        "severity": "medium",
                        "source_ref": f"meta:{data.get('cycle_id')}",
                        "payload": rec,
                    }
                )

        # QA artifacts
        coverage = self._load_json_if_exists(self._find_latest_json("outputs/qa/api_coverage_report.json"))
        if coverage:
            summary = coverage.get("summary") or {}
            target = coverage.get("target") or {}
            uncovered = int(summary.get("uncovered_endpoints") or 0)
            if uncovered > 0:
                findings.append(
                    {
                        "source": "qa_artifact",
                        "source_kind": "qa_api_coverage",
                        "category": "coverage",
                        "title": f"Cobertura API incompleta ({uncovered} endpoints sem cobertura)",
                        "description": f"Target met={target.get('target_met')} gap={target.get('endpoint_gap')}",
                        "area": "api",
                        "severity": "medium",
                        "source_ref": "outputs/qa/api_coverage_report.json",
                        "payload": {
                            "summary": summary,
                            "target": target,
                        },
                    }
                )

        score = self._load_json_if_exists(self._find_latest_json("outputs/qa/technical-qa/runs/*/score.json"))
        if score:
            summary = score.get("summary") or {}
            pass_rate = float(summary.get("pass_rate") or 0.0)
            if pass_rate < 1.0:
                findings.append(
                    {
                        "source": "qa_artifact",
                        "source_kind": "qa_technical_eval",
                        "category": "qa",
                        "title": f"Technical QA abaixo do ideal (pass_rate={pass_rate:.2f})",
                        "description": "Casos falhos detectados no score.json",
                        "area": "knowledge",
                        "severity": "high",
                        "source_ref": "outputs/qa/technical-qa/runs/*/score.json",
                        "payload": summary,
                    }
                )

        slo = self._load_json_if_exists(self._find_latest_json("outputs/qa/domain_slo_report.json"))
        if slo:
            active_alerts = slo.get("active_alerts") or []
            for alert in active_alerts:
                findings.append(
                    {
                        "source": "qa_artifact",
                        "source_kind": "qa_domain_slo_alert",
                        "category": "reliability",
                        "title": f"Alerta SLO ativo ({alert.get('domain')})",
                        "description": str(alert.get("message") or "Violacao de SLO"),
                        "area": str(alert.get("domain") or "ops"),
                        "severity": "high",
                        "source_ref": "outputs/qa/domain_slo_report.json",
                        "payload": alert,
                    }
                )

        return findings

    async def sync_backlog(self) -> dict[str, Any]:
        findings = await self._collect_findings()
        created = 0
        deduped = 0
        capped = 0
        fallback_used_count = 0
        daily_created = self._repo.count_auto_created_today()
        closed = await self.auto_close_tasks()

        for finding in findings:
            fp = self._fingerprint(
                [
                    str(finding.get("source_kind") or ""),
                    str(finding.get("category") or ""),
                    str(finding.get("title") or ""),
                    str(finding.get("description") or ""),
                    str(finding.get("area") or ""),
                ]
            )
            existing = self._repo.find_open_task_by_fingerprint(fp)
            if existing:
                deduped += 1
                continue

            if daily_created >= self.DAILY_CAP:
                capped += 1
                continue

            sprint_type_name, area, fallback_used, provider, model = await self._classify_sprint_type(finding)
            if fallback_used:
                fallback_used_count += 1

            sprint_type = self._repo.get_or_create_sprint_type(name=sprint_type_name, generated_by="janus")
            now = datetime.now(timezone.utc)
            week_start = now - timedelta(days=now.weekday())
            week_end = week_start + timedelta(days=6)
            sprint = self._repo.get_or_create_active_sprint(
                sprint_type_id=sprint_type.id,
                sprint_name=f"{sprint_type.name} - {week_start.date().isoformat()}",
                start_ts=week_start.timestamp(),
                end_ts=week_end.timestamp(),
            )

            priority = 2
            sev = str(finding.get("severity") or "medium").lower()
            if sev in {"high", "critical"}:
                priority = 1
            elif sev in {"low"}:
                priority = 4

            task = self._repo.create_task(
                title=str(finding.get("title") or "Melhoria detectada"),
                description=str(finding.get("description") or ""),
                sprint_id=sprint.id,
                priority=priority,
                source=str(finding.get("source") or "autonomy_admin"),
                source_kind=str(finding.get("source_kind") or "unknown"),
                source_fingerprint=fp,
                source_ref=str(finding.get("source_ref") or "") or None,
                area=area,
                severity=sev,
                auto_created=True,
                llm_provider=provider,
                llm_model=model,
                fallback_used=fallback_used,
            )
            self._repo.add_task_evidence(
                goal_id=task.id,
                evidence_type=str(finding.get("source_kind") or "finding"),
                source_uri=str(finding.get("source_ref") or "") or None,
                payload=finding.get("payload") or finding,
                score=None,
            )
            created += 1
            daily_created += 1

        return {
            "created": created,
            "deduped": deduped,
            "capped": capped,
            "closed": closed,
            "fallback_used_count": fallback_used_count,
            "findings_total": len(findings),
        }

    async def auto_close_tasks(self) -> int:
        closed = 0
        coverage = self._load_json_if_exists(self._find_latest_json("outputs/qa/api_coverage_report.json")) or {}
        score = self._load_json_if_exists(self._find_latest_json("outputs/qa/technical-qa/runs/*/score.json")) or {}
        target_met = bool((coverage.get("target") or {}).get("target_met"))
        pass_rate = float((score.get("summary") or {}).get("pass_rate") or 0.0)

        for task in self._repo.list_open_tasks():
            kind = str(task.source_kind or "")
            should_close = False
            reason = ""
            if kind == "qa_api_coverage" and target_met:
                should_close = True
                reason = "qa_api_coverage_target_met"
            elif kind == "qa_technical_eval" and pass_rate >= 1.0:
                should_close = True
                reason = "qa_technical_eval_pass_rate_ideal"

            if should_close:
                updated = self._repo.close_task(task.id, reason=reason, actor="autoclose_engine")
                if updated:
                    closed += 1
        return closed

    def get_board(self, *, status: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        return self._repo.list_board(status=status, limit=limit)

    def _git(self, args: list[str]) -> str | None:
        try:
            cp = subprocess.run(
                ["git", *args],
                cwd=str(self._repo_root),
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
            if cp.returncode != 0:
                return None
            return cp.stdout.strip()
        except Exception:
            return None

    def _get_head_commit(self) -> str | None:
        return self._git(["rev-parse", "HEAD"])

    def _resolve_files_for_study(
        self,
        *,
        mode: str,
        base_commit: str | None,
        target_commit: str | None,
        task_files: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        seen: set[str] = set()

        if mode == "incremental" and base_commit and target_commit:
            out = self._git(["diff", "--name-only", f"{base_commit}..{target_commit}"])
            if out:
                for rel in [line.strip() for line in out.splitlines() if line.strip()]:
                    p = self._repo_root / rel
                    allowed = self._repo_relative_if_allowed(p)
                    if not allowed or not p.exists() or allowed in seen:
                        continue
                    seen.add(allowed)
                    results.append(
                        {
                            "file_path": allowed,
                            "change_type": "modified",
                            "sha_before": base_commit,
                            "sha_after": target_commit,
                        }
                    )

        if not results and task_files:
            for rel in task_files:
                p = self._repo_root / rel
                allowed = self._repo_relative_if_allowed(p)
                if not allowed or not p.exists() or allowed in seen:
                    continue
                seen.add(allowed)
                results.append(
                    {
                        "file_path": allowed,
                        "change_type": "task_context",
                        "sha_before": base_commit,
                        "sha_after": target_commit,
                    }
                )

        if mode == "incremental" and not results and self.ALLOW_INCREMENTAL_FULL_FALLBACK:
            logger.info(
                "incremental_self_study_fallback_full_scan",
                reason="no_git_diff_or_task_context",
                local_only=True,
            )
        elif mode == "incremental" and not results:
            return results

        if not results:
            for root in self.ALLOWED_ROOTS:
                base = self._repo_root / root
                if not base.exists():
                    continue
                for path in base.rglob("*"):
                    if not path.is_file():
                        continue
                    rel = self._repo_relative_if_allowed(path)
                    if not rel or rel in seen:
                        continue
                    seen.add(rel)
                    results.append(
                        {
                            "file_path": rel,
                            "change_type": "full",
                            "sha_before": base_commit,
                            "sha_after": target_commit,
                        }
                    )
        return results

    def _summarize_file(self, rel_path: str) -> str:
        p = self._repo_root / rel_path
        if not p.exists() or not p.is_file():
            return "Arquivo indisponivel para estudo."
        if p.stat().st_size > self.MAX_FILE_SIZE_BYTES:
            return "Arquivo ignorado por tamanho."
        suffix = p.suffix.lower()
        if suffix not in {".py", ".ts", ".tsx", ".js", ".jsx", ".html", ".scss", ".css", ".md", ".json"}:
            return "Arquivo fora dos tipos de estudo permitidos."
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return "Falha de leitura do arquivo."
        lines = content.count("\n") + 1
        summary = f"{rel_path}: {lines} linhas analisadas."
        if suffix == ".py":
            summary += " Possivel modulo Python com classes/funcoes para indexacao de chamadas."
        elif suffix in {".ts", ".tsx", ".js", ".jsx"}:
            summary += " Possivel modulo de logica frontend/backend JS/TS."
        elif suffix in {".html", ".scss", ".css"}:
            summary += " Arquivo de interface/estilo."
        return summary

    def _build_graph_path_candidates(self, rel_path: str) -> list[str]:
        rel = str(rel_path or "").strip().lstrip("./")
        if not rel:
            return []

        candidates: set[str] = {rel}
        candidates.add(f"/{rel}")

        try:
            abs_path = (self._repo_root / rel).resolve().as_posix()
            candidates.add(abs_path)
        except Exception:
            pass

        if rel.startswith("backend/"):
            stripped = rel[len("backend/") :]
            if stripped:
                candidates.add(stripped)
                candidates.add(f"/{stripped}")
        if rel.startswith("app/"):
            backend_variant = f"backend/{rel}"
            candidates.add(backend_variant)
            candidates.add(f"/{backend_variant}")
            if rel.startswith("app/app/"):
                backend_stripped = f"backend/{rel[len('app/') :]}"
                candidates.add(backend_stripped)
                candidates.add(f"/{backend_stripped}")

        return [p for p in candidates if p]

    def _read_study_file_content(self, rel_path: str) -> tuple[str, str] | None:
        path = self._repo_root / rel_path
        if not path.exists() or not path.is_file():
            return None
        if path.stat().st_size > self.MAX_FILE_SIZE_BYTES:
            return None
        suffix = path.suffix.lower()
        if suffix not in {".py", ".ts", ".tsx", ".js", ".jsx", ".html", ".scss", ".css", ".md", ".json"}:
            return None
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None
        return suffix, content

    def _infer_self_memory_relationship_types(self, rel_path: str, summary: str) -> list[str]:
        path = str(rel_path or "").lower()
        text = str(summary or "").lower()
        rel_types: set[str] = {GraphRelationship.RELATES_TO.value}

        file_data = self._read_study_file_content(rel_path)
        suffix = file_data[0] if file_data else ""
        content = (file_data[1] if file_data else "")[:200_000]
        content_lower = content.lower()

        # Local structural/code analysis (no LLM): imports, declarations, calls, inheritance.
        if content:
            if suffix == ".py":
                if re.search(r"(?m)^\s*(import|from)\s+\S+", content):
                    rel_types.add(GraphRelationship.IMPORTS.value)
                    rel_types.add(GraphRelationship.DEPENDS_ON.value)
                if re.search(r"(?m)^\s*(def|class)\s+\w+", content):
                    rel_types.add(GraphRelationship.DEFINES.value)
                if re.search(r"(?m)^\s*class\s+\w+\s*\([^)]*\)\s*:", content):
                    rel_types.add(GraphRelationship.INHERITS_FROM.value)
                if re.search(r"\b\w+\s*\(", content):
                    rel_types.add(GraphRelationship.CALLS.value)
                    rel_types.add(GraphRelationship.USES.value)
            elif suffix in {".ts", ".tsx", ".js", ".jsx"}:
                if re.search(r"(?m)^\s*import\s+.+\s+from\s+['\"].+['\"]", content):
                    rel_types.add(GraphRelationship.IMPORTS.value)
                    rel_types.add(GraphRelationship.DEPENDS_ON.value)
                if re.search(r"\b(class|function|interface|type|enum)\s+\w+", content):
                    rel_types.add(GraphRelationship.DEFINES.value)
                if re.search(r"\bextends\b", content_lower):
                    rel_types.add(GraphRelationship.INHERITS_FROM.value)
                if re.search(r"\bimplements\b", content_lower):
                    rel_types.add(GraphRelationship.IMPLEMENTS.value)
                if re.search(r"\b\w+\s*\(", content):
                    rel_types.add(GraphRelationship.CALLS.value)
                    rel_types.add(GraphRelationship.USES.value)
            elif suffix in {".html", ".scss", ".css"}:
                rel_types.add(GraphRelationship.HAS_PROPERTY.value)
                rel_types.add(GraphRelationship.CONTAINS.value)
            elif suffix in {".json"}:
                rel_types.add(GraphRelationship.HAS_PROPERTY.value)
            elif suffix == ".md":
                rel_types.add(GraphRelationship.MENTIONS.value)

        # Path/context hints complement code signals.
        if any(marker in path for marker in ("/api/", "/endpoints/", "/controllers/")):
            rel_types.add(GraphRelationship.IMPLEMENTS.value)
        if any(marker in path for marker in ("/models/", "/schemas/", "/types/")):
            rel_types.add(GraphRelationship.DEFINES.value)
        if any(marker in path for marker in ("/services/", "/workers/", "/agents/")):
            rel_types.add(GraphRelationship.USES.value)
        if any(marker in path for marker in ("/db/", "/repositories/", "/storage/")):
            rel_types.add(GraphRelationship.DEPENDS_ON.value)
        if any(marker in path for marker in ("/tests/", ".spec.", ".test.")):
            rel_types.add(GraphRelationship.MENTIONS.value)
        if any(marker in path for marker in (".html", ".scss", ".css")) or "interface/estilo" in text:
            rel_types.add(GraphRelationship.HAS_PROPERTY.value)
            rel_types.add(GraphRelationship.CONTAINS.value)

        return [rel for rel in self.SELF_MEMORY_RELATION_ALLOWLIST if rel in rel_types]

    def _build_self_memory_rel_merge_block(self, target_var: str) -> str:
        lines: list[str] = []
        for rel_type in self.SELF_MEMORY_RELATION_ALLOWLIST:
            lines.append(
                f"              FOREACH (__ IN CASE WHEN '{rel_type}' IN $rel_types THEN [1] ELSE [] END |"
            )
            lines.append(f"                MERGE (m)-[:{rel_type}]->({target_var})")
            lines.append("              )")
        return "\n".join(lines)

    async def _persist_self_memory(self, *, rel_path: str, summary: str, sha_after: str | None) -> None:
        if not self._is_allowed_file_path(rel_path):
            return
        path_candidates = self._build_graph_path_candidates(rel_path)
        if not path_candidates:
            return
        rel_types = self._infer_self_memory_relationship_types(rel_path, summary)
        if not rel_types:
            rel_types = [GraphRelationship.RELATES_TO.value]
        file_rel_merge_block = self._build_self_memory_rel_merge_block("f")
        code_file_rel_merge_block = self._build_self_memory_rel_merge_block("cf")
        graph = await get_graph_db()
        await graph.execute(
            f"""
            MERGE (m:SelfMemory {{file_path: $file_path}})
            SET m.summary = $summary,
                m.updated_at = timestamp(),
                m.confidence = 0.75,
                m.sha_after = $sha_after
            WITH m, $path_candidates AS path_candidates
            OPTIONAL MATCH (f:File)
            WHERE f.path IN path_candidates
            FOREACH (_ IN CASE WHEN f IS NULL THEN [] ELSE [1] END |
{file_rel_merge_block}
            )
            WITH m, path_candidates
            OPTIONAL MATCH (cf:CodeFile)
            WHERE cf.path IN path_candidates
            FOREACH (_ IN CASE WHEN cf IS NULL THEN [] ELSE [1] END |
{code_file_rel_merge_block}
            )
            WITH m, path_candidates
            OPTIONAL MATCH (fn:CodeFunction)
            WHERE fn.file_path IN path_candidates
            FOREACH (_ IN CASE WHEN fn IS NULL OR NOT ('DEFINES' IN $rel_types) THEN [] ELSE [1] END |
              MERGE (m)-[:DEFINES]->(fn)
            )
            WITH m, path_candidates
            OPTIONAL MATCH (cl:CodeClass)
            WHERE cl.file_path IN path_candidates
            FOREACH (_ IN CASE WHEN cl IS NULL OR NOT ('DEFINES' IN $rel_types) THEN [] ELSE [1] END |
              MERGE (m)-[:DEFINES]->(cl)
            )
            """,
            {
                "file_path": rel_path,
                "path_candidates": path_candidates,
                "rel_types": rel_types,
                "summary": summary[:4000],
                "sha_after": sha_after,
            },
            operation="self_study_selfmemory_upsert",
        )

    async def run_self_study(
        self,
        *,
        mode: str = "incremental",
        reason: str | None = None,
        trigger_type: str = "manual",
        task_files: list[str] | None = None,
    ) -> dict[str, Any]:
        mode = (mode or "incremental").strip().lower()
        if mode not in {"incremental", "full"}:
            raise AutonomyAdminServiceError("mode must be incremental|full")

        state = self._repo.get_self_study_state()
        base_commit = state.last_studied_commit if mode == "incremental" else None
        target_commit = self._get_head_commit()

        run = self._repo.create_self_study_run(
            trigger_type=trigger_type,
            mode=mode,
            reason=reason,
            base_commit=base_commit,
            target_commit=target_commit,
        )

        files = self._resolve_files_for_study(
            mode=mode,
            base_commit=base_commit,
            target_commit=target_commit,
            task_files=task_files,
        )
        total_candidates = len(files)
        files = files[: self.MAX_FILES_PER_RUN]
        self._repo.update_self_study_run_progress(
            run.id,
            files_total=len(files),
            files_processed=0,
        )
        processed = 0
        errors = 0
        started = time.perf_counter()
        timed_out = False

        for item in files:
            if (time.perf_counter() - started) >= self.MAX_RUN_SECONDS:
                timed_out = True
                break
            rel = item["file_path"]
            file_row = self._repo.add_self_study_file(
                run_id=run.id,
                file_path=rel,
                change_type=item.get("change_type"),
                sha_before=item.get("sha_before"),
                sha_after=item.get("sha_after"),
                summary_status="running",
            )
            try:
                summary = self._summarize_file(rel)
                await self._persist_self_memory(rel_path=rel, summary=summary, sha_after=item.get("sha_after"))
                self._repo.update_self_study_file_status(file_row.id, "completed")
            except Exception as e:
                errors += 1
                self._repo.update_self_study_file_status(file_row.id, "failed", error=str(e))
            finally:
                processed += 1
                self._repo.update_self_study_run_progress(
                    run.id,
                    files_processed=processed,
                )

        truncated = total_candidates > self.MAX_FILES_PER_RUN
        final_status = (
            "completed"
            if errors == 0 and not timed_out and not truncated
            else ("partial" if processed > 0 else "failed")
        )
        run_error_parts: list[str] = []
        if errors > 0:
            run_error_parts.append(f"{errors} file(s) failed")
        if timed_out:
            run_error_parts.append("run timeout reached")
        if truncated:
            run_error_parts.append(f"file cap reached ({self.MAX_FILES_PER_RUN})")
        self._repo.finish_self_study_run(
            run.id,
            files_total=len(files),
            files_processed=processed,
            status=final_status,
            error="; ".join(run_error_parts) if run_error_parts else None,
        )
        if final_status in {"completed", "partial"}:
            self._repo.update_self_study_state(last_studied_commit=target_commit, mark_success=True)

        return {
            "run_id": run.id,
            "status": final_status,
            "files_total": len(files),
            "files_processed": processed,
            "errors": errors,
            "timed_out": timed_out,
            "file_cap": self.MAX_FILES_PER_RUN,
            "base_commit": base_commit,
            "target_commit": target_commit,
        }

    def get_self_study_status(self) -> dict[str, Any]:
        state = self._repo.get_self_study_state()
        running = self._repo.get_latest_running_self_study()
        runs = self._repo.list_self_study_runs(limit=5)
        return {
            "last_studied_commit": state.last_studied_commit,
            "last_success_at": state.last_success_at.isoformat() if state.last_success_at else None,
            "running": {
                "id": running.id,
                "status": running.status,
                "mode": running.mode,
                "created_at": running.created_at.isoformat() if running.created_at else None,
                **(self._repo.get_self_study_run_progress(running.id) or {}),
            }
            if running
            else None,
            "recent_runs": [
                {
                    "id": r.id,
                    "trigger_type": r.trigger_type,
                    "mode": r.mode,
                    "status": r.status,
                    "files_total": r.files_total,
                    "files_processed": r.files_processed,
                    "error": r.error,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                }
                for r in runs
            ],
        }

    def list_self_study_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        rows = self._repo.list_self_study_runs(limit=limit)
        output: list[dict[str, Any]] = []
        for run in rows:
            files = self._repo.list_self_study_files(run.id, limit=300)
            output.append(
                {
                    "id": run.id,
                    "trigger_type": run.trigger_type,
                    "mode": run.mode,
                    "status": run.status,
                    "files_total": run.files_total,
                    "files_processed": run.files_processed,
                    "error": run.error,
                    "base_commit": run.base_commit,
                    "target_commit": run.target_commit,
                    "created_at": run.created_at.isoformat() if run.created_at else None,
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                    "files": [
                        {
                            "id": f.id,
                            "file_path": f.file_path,
                            "change_type": f.change_type,
                            "sha_before": f.sha_before,
                            "sha_after": f.sha_after,
                            "summary_status": f.summary_status,
                            "error": f.error,
                        }
                        for f in files
                    ],
                }
            )
        return output

    @staticmethod
    def _is_legacy_code_answer(answer: str) -> bool:
        normalized = (answer or "").strip().lower()
        if not normalized:
            return True
        markers = (
            "graph rag not initialized",
            "nao tenho acesso",
            "não tenho acesso",
            "nao encontrei citacoes rastreaveis",
            "não encontrei citações rastreáveis",
        )
        return any(marker in normalized for marker in markers)

    @staticmethod
    def _line_label(citation: dict[str, Any]) -> str:
        start = citation.get("line_start", citation.get("line"))
        end = citation.get("line_end")
        try:
            if start is None:
                return ""
            if end is None or int(end) == int(start):
                return str(int(start))
            return f"{int(start)}-{int(end)}"
        except Exception:
            return ""

    def _build_code_evidence_answer(
        self,
        *,
        question: str,
        citations: list[dict[str, Any]],
        self_memory: list[dict[str, Any]],
    ) -> str:
        by_file: dict[str, list[str]] = {}
        for citation in citations:
            path = str(citation.get("file_path") or "").strip()
            if not path:
                continue
            line = self._line_label(citation)
            by_file.setdefault(path, [])
            if line and line not in by_file[path]:
                by_file[path].append(line)

        if not by_file:
            return (
                "Nao encontrei evidencia suficiente no codigo para responder com seguranca. "
                "Reindexe/atualize o autoestudo e tente novamente."
            )

        top_files = list(by_file.items())[:5]
        file_segments: list[str] = []
        for path, lines in top_files:
            if lines:
                file_segments.append(f"{path}:{', '.join(lines[:4])}")
            else:
                file_segments.append(path)

        answer_parts = [
            (
                "Com base nas citacoes do codigo para a pergunta "
                f"\"{question}\", os pontos mais relevantes estao em: {'; '.join(file_segments)}."
            )
        ]
        if self_memory:
            first = self_memory[0]
            mem_path = str(first.get("file_path") or "").strip()
            mem_summary = str(first.get("summary") or "").strip()
            if mem_path and mem_summary:
                answer_parts.append(f"SelfMemory recente: {mem_path} -> {mem_summary}")
        answer_parts.append("Posso detalhar qualquer arquivo citado, linha por linha, se voce quiser.")
        return " ".join(answer_parts)

    async def ask_code_as_admin(self, *, question: str, limit: int = 10, citation_limit: int = 8) -> dict[str, Any]:
        question = (question or "").strip()
        if not question:
            raise AutonomyAdminServiceError("question is required")

        result = await self._knowledge_service.ask_code_with_citations(
            question=question,
            limit=limit,
            citation_limit=citation_limit,
        )
        citations_raw = result.get("citations") or []
        citations: list[dict[str, Any]] = []
        for c in citations_raw:
            rel = self._normalize_repo_path(c.get("file_path"))
            if not self._is_allowed_file_path(rel):
                continue
            item = dict(c)
            item["file_path"] = rel
            citations.append(item)

        if not citations:
            return {
                "answer": (
                    "Nao encontrei evidencia suficiente no codigo para responder com seguranca. "
                    "Reindexe/atualize o autoestudo e tente novamente."
                ),
                "citations": [],
                "self_memory": [],
            }

        # Enriquecer com memorias recentes de autoestudo
        memory_rows: list[dict[str, Any]] = []
        try:
            graph = await get_graph_db()
            tokens = [tok.lower() for tok in question.replace("/", " ").replace(":", " ").split() if len(tok) > 2]
            memory_rows = await graph.query(
                """
                MATCH (m:SelfMemory)
                WHERE any(prefix IN $allowed_prefixes WHERE m.file_path STARTS WITH prefix)
                  AND (
                    size($tokens) = 0
                    OR any(t IN $tokens WHERE toLower(m.summary) CONTAINS t OR toLower(m.file_path) CONTAINS t)
                  )
                RETURN m.file_path AS file_path, m.summary AS summary, m.updated_at AS updated_at
                ORDER BY m.updated_at DESC
                LIMIT 5
                """,
                {"tokens": tokens, "allowed_prefixes": [f"{p}/" for p in self.ALLOWED_ROOTS]},
                operation="admin_code_qa_self_memory",
            )
        except Exception as exc:
            logger.warning("admin_code_qa_self_memory_failed", error=str(exc))
        answer = str(result.get("answer") or "").strip()
        if self._is_legacy_code_answer(answer):
            answer = self._build_code_evidence_answer(
                question=question,
                citations=citations[:citation_limit],
                self_memory=memory_rows,
            )
        return {
            "answer": answer,
            "citations": citations[:citation_limit],
            "self_memory": memory_rows,
        }

    async def startup_self_study_check(self) -> dict[str, Any]:
        state = self._repo.get_self_study_state()
        head = self._get_head_commit()
        if not head:
            return {"status": "skipped", "reason": "git_head_unavailable"}
        if state.last_studied_commit == head:
            return {"status": "ok", "reason": "already_up_to_date", "head": head}
        return await self.run_self_study(
            mode="incremental",
            reason="startup_gap_check",
            trigger_type="startup",
        )


def get_autonomy_admin_service(request: Request) -> AutonomyAdminService:
    service = getattr(request.app.state, "autonomy_admin_service", None)
    if service is None:
        service = AutonomyAdminService(
            llm_service=request.app.state.llm_service,
            knowledge_service=request.app.state.knowledge_service,
        )
        request.app.state.autonomy_admin_service = service
    return service


async def maybe_trigger_self_study_on_goal_completion(
    *,
    app: Any | None,
    reason: str,
    trigger_type: str = "goal_completed",
) -> None:
    if app is None:
        return
    try:
        service = getattr(app.state, "autonomy_admin_service", None)
        if service is None:
            llm_service = getattr(app.state, "llm_service", None)
            knowledge_service = getattr(app.state, "knowledge_service", None)
            if llm_service is None or knowledge_service is None:
                return
            service = AutonomyAdminService(llm_service=llm_service, knowledge_service=knowledge_service)
            app.state.autonomy_admin_service = service
        await service.run_self_study(
            mode="incremental",
            reason=reason,
            trigger_type=trigger_type,
        )
    except Exception as e:
        logger.warning("self_study_trigger_failed", error=str(e))
