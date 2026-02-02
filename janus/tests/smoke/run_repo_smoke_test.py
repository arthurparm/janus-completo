import json
import sys
import time
from urllib import error, request

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
    code, body = _req(
        "POST", "/api/v1/users", {"email": "smoke@example.com", "display_name": "Smoke Test"}
    )
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
    code, body = _req(
        "POST", "/api/v1/productivity/calendar/events/add", evt, headers={"X-User-Id": str(user_id)}
    )
    if code != 200 or not (isinstance(body, dict) and body.get("status") == "queued"):
        print(f"[FAIL] calendar add -> {code} {body}")
        sys.exit(1)
    print("[OK] calendar add queued")

    # 5. Listar eventos (pode estar vazio, não falha)
    code, body = _req(
        "GET",
        f"/api/v1/productivity/calendar/events?user_id={user_id}",
        headers={"X-User-Id": str(user_id)},
    )
    if code != 200:
        print(f"[WARN] calendar list -> {code} {body}")
    else:
        print("[OK] calendar list")

    elapsed = time.time() - t0
    print(f"[SMOKE] Concluído em {elapsed:.2f}s")
    sys.exit(0)


if __name__ == "__main__":
    main()
