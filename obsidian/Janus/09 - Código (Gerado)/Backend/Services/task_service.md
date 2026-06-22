---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/task_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# task_service

## Arquivos-fonte
- `backend/app/services/task_service.py`

## Dependências de código
- Repositórios
  - `task_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/exception_handlers.py`
- `backend/app/api/v1/endpoints/tasks.py`
- `backend/app/core/kernel.py`

## Símbolos
- class: `TaskServiceError`
  - Base exception for task service errors.
- class: `BrokerConnectionError`
  - Raised when the message broker is not available.
- class: `TaskService`
  - Camada de serviço para tarefas assíncronas.
Orquestra a lógica de negócio, recebendo suas dependências via DI.
- method: `TaskService.__init__(self, repo: TaskRepository)`
- method: `TaskService.create_consolidation_task(self, mode: str, limit: int | None, experience_id: str | None, experience_content: str | None, metadata: dict | None)` -> `str`
  - Cria a mensagem da tarefa e a delega para o repositório publicar.
- method: `TaskService.get_queue_details(self, queue_name: str)` -> `dict[str, Any]`
  - Delega a busca de detalhes da fila para o repositório.
- method: `TaskService.check_broker_health(self)` -> `bool`
  - Delega a verificação de saúde do broker para o repositório.
- method: `TaskService.get_queue_policy(self, queue_name: str)` -> `dict[str, Any]`
  - Delega ao repositório a consulta da política/argumentos da fila.
- method: `TaskService.validate_queue_policy(self, queue_name: str)` -> `dict[str, Any]`
  - Valida argumentos atuais da fila contra configuração esperada.
- method: `TaskService.reconcile_queue_policy(self, queue_name: str, force_delete: bool = True)` -> `dict[str, Any]`
  - Reconcilia política (deleta e recria fila se divergente).
- function: `get_task_service(request: Request)` -> `TaskService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
