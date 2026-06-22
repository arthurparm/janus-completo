---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "tooling/qa_request_support.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# qa_request_support

## Arquivos-fonte
- `tooling/qa_request_support.py`

## Símbolos
- function: `utc_now()` -> `datetime`
- function: `isoformat_utc(dt: datetime)` -> `str`
- function: `generate_request_id(prefix: str, phase: str, suite: str, seq: int)` -> `str`
- function: `sanitize_headers(headers: dict[str, str])` -> `dict[str, str]`
- function: `classify_gate(result_class: str, log_evidence: str)` -> `str`
- function: `classify_http_status(status: int, expected_statuses: list[int] | None = None, *, phase: str = 'auth', path: str = '', notes: str = '')` -> `str`
- function: `is_env_blocked_expected(*, path: str, status: int, notes: str = '')` -> `bool`
- class: `DockerLogEvidence`
- class: `DockerLogCorrelator`
- method: `DockerLogCorrelator.__init__(self, *, service: str = 'janus-api', container: str = 'janus_api', grace_log_ms: int = 400, since_padding_sec: int = 1, include_weak_fallback: bool = True)` -> `None`
- method: `DockerLogCorrelator._run(self, cmd: list[str])` -> `tuple[int, str]`
- method: `DockerLogCorrelator._fetch_logs_since(self, since_dt: datetime)` -> `tuple[str, str]`
- method: `DockerLogCorrelator.correlate(self, *, request_id: str, method: str, path: str, phase: str, suite: str, t0: datetime, response_echo_request_id: str | None = None)` -> `DockerLogEvidence`
- function: `bootstrap_local_auth(*, base_url: str, timeout: float = 20.0, session: requests.Session | None = None, request_id_prefix: str = 'qa-bootstrap')` -> `dict[str, Any]`
- function: `_safe_json(resp: requests.Response)` -> `Any`
- function: `_redact_sensitive(payload: Any)` -> `Any`
- function: `save_json(path: str | Any, payload: Any)` -> `None`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
