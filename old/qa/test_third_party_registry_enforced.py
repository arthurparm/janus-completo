import json
import re
from pathlib import Path
from urllib.parse import urlparse


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_registry() -> dict:
    path = _repo_root() / "documentation" / "compliance" / "third-parties-register.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _registry_sets(registry: dict) -> tuple[set[str], set[str]]:
    provider_keys: set[str] = set()
    hosts: set[str] = set()
    for item in registry.get("providers") or []:
        for k in item.get("provider_keys") or []:
            provider_keys.add(str(k).strip())
        for h in item.get("hosts") or []:
            hosts.add(str(h).strip().lower().strip("."))
    return provider_keys, hosts


def _extract_llm_provider_keys() -> set[str]:
    from app.config import settings
    from app.core.llm.router import LLMFactory, RouterSelection
    from app.core.llm.types import ModelPriority, ModelRole

    selection = RouterSelection(role=ModelRole.ORCHESTRATOR, priority=ModelPriority.FAST_AND_CHEAP)
    factory = LLMFactory(selection)

    keys: set[str] = set()
    for item in factory.cloud_catalog():
        keys.add(str(item.get("provider_key") or "").strip())

    if getattr(settings, "OPENROUTER_BASE_URL", None):
        keys.add("openrouter")

    return {k for k in keys if k and k not in {"ollama", "unknown"}}


def _extract_oauth_provider_keys() -> set[str]:
    root = _repo_root()
    targets = [
        root / "backend" / "app" / "api" / "v1" / "endpoints" / "productivity.py",
        root / "backend" / "app" / "core" / "workers" / "google_productivity_worker.py",
        root / "backend" / "app" / "api" / "v1" / "endpoints" / "auth.py",
    ]
    providers: set[str] = set()
    for path in targets:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r'provider\s*=\s*"([^"]+)"', text):
            providers.add(match.group(1).strip())
        for match in re.finditer(r'provider\s*=\s*\'([^\']+)\'', text):
            providers.add(match.group(1).strip())
        for match in re.finditer(r'provider\s*:\s*"([^"]+)"', text):
            providers.add(match.group(1).strip())
    return {p for p in providers if p and p not in {"janus"}}


def _extract_third_party_hosts(monkeypatch) -> set[str]:
    from app.config import settings
    from app.core.security import egress_policy

    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_ID", "x", raising=False)
    monkeypatch.setattr(settings, "GOOGLE_OAUTH_CLIENT_SECRET", "x", raising=False)
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "x", raising=False)
    monkeypatch.setattr(settings, "DEEPSEEK_API_KEY", "x", raising=False)
    monkeypatch.setattr(settings, "XAI_API_KEY", "x", raising=False)
    monkeypatch.setattr(settings, "TAVILY_API_KEY", "x", raising=False)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "x", raising=False)

    hosts = {str(h).strip().lower().strip(".") for h in egress_policy._default_external_worker_hosts()}

    openrouter_base = str(getattr(settings, "OPENROUTER_BASE_URL", "") or "")
    if openrouter_base:
        parsed = urlparse(openrouter_base)
        if parsed.hostname:
            hosts.add(str(parsed.hostname).strip().lower().strip("."))

    hosts.add("api.tavily.com")
    hosts.add("generativelanguage.googleapis.com")
    hosts.add("identitytoolkit.googleapis.com")
    hosts.add("securetoken.googleapis.com")

    return {h for h in hosts if h}


def test_third_party_inventory_registry_is_enforced(monkeypatch):
    registry = _load_registry()
    reg_provider_keys, reg_hosts = _registry_sets(registry)

    used_provider_keys = set()
    used_provider_keys |= _extract_llm_provider_keys()
    used_provider_keys |= _extract_oauth_provider_keys()

    missing_keys = sorted(k for k in used_provider_keys if k not in reg_provider_keys)
    assert not missing_keys, f"Missing provider_keys in third-party registry: {missing_keys}"

    used_hosts = _extract_third_party_hosts(monkeypatch)
    missing_hosts = sorted(h for h in used_hosts if h not in reg_hosts)
    assert not missing_hosts, f"Missing hosts in third-party registry: {missing_hosts}"
