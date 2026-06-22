---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/scheduler_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# scheduler_service

## Objetivo
SchedulerService - Cron-like Task Scheduling for Janus
=======================================================

## Arquivos-fonte
- `backend/app/services/scheduler_service.py`

## Dependências de código
- Repositórios
  - `audit_ledger_repository`
  - `observability_repository`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`

## Símbolos
- class: `ScheduleType`
  - Tipos de agendamento suportados.
- class: `ScheduledJob`
  - Representa um job agendado.
- method: `ScheduledJob.calculate_next_run(self)` -> `datetime`
  - Calcula o próximo horário de execução.
- class: `SchedulerService`
  - Serviço de agendamento de tarefas (Cron Jobs).
- method: `SchedulerService.__init__(self)`
- method: `SchedulerService.register_job(self, name: str, callback: Callable[[], Awaitable[Any]], schedule_type: ScheduleType = ScheduleType.INTERVAL, interval_seconds: int = 60, hour: int = 0, minute: int = 0, weekday: int = 0, enabled: bool = True, metadata: dict[str, Any] | None = None)` -> `ScheduledJob`
  - Registra um novo job no scheduler.
- method: `SchedulerService.unregister_job(self, name: str)` -> `bool`
  - Remove um job do scheduler.
- method: `SchedulerService.enable_job(self, name: str)` -> `bool`
  - Ativa um job.
- method: `SchedulerService.disable_job(self, name: str)` -> `bool`
  - Desativa um job.
- method: `SchedulerService.get_job(self, name: str)` -> `ScheduledJob | None`
  - Retorna um job pelo nome.
- method: `SchedulerService.list_jobs(self)` -> `list[dict[str, Any]]`
  - Lista todos os jobs registrados.
- method: `SchedulerService.start(self)`
  - Inicia o scheduler.
- method: `SchedulerService.stop(self)`
  - Para o scheduler.
- method: `SchedulerService._scheduler_loop(self)`
  - Loop principal do scheduler.
- method: `SchedulerService._execute_job(self, job: ScheduledJob)`
  - Executa um job específico.
- method: `SchedulerService.get_status(self)` -> `dict[str, Any]`
  - Retorna o status do scheduler.
- function: `get_scheduler()` -> `SchedulerService`
  - Retorna a instância singleton do scheduler.
- function: `initialize_default_jobs(scheduler: SchedulerService)`
  - Registra os jobs padrão do sistema.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
