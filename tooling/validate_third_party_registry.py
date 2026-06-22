import json
import sys
from pathlib import Path


_ALLOWED_CATEGORIES = {"llm", "oauth", "web_search", "auth", "infra_external", "analytics"}


def _read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _validate_registry(repo_root: Path, registry_path: Path) -> list[str]:
    errors: list[str] = []
    payload = _read_json(registry_path)
    if str(payload.get("classification") or "").strip() != "internal-only":
        errors.append("classification must be 'internal-only'")
    providers = payload.get("providers") or []
    if not isinstance(providers, list):
        return ["providers must be a list"]

    ids: set[str] = set()
    provider_keys: set[str] = set()
    hosts: set[str] = set()

    for item in providers:
        if not isinstance(item, dict):
            errors.append("provider entry must be an object")
            continue
        pid = str(item.get("id") or "").strip()
        if not pid:
            errors.append("provider missing id")
        elif pid in ids:
            errors.append(f"duplicate id: {pid}")
        ids.add(pid)

        category = str(item.get("category") or "").strip()
        if category not in _ALLOWED_CATEGORIES:
            errors.append(f"{pid or '<missing-id>'}: invalid category '{category}'")

        pkeys = item.get("provider_keys") or []
        if not isinstance(pkeys, list) or not pkeys:
            errors.append(f"{pid or '<missing-id>'}: provider_keys must be a non-empty list")
        else:
            for k in pkeys:
                key = str(k or "").strip()
                if not key:
                    errors.append(f"{pid}: empty provider_key")
                    continue
                if key in provider_keys:
                    errors.append(f"duplicate provider_key: {key}")
                provider_keys.add(key)

        host_list = item.get("hosts") or []
        if not isinstance(host_list, list):
            errors.append(f"{pid}: hosts must be a list")
        else:
            for h in host_list:
                host = str(h or "").strip().lower().strip(".")
                if not host:
                    errors.append(f"{pid}: empty host")
                    continue
                if host in hosts:
                    errors.append(f"duplicate host: {host}")
                hosts.add(host)

        for rel_path in item.get("code_refs") or []:
            if not isinstance(rel_path, str):
                continue
            target = (repo_root / rel_path).resolve()
            if not target.exists():
                errors.append(f"{pid}: missing code_refs file {rel_path}")

    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    registry_path = repo_root / "documentation" / "compliance" / "third-parties-register.json"
    if len(sys.argv) > 1:
        registry_path = (repo_root / sys.argv[1]).resolve()

    if not registry_path.exists():
        print(f"Registry not found: {registry_path}", file=sys.stderr)
        return 2

    errors = _validate_registry(repo_root=repo_root, registry_path=registry_path)
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

