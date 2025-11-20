import os
import json
import structlog
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.mysql_config import mysql_db
from app.db.graph import get_graph_db, GraphDatabase
from app.repositories.knowledge_repository import KnowledgeRepository
from app.db.vector_store import get_qdrant_client

logger = structlog.get_logger(__name__)


class DedupeService:
    def __init__(self, mysql_session: Optional[Session] = None, graph_db: Optional[GraphDatabase] = None):
        self._mysql_session = mysql_session
        self._graph_db = graph_db

    def _get_session(self) -> Session:
        return self._mysql_session or mysql_db.get_session_direct()

    async def _get_graph(self) -> GraphDatabase:
        return self._graph_db or get_graph_db()

    def detect_mysql_duplicates(self) -> Dict[str, Any]:
        s = self._get_session()
        try:
            dup_users_email = s.execute(text("SELECT email, COUNT(*) as cnt FROM users WHERE email IS NOT NULL GROUP BY email HAVING COUNT(*) > 1")).fetchall()
            dup_users_ext = s.execute(text("SELECT external_id, COUNT(*) as cnt FROM users WHERE external_id IS NOT NULL GROUP BY external_id HAVING COUNT(*) > 1")).fetchall()
            dup_experiments = s.execute(text("SELECT name, user_id, COUNT(*) as cnt FROM experiments GROUP BY name, user_id HAVING COUNT(*) > 1")).fetchall()
            return {
                "users_by_email": [dict(r) for r in dup_users_email],
                "users_by_external_id": [dict(r) for r in dup_users_ext],
                "experiments_by_name_user": [dict(r) for r in dup_experiments],
            }
        finally:
            if self._mysql_session is None:
                s.close()

    def fix_mysql_duplicates(self) -> Dict[str, Any]:
        s = self._get_session()
        report: Dict[str, Any] = {"users": [], "experiments": []}
        try:
            # Usuários por email
            rows = s.execute(text("SELECT email FROM users WHERE email IS NOT NULL GROUP BY email HAVING COUNT(*) > 1")).fetchall()
            for r in rows:
                email = r[0]
                users = s.execute(text("SELECT id, display_name, created_at FROM users WHERE email = :email ORDER BY created_at ASC"), {"email": email}).fetchall()
                if len(users) < 2:
                    continue
                canonical_id = users[0][0]
                dup_ids = [u[0] for u in users[1:]]
                # Remapear FKs (exemplos: profiles, sessions, audit_events)
                s.execute(text("UPDATE profiles SET user_id = :canon WHERE user_id IN :dups"), {"canon": canonical_id, "dups": tuple(dup_ids)})
                s.execute(text("UPDATE sessions SET user_id = :canon WHERE user_id IN :dups"), {"canon": canonical_id, "dups": tuple(dup_ids)})
                s.execute(text("UPDATE audit_events SET user_id = :canon WHERE user_id IN :dups"), {"canon": canonical_id, "dups": tuple(dup_ids)})
                s.execute(text("DELETE FROM user_roles WHERE user_id IN :dups"), {"dups": tuple(dup_ids)})
                s.execute(text("DELETE FROM consents WHERE user_id IN :dups"), {"dups": tuple(dup_ids)})
                s.execute(text("DELETE FROM oauth_tokens WHERE user_id IN :dups"), {"dups": tuple(dup_ids)})
                s.execute(text("DELETE FROM users WHERE id IN :dups"), {"dups": tuple(dup_ids)})
                report["users"].append({"email": email, "canonical_id": canonical_id, "removed": dup_ids})
            # Experimentos por (name, user_id)
            rows = s.execute(text("SELECT name, user_id FROM experiments GROUP BY name, user_id HAVING COUNT(*) > 1")).fetchall()
            for r in rows:
                name, user_id = r[0], r[1]
                exps = s.execute(text("SELECT id, created_at FROM experiments WHERE name = :name AND (user_id IS NULL OR user_id = :user_id) ORDER BY created_at ASC"), {"name": name, "user_id": user_id}).fetchall()
                if len(exps) < 2:
                    continue
                canon_id = exps[0][0]
                dup_ids = [e[0] for e in exps[1:]]
                s.execute(text("UPDATE experiment_arms SET experiment_id = :canon WHERE experiment_id IN :dups"), {"canon": canon_id, "dups": tuple(dup_ids)})
                s.execute(text("UPDATE experiment_results SET experiment_id = :canon WHERE experiment_id IN :dups"), {"canon": canon_id, "dups": tuple(dup_ids)})
                s.execute(text("UPDATE experiment_feedback SET experiment_id = :canon WHERE experiment_id IN :dups"), {"canon": canon_id, "dups": tuple(dup_ids)})
                s.execute(text("DELETE FROM experiments WHERE id IN :dups"), {"dups": tuple(dup_ids)})
                report["experiments"].append({"name": name, "user_id": user_id, "canonical_id": canon_id, "removed": dup_ids})
            s.commit()
            return report
        finally:
            if self._mysql_session is None:
                s.close()

    async def dedupe_graph(self) -> Dict[str, Any]:
        g = await self._get_graph()
        repo = KnowledgeRepository(g)
        concepts = await repo.dedupe_concepts()
        fn_cls = await repo.dedupe_functions_and_classes()
        files = await repo.dedupe_files()
        return {"concepts": concepts, "fn_cls": fn_cls, "files": files}

    def detect_qdrant_duplicates(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        client = get_qdrant_client()
        summary: Dict[str, Any] = {"collections": []}
        try:
            from qdrant_client import models as _models
            colls: List[str] = []
            # Heurística: coleções por usuário começam com 'user_'
            try:
                resp = client.get_collections()
                colls = [c.name for c in getattr(resp, "collections", []) or [] if c.name.startswith("user_")]
            except Exception:
                colls = []
            for coll in colls:
                filt = [_models.FieldCondition(key="metadata.content_hash", match=_models.MatchAny(any=["*"]))]
                if user_id:
                    filt.append(_models.FieldCondition(key="metadata.user_id", match=_models.MatchValue(value=str(user_id))))
                qf = _models.Filter(must=filt)
                # Não há group-by; contar total com content_hash preenchido
                try:
                    cnt = client.count(collection_name=coll, count_filter=qf, exact=True)
                    summary["collections"].append({"name": coll, "with_hash": int(getattr(cnt, "count", 0) or 0)})
                except Exception:
                    summary["collections"].append({"name": coll, "with_hash": 0})
        except Exception:
            logger.warning("Falha ao detectar duplicidades em Qdrant", exc_info=True)
        return summary

    def _write_report(self, data: Dict[str, Any]) -> str:
        os.makedirs("reports", exist_ok=True)
        import datetime as _dt
        ts = _dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        path = os.path.join("reports", f"duplicates-{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return path

    async def run(self, dry_run: bool = True) -> Dict[str, Any]:
        report: Dict[str, Any] = {"dry_run": dry_run, "mysql": {}, "neo4j": {}, "qdrant": {}}
        try:
            report["mysql"]["detected"] = self.detect_mysql_duplicates()
            if not dry_run:
                report["mysql"]["fixed"] = self.fix_mysql_duplicates()
        except Exception:
            logger.warning("Falha em dedupe MySQL", exc_info=True)
        try:
            report["neo4j"]["fixed"] = await self.dedupe_graph()
        except Exception:
            logger.warning("Falha em dedupe Neo4j", exc_info=True)
        try:
            report["qdrant"]["detected"] = self.detect_qdrant_duplicates()
        except Exception:
            logger.warning("Falha em dedupe Qdrant", exc_info=True)
        path = self._write_report(report)
        report["report_path"] = path
        return report