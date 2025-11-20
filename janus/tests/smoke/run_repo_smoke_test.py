import sys
import json
import time
from urllib import request, error


BASE_URL = "http://localhost:8000"


def _req(method: str, path: str, data: dict | None = None, headers: dict | None = None):
    url = BASE_URL + path
    body = None
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    if data is not None:
        body = json.dumps(data).encode("utf-8")
    req = request.Request(url=url, data=body, headers=hdrs, method=method.upper())
    try:
        with request.urlopen(req, timeout=10) as resp:
            ct = resp.headers.get("Content-Type", "application/json").lower()
            raw = resp.read()
            if ct.startswith("application/json"):
                return resp.status, json.loads(raw.decode())
            return resp.status, raw.decode()
    except error.HTTPError as e:
        try:
            raw = e.read()
            return e.code, raw.decode()
        except Exception:
            return e.code, str(e)
    except Exception as e:
        return 0, f"request_error: {e}"


def main():
    t0 = time.time()
    print("[SMOKE] Iniciando teste de ciclo completo")
    # 1. Health
    code, body = _req("GET", "/healthz")
    if code != 200 or (isinstance(body, dict) and body.get("status") != "ok"):
        print(f"[FAIL] /healthz -> {code} {body}")
        sys.exit(1)
    print("[OK] /healthz")

    # 2. Criar usuário
    code, body = _req("POST", "/api/v1/users", {"email": "smoke@example.com", "display_name": "Smoke Test"})
    if code != 200 or not isinstance(body, dict) or "id" not in body:
        print(f"[FAIL] /api/v1/users -> {code} {body}")
        sys.exit(1)
    user_id = int(body["id"])
    print(f"[OK] create user id={user_id}")

    # 3. Consentimento para calendar.write
    code, body = _req(
        "POST",
        f"/api/v1/users/{user_id}/consents",
        {"scope": "calendar.write", "granted": True, "expires_at": None},
        headers={"X-User-Id": str(user_id)},
    )
    if code != 200:
        print(f"[FAIL] add consent -> {code} {body}")
        sys.exit(1)
    print("[OK] consent calendar.write")

    # 4. Adicionar evento de calendário
    evt = {
        "user_id": user_id,
        "event": {
            "title": "Smoke Event",
            "start_ts": time.time() + 60,
            "end_ts": time.time() + 3600,
            "location": "Remote",
            "notes": "smoke",
        },
        "index": False,
    }
    code, body = _req("POST", "/api/v1/productivity/calendar/events/add", evt, headers={"X-User-Id": str(user_id)})
    if code != 200 or not (isinstance(body, dict) and body.get("status") == "queued"):
        print(f"[FAIL] calendar add -> {code} {body}")
        sys.exit(1)
    print("[OK] calendar add queued")

    # 5. Listar eventos (pode estar vazio, não falha)
    code, body = _req("GET", f"/api/v1/productivity/calendar/events?user_id={user_id}", headers={"X-User-Id": str(user_id)})
    if code != 200:
        print(f"[WARN] calendar list -> {code} {body}")
    else:
        print("[OK] calendar list")

    elapsed = time.time() - t0
    print(f"[SMOKE] Concluído em {elapsed:.2f}s")
    sys.exit(0)


if __name__ == "__main__":
    main()
from pathlib import Path
import asyncio

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "janus"))

from app.repositories.knowledge_repository import KnowledgeRepository
from app.models.schemas import GraphRelationship


class _Result:
    async def single(self):
        return None


class _Tx:
    def __init__(self, sink):
        self.sink = sink

    async def run(self, query, **kwargs):
        self.sink.append(query)
        return _Result()

    async def commit(self):
        pass


class _Session:
    def __init__(self, sink):
        self.sink = sink

    async def begin_transaction(self):
        return _Tx(self.sink)

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


class FakeGraphDB:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.sink = []

    async def query(self, cypher_query: str, params: dict = None, operation: str | None = None):
        return self.responses.get(operation or "", [])

    async def execute(self, cypher_query: str, params: dict = None, operation: str | None = None):
        self.sink.append(cypher_query)

    async def get_session(self):
        return _Session(self.sink)

    async def register_relationship_type(self, tx_or_session, rel_type: str):
        self.sink.append(f"REGISTER {rel_type}")


async def main():
    try:
        responses = {
            "repo_dedupe_concepts_scan": [{"name": "ConceptX", "cs": [1, 2]}],
            "repo_dedupe_functions_scan": [{"name": "fn", "fp": "/path", "fs": [1, 2]}],
            "repo_dedupe_classes_scan": [{"name": "Cls", "fp": "/path", "cs": [3, 4]}],
            "repo_dedupe_files_scan": [{"p": "/path", "fs": [1, 2]}],
        }
        db = FakeGraphDB(responses)
        repo = KnowledgeRepository(db)

        rc = await repo.dedupe_concepts()
        rfc = await repo.dedupe_functions_and_classes()
        rf = await repo.dedupe_files()
        await repo.bulk_merge_calls([
            {"caller_name": "a", "callee_name": "b", "file_path": "/p"},
        ])

        q = "\n".join(db.sink)
        assert f"`{GraphRelationship.RELATES_TO.value}`" in q
        assert f"`{GraphRelationship.CALLS.value}`" in q
        assert f"`{GraphRelationship.IMPLEMENTS.value}`" in q

        print({
            "concepts": rc,
            "fn_cls": rfc,
            "files": rf,
        })
        return 0
    except Exception as e:
        print("SMOKE_TEST_ERROR", str(e))
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))