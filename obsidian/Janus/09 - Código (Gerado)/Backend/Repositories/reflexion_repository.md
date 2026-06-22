---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/reflexion_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# reflexion_repository

## Arquivos-fonte
- `backend/app/repositories/reflexion_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/core/workers/reflexion_worker.py`
- `backend/app/services/reflexion_service.py`

## Símbolos
- class: `ReflexionRepositoryError`
  - Base exception for reflexion repository errors.
- class: `ReflexionRepository`
  - Camada de Repositório para o ciclo de auto-otimização Reflexion.
Abstrai todas as interações diretas com a infraestrutura de otimização.
- method: `ReflexionRepository.__init__(self, memory_service: MemoryService)`
- method: `ReflexionRepository.run_cycle(self, task: str, config: ReflexionConfig)` -> `dict[str, Any]`
  - Executa o ciclo de Reflexion através da infraestrutura core.
- method: `ReflexionRepository.reset_breakers(self)`
  - Reseta os circuit breakers dos agentes.
- method: `ReflexionRepository.get_health(self)` -> `dict[str, Any]`
  - Coleta informações de saúde do módulo de Reflexion.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
