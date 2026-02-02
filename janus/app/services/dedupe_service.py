import json
import os
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import db
from app.db.graph import GraphDatabase, get_graph_db
from app.db.vector_store import async_count_points, get_async_qdrant_client
from app.repositories.knowledge_repository import KnowledgeRepository

logger = structlog.get_logger(__name__)


class DedupeError(Exception):
    """Erro base para falhas no serviço de deduplicação."""

    pass


class DedupeService:
    def __init__(self, db_session: Session | None = None, graph_db: GraphDatabase | None = None):
        self._db_session = db_session
        self._graph_db = graph_db

    def _get_session(self) -> Session:
        return self._db_session or db.get_session_direct()

    async def _get_graph(self) -> GraphDatabase:
        return self._graph_db or get_graph_db()

    def detect_db_duplicates(self) -> dict[str, Any]:
        s = self._get_session()
        try:
            dup_users_email = s.execute(
                text(
                    "SELECT email, COUNT(*) as cnt FROM users WHERE email IS NOT NULL GROUP BY email HAVING COUNT(*) > 1"
                )
            ).fetchall()
            dup_users_ext = s.execute(
                text(
                    "SELECT external_id, COUNT(*) as cnt FROM users WHERE external_id IS NOT NULL GROUP BY external_id HAVING COUNT(*) > 1"
                )
            ).fetchall()
            dup_experiments = s.execute(
                text(
                    "SELECT name, user_id, COUNT(*) as cnt FROM experiments GROUP BY name, user_id HAVING COUNT(*) > 1"
                )
            ).fetchall()
            return {
                "users_by_email": [dict(r) for r in dup_users_email],
                "users_by_external_id": [dict(r) for r in dup_users_ext],
                "experiments_by_name_user": [dict(r) for r in dup_experiments],
            }
        except SQLAlchemyError as e:
            logger.error("Falha ao detectar duplicatas no SQL", exc_info=e)
            raise DedupeError(f"Erro de banco de dados: {e}") from e
        finally:
            if self._db_session is None:
                s.close()

    def fix_db_duplicates(self) -> dict[str, Any]:
        s = self._get_session()
        report: dict[str, Any] = {"users": [], "experiments": []}
        try:
            # Usuários por email
            rows = s.execute(
                text(
                    "SELECT email FROM users WHERE email IS NOT NULL GROUP BY email HAVING COUNT(*) > 1"
                )
            ).fetchall()

            for r in rows:
                email = r[0]
                users = s.execute(
                    text(
                        "SELECT id, display_name, created_at FROM users WHERE email = :email ORDER BY created_at ASC"
                    ),
                    {"email": email},
                ).fetchall()

                if len(users) < 2:
                    continue

                canonical_id = users[0][0]
                dup_ids = [u[0] for u in users[1:]]

                # Remapear FKs
                for table in ["profiles", "sessions", "audit_events"]:
                    s.execute(
                        text(f"UPDATE {table} SET user_id = :canon WHERE user_id IN :dups"),
                        {"canon": canonical_id, "dups": tuple(dup_ids)},
                    )

                # Deletar duplicatas de tabelas dependentes
                for table in ["user_roles", "consents", "oauth_tokens"]:
                    s.execute(
                        text(f"DELETE FROM {table} WHERE user_id IN :dups"),
                        {"dups": tuple(dup_ids)},
                    )

                # Deletar usuário duplicado
                s.execute(text("DELETE FROM users WHERE id IN :dups"), {"dups": tuple(dup_ids)})

                report["users"].append(
                    {"email": email, "canonical_id": canonical_id, "removed": dup_ids}
                )

            # Experimentos por (name, user_id)
            rows = s.execute(
                text(
                    "SELECT name, user_id FROM experiments GROUP BY name, user_id HAVING COUNT(*) > 1"
                )
            ).fetchall()

            for r in rows:
                name, user_id = r[0], r[1]
                exps = s.execute(
                    text(
                        "SELECT id, created_at FROM experiments WHERE name = :name AND (user_id IS NULL OR user_id = :user_id) ORDER BY created_at ASC"
                    ),
                    {"name": name, "user_id": user_id},
                ).fetchall()

                if len(exps) < 2:
                    continue

                canon_id = exps[0][0]
                dup_ids = [e[0] for e in exps[1:]]

                for table in ["experiment_arms", "experiment_results", "experiment_feedback"]:
                    s.execute(
                        text(
                            f"UPDATE {table} SET experiment_id = :canon WHERE experiment_id IN :dups"
                        ),
                        {"canon": canon_id, "dups": tuple(dup_ids)},
                    )

                s.execute(
                    text("DELETE FROM experiments WHERE id IN :dups"), {"dups": tuple(dup_ids)}
                )

                report["experiments"].append(
                    {"name": name, "user_id": user_id, "canonical_id": canon_id, "removed": dup_ids}
                )

            s.commit()
            return report
        except SQLAlchemyError as e:
            s.rollback()
            logger.error("Falha ao corrigir duplicatas no SQL", exc_info=e)
            raise DedupeError(f"Erro de transação SQL: {e}") from e
        finally:
            if self._db_session is None:
                s.close()

    async def dedupe_graph(self) -> dict[str, Any]:
        try:
            g = await self._get_graph()
            repo = KnowledgeRepository(g)
            concepts = await repo.dedupe_concepts()
            fn_cls = await repo.dedupe_functions_and_classes()
            files = await repo.dedupe_files()
            return {"concepts": concepts, "fn_cls": fn_cls, "files": files}
        except Exception as e:
            logger.error("Erro no processo de deduplicação do Grafo", exc_info=e)
            raise DedupeError(f"Falha no Grafo: {e}") from e

    async def detect_qdrant_duplicates(self, user_id: str | None = None) -> dict[str, Any]:
        try:
            client = get_async_qdrant_client()
            summary: dict[str, Any] = {"collections": []}
            from qdrant_client import models as _models

            colls: list[str] = []
            try:
                resp = await client.get_collections()
                colls = [
                    c.name
                    for c in getattr(resp, "collections", []) or []
                    if c.name.startswith("user_")
                ]
            except Exception as e:
                logger.warning("failed_to_list_qdrant_collections", error=str(e))
                # Aqui pode ser erro de conexão temporário, retornamos lista vazia mas logamos
                return {"error": str(e), "collections": []}

            for coll in colls:
                filt = [
                    _models.FieldCondition(
                        key="metadata.content_hash", match=_models.MatchAny(any=["*"])
                    )
                ]
                if user_id:
                    filt.append(
                        _models.FieldCondition(
                            key="metadata.user_id", match=_models.MatchValue(value=str(user_id))
                        )
                    )
                qf = _models.Filter(must=filt)

                try:
                    cnt = await async_count_points(client, coll, qf, exact=True)
                    summary["collections"].append({"name": coll, "with_hash": cnt})
                except Exception as e:
                    logger.debug("failed_to_count_qdrant_collection", collection=coll, error=str(e))
                    summary["collections"].append({"name": coll, "with_hash": 0, "error": str(e)})

            return summary

        except Exception as e:
            logger.error("Erro crítico na detecção de duplicatas do Qdrant", exc_info=e)
            raise DedupeError(f"Falha no Qdrant: {e}") from e

    def _write_report(self, data: dict[str, Any]) -> str:
        try:
            os.makedirs("reports", exist_ok=True)
            import datetime as _dt

            ts = _dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            path = os.path.join("reports", f"duplicates-{ts}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return path
        except Exception as e:
            logger.error("Falha ao salvar relatório de deduplicação", exc_info=e)
            return "failed_to_save_report"

    async def run(self, dry_run: bool = True) -> dict[str, Any]:
        report: dict[str, Any] = {"dry_run": dry_run, "db": {}, "neo4j": {}, "qdrant": {}}

        # SQL Cleanup
        try:
            report["db"]["detected"] = self.detect_db_duplicates()
            if not dry_run:
                report["db"]["fixed"] = self.fix_db_duplicates()
        except DedupeError as e:
            report["db"]["error"] = str(e)
        except Exception as e:
            report["db"]["error"] = f"Unexpected: {e}"

        # Graph Cleanup
        try:
            report["neo4j"]["fixed"] = await self.dedupe_graph()
        except DedupeError as e:
            report["neo4j"]["error"] = str(e)
        except Exception as e:
            report["neo4j"]["error"] = f"Unexpected: {e}"

        # Vector Cleanup
        try:
            report["qdrant"]["detected"] = self.detect_qdrant_duplicates()
        except DedupeError as e:
            report["qdrant"]["error"] = str(e)
        except Exception as e:
            report["qdrant"]["error"] = f"Unexpected: {e}"

        path = self._write_report(report)
        report["report_path"] = path
        return report
