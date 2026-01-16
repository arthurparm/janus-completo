import json
import re
from typing import Any

UI_TAG_RE = re.compile(
    r"<janus-ui\\s+type\\s*=\\s*['\"]([^'\"]+)['\"][^>]*>(.*?)</janus-ui>",
    re.IGNORECASE | re.DOTALL,
)

ALLOWED_UI_TYPES = {"table"}
MAX_UI_JSON_BYTES = 100_000


def extract_ui_block(text: str) -> tuple[str, dict[str, Any] | None]:
    if not text:
        return text, None

    matches = list(UI_TAG_RE.finditer(text))
    if not matches:
        return text, None

    clean_text = UI_TAG_RE.sub("", text).strip()
    first = matches[0]
    ui_type = first.group(1).strip().lower()
    json_payload = (first.group(2) or "").strip()

    if not json_payload or ui_type not in ALLOWED_UI_TYPES:
        return clean_text, None

    if len(json_payload.encode("utf-8")) > MAX_UI_JSON_BYTES:
        return clean_text, None

    try:
        data = json.loads(json_payload)
    except Exception:
        return clean_text, None

    return clean_text, {"type": ui_type, "data": data}
