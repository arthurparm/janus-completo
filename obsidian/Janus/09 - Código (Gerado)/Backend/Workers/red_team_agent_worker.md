---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/red_team_agent_worker.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# red_team_agent_worker

## Arquivos-fonte
- `backend/app/core/workers/red_team_agent_worker.py`

## Filas/loops observáveis
- `QueueName.TASKS_AGENT_RED_TEAM`

## Símbolos
- function: `_build_security_prompt(goal: str, context: str, code_snippets: dict)` -> `str`
- function: `_is_vulnerable(text: str)` -> `bool`
- function: `_extract_json_payload(text: str)` -> `dict[str, Any] | None`
- function: `_normalize_severity(value: Any)` -> `str`
- function: `_normalize_findings(items: Any)` -> `list[dict[str, Any]]`
- function: `_parse_security_assessment(response_text: str)` -> `tuple[str, list[dict[str, Any]], str]`
- function: `process_red_team_task(task: TaskMessage)` -> `None`
- function: `start_red_team_agent_worker()`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
