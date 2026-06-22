---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/sandbox_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# sandbox_service

## Arquivos-fonte
- `backend/app/services/sandbox_service.py`

## Dependências de código
- Repositórios
  - `sandbox_repository`

## Fluxos de uso (chamadores)
- `backend/app/api/exception_handlers.py`
- `backend/app/api/v1/endpoints/sandbox.py`
- `backend/app/core/kernel.py`

## Símbolos
- class: `SandboxError`
  - Base exception for sandbox service errors.
- class: `InvalidInputError`
  - Raised for invalid input, such as empty code.
- class: `SandboxService`
  - Camada de serviço para operações de execução de código em sandbox.
Orquestra a lógica de negócio, recebendo suas dependências via DI.
- method: `SandboxService.__init__(self, repo: SandboxRepository)`
- method: `SandboxService.execute_code(self, code: str, context: dict[str, Any])` -> `ExecutionResult`
  - Valida a entrada e delega a execução de código para o repositório.
- method: `SandboxService.evaluate_expression(self, expression: str)` -> `ExecutionResult`
  - Valida a entrada e delega a avaliação de expressão para o repositório.
- method: `SandboxService.get_capabilities(self)` -> `dict[str, Any]`
  - Retorna as capacidades e restrições do sandbox.
- function: `get_sandbox_service(request: Request)` -> `SandboxService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
