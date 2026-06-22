---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/sandbox_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# sandbox_repository

## Arquivos-fonte
- `backend/app/repositories/sandbox_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/core/kernel.py`
- `backend/app/services/sandbox_service.py`

## Símbolos
- class: `SandboxRepositoryError`
  - Base exception for sandbox repository errors.
- class: `SandboxRepository`
  - Camada de Repositório para o Sandbox Python.
Abstrai todas as interações diretas com a infraestrutura de execução de código.
- method: `SandboxRepository.execute_code(self, code: str, context: dict[str, Any])` -> `ExecutionResult`
  - Executa um bloco de código através da infraestrutura de sandbox.
- method: `SandboxRepository.evaluate_expression(self, expression: str)` -> `ExecutionResult`
  - Avalia uma expressão através da infraestrutura de sandbox.
- function: `get_sandbox_repository()` -> `SandboxRepository`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
