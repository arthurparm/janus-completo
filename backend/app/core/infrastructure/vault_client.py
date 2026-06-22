from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from app.config import settings
from app.core.security.egress_policy import enforce_worker_http_egress

logger = structlog.get_logger(__name__)


@dataclass
class VaultToken:
    token: str
    expires_at: float | None = None


class VaultClient:
    def __init__(self) -> None:
        self._cached: VaultToken | None = None

    def _base_url(self) -> str:
        base = str(getattr(settings, "VAULT_ADDR", "") or "").strip().rstrip("/")
        if not base:
            raise RuntimeError("Vault is not configured (VAULT_ADDR missing).")
        allowed = enforce_worker_http_egress(base, tool="vault_client")
        if not allowed:
            raise RuntimeError("Vault egress blocked by policy.")
        return allowed.rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        namespace = str(getattr(settings, "VAULT_NAMESPACE", "") or "").strip()
        if namespace:
            headers["X-Vault-Namespace"] = namespace
        return headers

    def _get_token(self) -> str:
        token_secret = getattr(settings, "VAULT_TOKEN", None)
        if token_secret:
            return token_secret.get_secret_value()

        cached = self._cached
        now = time.time()
        if cached and cached.expires_at and cached.expires_at > now + 30:
            return cached.token

        method = str(getattr(settings, "VAULT_AUTH_METHOD", "approle") or "").strip().lower()
        if method != "approle":
            raise RuntimeError("Vault token is not configured and auth method is not approle.")

        role_id = str(getattr(settings, "VAULT_APPROLE_ROLE_ID", "") or "").strip()
        secret_id_secret = getattr(settings, "VAULT_APPROLE_SECRET_ID", None)
        if not role_id or not secret_id_secret:
            raise RuntimeError("Vault AppRole credentials are missing.")
        secret_id = secret_id_secret.get_secret_value()

        url = f"{self._base_url()}/v1/auth/approle/login"
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            resp = client.post(
                url,
                json={"role_id": role_id, "secret_id": secret_id},
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json() or {}

        auth = data.get("auth") or {}
        token = str(auth.get("client_token") or "").strip()
        lease_duration = auth.get("lease_duration")
        if not token:
            raise RuntimeError("Vault AppRole login did not return a token.")

        expires_at = None
        try:
            if lease_duration is not None:
                expires_at = now + float(lease_duration)
        except Exception:
            expires_at = None

        self._cached = VaultToken(token=token, expires_at=expires_at)
        return token

    def _request(self, method: str, path: str, *, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self._base_url()}{path}"
        headers = dict(self._headers())
        headers["X-Vault-Token"] = self._get_token()
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            resp = client.request(method, url, json=json_body, headers=headers)
            resp.raise_for_status()
            return resp.json() or {}

    def transit_encrypt(self, *, plaintext: str) -> str:
        mount = str(getattr(settings, "VAULT_TRANSIT_MOUNT", "transit") or "transit").strip().strip("/")
        key_name = str(getattr(settings, "VAULT_TRANSIT_KEY_NAME", "") or "").strip()
        if not key_name:
            raise RuntimeError("Vault transit key name is missing (VAULT_TRANSIT_KEY_NAME).")
        b64_plain = base64.b64encode(plaintext.encode("utf-8")).decode("utf-8")
        payload = {"plaintext": b64_plain}
        data = self._request("POST", f"/v1/{mount}/encrypt/{key_name}", json_body=payload)
        out = (data.get("data") or {}).get("ciphertext")
        ciphertext = str(out or "").strip()
        if not ciphertext:
            raise RuntimeError("Vault transit encrypt did not return ciphertext.")
        return ciphertext

    def transit_decrypt(self, *, ciphertext: str) -> str:
        mount = str(getattr(settings, "VAULT_TRANSIT_MOUNT", "transit") or "transit").strip().strip("/")
        key_name = str(getattr(settings, "VAULT_TRANSIT_KEY_NAME", "") or "").strip()
        if not key_name:
            raise RuntimeError("Vault transit key name is missing (VAULT_TRANSIT_KEY_NAME).")
        payload = {"ciphertext": ciphertext}
        data = self._request("POST", f"/v1/{mount}/decrypt/{key_name}", json_body=payload)
        out = (data.get("data") or {}).get("plaintext")
        b64_plain = str(out or "").strip()
        if not b64_plain:
            raise RuntimeError("Vault transit decrypt did not return plaintext.")
        return base64.b64decode(b64_plain.encode("utf-8")).decode("utf-8")

    def transit_rotate(self) -> dict[str, Any]:
        mount = str(getattr(settings, "VAULT_TRANSIT_MOUNT", "transit") or "transit").strip().strip("/")
        key_name = str(getattr(settings, "VAULT_TRANSIT_KEY_NAME", "") or "").strip()
        if not key_name:
            raise RuntimeError("Vault transit key name is missing (VAULT_TRANSIT_KEY_NAME).")
        return self._request("POST", f"/v1/{mount}/keys/{key_name}/rotate", json_body={})


vault_client = VaultClient()

