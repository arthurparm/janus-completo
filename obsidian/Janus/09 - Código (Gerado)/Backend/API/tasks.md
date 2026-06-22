---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/tasks.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# tasks

## Arquivos-fonte
- `backend/app/api/v1/endpoints/tasks.py`

## Rotas
- `GET /health/rabbitmq`
- `GET /outbox/stats`
- `GET /queue/{queue_name}`
- `GET /queue/{queue_name}/policy`
- `GET /queue/{queue_name}/policy/validate`
- `POST /consolidation`
- `POST /outbox/reconcile`
- `POST /queue/{queue_name}/policy/reconcile`

## Dependências de código
- Serviços
  - `task_service`

## Símbolos
- class: `ConsolidationTaskRequest`
- class: `TaskResponse`
- class: `QueueInfoResponse`
- class: `QueuePolicyResponse`
- class: `QueuePolicyValidationResponse`
- class: `ReconcilePolicyRequest`
- class: `ReconcilePolicyResponse`
- class: `OutboxStatsResponse`
- class: `OutboxReconcileRequest`
- class: `OutboxReconcileResponse`
- function: `create_consolidation_task(request: ConsolidationTaskRequest, service: TaskService = Depends(get_task_service), http_request: Request = None)`
  - Delega a publicação de uma tarefa de consolidação para o TaskService.
- function: `get_queue_info(queue_name: str, service: TaskService = Depends(get_task_service))`
  - Delega a busca de informações da fila para o TaskService.
- function: `check_rabbitmq_health(service: TaskService = Depends(get_task_service), request: Request = None)`
  - Delega a verificação de saúde do broker para o TaskService.
- function: `get_queue_policy(queue_name: str, service: TaskService = Depends(get_task_service))`
  - Retorna a política e argumentos atuais da fila via Management API.
- function: `validate_queue_policy(queue_name: str, service: TaskService = Depends(get_task_service))`
  - Valida a política da fila e indica divergências (TTL, max-length, etc.).
- function: `reconcile_queue_policy(queue_name: str, request: ReconcilePolicyRequest, service: TaskService = Depends(get_task_service))`
  - Executa reconciliação da política da fila. Se houver divergências e `force_delete` estiver habilitado,
a fila será deletada via Management API e recriada com os argumentos esperados.
Atenção: Deletar a fila remove mensagens pendentes.
- function: `get_outbox_stats(request: Request)`
- function: `reconcile_outbox(payload: OutboxReconcileRequest, request: Request)`
- function: `_negotiate_response(request: Request, data: dict)` -> `Response`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
