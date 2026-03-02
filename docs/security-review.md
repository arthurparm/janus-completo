# Weekly Security & LGPD Review

**Date:** 2026-03-02
**Status:** In Progress

## Scope
This review focuses on identifying and mitigating security and privacy (LGPD) risks across the codebase.

## Findings

### PII in Logs
- **Risk:** Several `logger.info` statements log PII or sensitive message content (e.g., in `seed_graph.py`, `daemon.py`, `sync_events.py`, etc.).
- **Action:** Scrub logs for `user_id`, `email`, `password`, `message`, `feedback`, `cpf`, `cnpj`, `card`, `ip`. Implement log sanitization before writing to log sinks.

### Missing Validations / Lax Permissions
- **Risk:** `X-User-Id` header is widely used across endpoints (59+ instances) to determine the actor, often directly from `request.headers.get("X-User-Id")`. If `AUTH_TRUST_X_USER_ID_HEADER=True` (default in some configs), this allows trivial authentication bypass/impersonation.
- **Action:** Ensure `X-User-Id` is strictly verified or replaced with a secure JWT claim. Add validation for the `actor` in all these endpoints.

### Endpoints without Rate Limiting
- **Risk:** No explicit `@limiter.limit` decorators are found in the application code, particularly in sensitive endpoints like `/api/v1/auth/local/login`.
- **Action:** Implement explicit rate limiting, especially on authentication and heavy API endpoints, to prevent brute-force attacks.

### Hardcoded Secrets / Default Credentials
- **Risk:** Potential default passwords (`RABBITMQ_PASSWORD`, `NEO4J_PASSWORD`, `POSTGRES_PASSWORD`) may exist in `config.py` without sufficient production validation.
- **Action:** Validate config on startup; fail if default passwords are used in production environments.

### Vulnerable Dependencies
- **Risk:** `requirements.txt` uses broad version ranges and lacks a lock file, posing stability and supply-chain risks.
- **Action:** Transition to pinned versions or a lock file (e.g., `pip-compile` or `poetry`).

## Recommendations
1. Enforce strict redaction on `logger.info` to avoid PII leaks.
2. Deprecate direct usage of `X-User-Id` header for authorization; use signed tokens.
3. Add rate limiting to all authentication endpoints.
4. Pin dependencies in `requirements.txt`.
