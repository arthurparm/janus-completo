---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/task_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# task_repository

## Arquivos-fonte
- `backend/app/repositories/task_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/services/task_service.py`

## Símbolos
- class: `TaskRepositoryError`
  - Base exception for task repository errors.
- class: `TaskRepository`
  - Camada de Repositório para tarefas assíncronas (Message Broker).
Recebe sua dependência de infraestrutura via DI.
- method: `TaskRepository.__init__(self, broker: MessageBroker)`
- method: `TaskRepository.publish_message(self, queue_name: str, message: str)`
  - Publica uma mensagem em uma fila específica.
- method: `TaskRepository.get_queue_info(self, queue_name: str)` -> `dict[str, Any] | None`
  - Busca informações de uma fila específica.
- method: `TaskRepository.is_broker_healthy(self)` -> `bool`
  - Verifica a saúde do message broker.
- method: `TaskRepository.get_queue_policy(self, queue_name: str)` -> `dict[str, Any] | None`
  - Consulta a política/argumentos atuais de uma fila via Management API.
- method: `TaskRepository.validate_queue_policy(self, queue_name: str)` -> `dict[str, Any]`
  - Valida argumentos da fila contra a configuração esperada.
- method: `TaskRepository.reconcile_queue_policy(self, queue_name: str, force_delete: bool = True)` -> `dict[str, Any]`
  - Reconciliar política (deletando e recriando fila se divergente).
- function: `get_task_repository(broker: MessageBroker = Depends(get_broker))` -> `TaskRepository`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
