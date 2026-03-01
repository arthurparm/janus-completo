# Security Review

## Checklist
- [x] Check for AuthZ on endpoints
- [x] Check for rate limiting on public/auth endpoints
- [x] Check for hardcoded secrets
- [x] Check for header validation (e.g. X-User-Id)
- [x] Check for vulnerable/unpinned dependencies

## Gaps Found

1. **AuthZ Missing on Workspace Endpoints**: The endpoints in `backend/app/api/v1/endpoints/workspace.py` rely on `Depends(get_collaboration_service)` which does not enforce authentication. This leaves endpoints like `add_artifact` and `shutdown_system` unprotected.
2. **Brute Force Risk on Auth Endpoints**: The `backend/app/api/v1/endpoints/auth.py` endpoints (login, refresh) lack rate limiting decorators (`@limiter.limit`), posing a brute-force attack risk.
3. **Hardcoded Secrets without Validation**: The `backend/app/config.py` file has hardcoded defaults for `NEO4J_PASSWORD`, `POSTGRES_PASSWORD`, and `RABBITMQ_PASSWORD` without validation logic to prevent their use in production environments.
4. **Trusted `X-User-Id` Header**: There is a critical vulnerability in `backend/app/core/infrastructure/auth.py` where the `X-User-Id` header is trusted without verification (enabled by default via `AUTH_TRUST_X_USER_ID_HEADER=True`), allowing authentication bypass/impersonation.
5. **Missing Dependency Lock**: The `backend/requirements.txt` file lacks a lock file and uses broad version ranges, posing a stability and security risk.

## Actionable Recommendations

- **Workspace Endpoints**: Add proper authentication dependencies (e.g., `get_current_user`) to all `workspace` endpoints.
- **Auth Rate Limiting**: Apply `@limiter.limit` decorators to `login` and `refresh` endpoints in `auth.py`.
- **Config Validation**: Implement a Pydantic validator in `backend/app/config.py` that raises an error if default passwords are used when the environment is not set to `development` or `test`.
- **Header Validation**: Disable `AUTH_TRUST_X_USER_ID_HEADER` by default or remove the trust entirely unless cryptographically signed. Enforce proper token validation instead.
- **Dependency Management**: Generate and commit a `requirements.lock` file or migrate to a tool like `pipenv` or `poetry` to pin dependency versions securely.
