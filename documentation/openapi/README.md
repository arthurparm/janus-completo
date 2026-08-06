# OpenAPI security profiles

The operation-level source of truth is
`backend/app/core/security/endpoint_policy_manifest.json`. Every entry contains the complete method,
full path, profile, principal type, scopes, ownership mode, operation ID and delegation flag. FastAPI
startup requires a bijection between that manifest and the registered routes before filtering the
active profile.

The three files under `current/` are generated from the manifest-backed executable routes and must
remain pairwise disjoint. Regenerate them with:

```bash
PYTHONPATH=backend python tooling/generate_security_openapi.py
```

CI reruns generation with `--check` and fails when a committed snapshot is stale. It also compares
against the target branch and blocks a new public operation, authentication removal, scope reduction,
or ownership removal. Changes in this directory require the security CODEOWNER.

When `APP_VERSION` changes after approval, archive the accepted baseline once:

```bash
PYTHONPATH=backend python tooling/generate_security_openapi.py --archive-version 0.5.45
```

An existing history entry may be reproduced byte-for-byte but cannot be changed to different content.
