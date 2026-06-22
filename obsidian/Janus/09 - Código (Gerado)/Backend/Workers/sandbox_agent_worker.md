---
tipo: codigo
dominio: backend
camada: workers
gerado: true
origem: "backend/app/core/workers/sandbox_agent_worker.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# sandbox_agent_worker

## Objetivo
Sandbox Agent Worker

## Arquivos-fonte
- `backend/app/core/workers/sandbox_agent_worker.py`

## Filas/loops observáveis
- `JANUS.tasks.agent.sandbox`
- `QueueName.TASKS_AGENT_SANDBOX`

## Símbolos
- function: `_build_command_for_code(code: str)` -> `list`
  - Monta comando `python -c` que decodifica o código via base64 e executa.
Evita problemas de quoting/escape e mantém a jaula sem volumes/FS.
- function: `_run_in_docker(code: str)` -> `tuple[str, str]`
  - Executa o código em um contentor Docker altamente restrito.
Retorna (stdout, stderr). Em caso de falha estrutural, stderr conterá a causa.
- function: `process_sandbox_task(task: TaskMessage)` -> `None`
- function: `start_sandbox_agent_worker()`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
