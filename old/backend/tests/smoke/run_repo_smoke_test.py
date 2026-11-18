import json
import os
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
    token = str(os.getenv("JANUS_USER_ACCESS_TOKEN") or "").strip()
    if not token:
        print("[FAIL] JANUS_USER_ACCESS_TOKEN is required; obtain it from the configured OIDC IdP")
        sys.exit(2)
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 1. Authenticated user-profile health
    code, body = _req("GET", "/healthz/user", headers=auth_headers)
    if code != 200 or (isinstance(body, dict) and body.get("status") != "ok"):
        print(f"[FAIL] /healthz/user -> {code} {body}")
        sys.exit(1)
    print("[OK] /healthz/user")

    # 2. Resolve the JIT-provisioned identity.
    code, body = _req("GET", "/api/v1/users/me", headers=auth_headers)
    if code != 200 or not isinstance(body, dict) or "id" not in body:
        print(f"[FAIL] /api/v1/users/me -> {code} {body}")
        sys.exit(1)
    user_id = body["id"]
    print(f"[OK] register user id={user_id}")

    # 3. Read the user-safe system status; operational status remains control-plane only.
    code, body = _req("GET", "/api/v1/system/status/user", headers=auth_headers)
    if code != 200:
        print(f"[FAIL] user system status -> {code} {body}")
        sys.exit(1)
    print("[OK] user system status")

    elapsed = time.time() - t0
    print(f"[SMOKE] Concluído em {elapsed:.2f}s")
    sys.exit(0)


if __name__ == "__main__":
    main()
