from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.security.redaction import redact_sensitive_payload


def _outbox_path() -> Path:
    configured = os.getenv("SECURITY_ALERT_OUTBOX_PATH", "").strip()
    return Path(configured or "outputs/security/security-alert-outbox.jsonl")


def _append_outbox(event: dict[str, Any]) -> None:
    path = _outbox_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def emit_security_alert(event_type: str, details: dict[str, Any]) -> bool:
    event = redact_sensitive_payload(
        {"event_type": event_type, "details": details, "occurred_at": int(time.time())}
    )
    if not isinstance(event, dict):
        event = {"event_type": event_type, "details": "[REDACTION_FAILED]"}
    _append_outbox(event)

    webhook = str(getattr(settings, "SECURITY_ALERT_WEBHOOK_URL", "") or "").strip()
    if not webhook:
        return False
    parsed = urllib.parse.urlparse(webhook)
    allowed = {str(host).lower() for host in (settings.SECURITY_ALERT_ALLOWED_HOSTS or [])}
    if parsed.scheme != "https" or not parsed.hostname or parsed.hostname.lower() not in allowed:
        return False

    body = json.dumps(event, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signing_key = str(getattr(settings, "SECURITY_ALERT_WEBHOOK_HMAC_KEY", "") or "")
    signature = hmac.new(signing_key.encode("utf-8"), body, hashlib.sha256).hexdigest()
    request = urllib.request.Request(
        webhook,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "X-Janus-Signature": signature},
    )
    for _attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=3) as response:
                if 200 <= int(response.status) < 300:
                    return True
        except Exception:
            continue
    return False
