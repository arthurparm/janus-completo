---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "backend/scripts/benchmark_complex_process.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# benchmark_complex_process

## Objetivo
Benchmark average tokens for a "complex process" by running an API call and
aggregating LLM token usage from audit_events by trace_id.

## Arquivos-fonte
- `backend/scripts/benchmark_complex_process.py`

## Símbolos
- class: `TokenSample`
- function: `_load_env_file(path: Path)` -> `Dict[str, str]`
- function: `_get_setting(env: Dict[str, str], key: str, default: Optional[str])` -> `Optional[str]`
- function: `_require_requests()` -> `None`
- function: `_require_psycopg()` -> `None`
- function: `_post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: float)` -> `Dict[str, Any]`
- function: `_start_conversation(base_url: str, user_id: str, project_id: Optional[str], timeout: float)` -> `str`
- function: `_send_chat_message(base_url: str, conversation_id: str, message: str, role: str, priority: str, timeout_seconds: Optional[int], user_id: str, project_id: Optional[str], headers: Dict[str, str], timeout: float)` -> `Dict[str, Any]`
- function: `_invoke_llm(base_url: str, prompt: str, role: str, priority: str, timeout_seconds: Optional[int], user_id: str, project_id: Optional[str], headers: Dict[str, str], timeout: float)` -> `Dict[str, Any]`
- function: `_connect_db(host: str, port: int, user: str, password: str, dbname: str)` -> `Any`
- function: `_query_tokens_for_trace(conn: Any, trace_id: str)` -> `Tuple[int, int, int, float]`
- function: `_wait_for_tokens(conn: Any, trace_id: str, retries: int, delay_s: float)` -> `Tuple[int, int, int, float]`
- function: `_read_prompt(prompt_arg: Optional[str], prompt_file: Optional[str])` -> `str`
- function: `_summarize(samples: Iterable[TokenSample])` -> `Dict[str, float]`
- function: `_parse_args()` -> `argparse.Namespace`
- function: `main()` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
