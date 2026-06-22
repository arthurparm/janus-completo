---
tipo: codigo
dominio: backend
camada: api
gerado: true
origem: "backend/app/api/v1/endpoints/sandbox.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# sandbox

## Arquivos-fonte
- `backend/app/api/v1/endpoints/sandbox.py`

## Rotas
- `GET /capabilities`
- `POST /evaluate`
- `POST /execute`

## Dependências de código
- Serviços
  - `sandbox_service`

## Símbolos
- class: `CodeExecutionRequest`
- class: `ExpressionRequest`
- function: `execute_code(request: CodeExecutionRequest, service: SandboxService = Depends(get_sandbox_service))`
  - Delega a execução de código de forma segura para o SandboxService.
- function: `evaluate_expression(request: ExpressionRequest, service: SandboxService = Depends(get_sandbox_service))`
  - Delega a avaliação de uma expressão para o SandboxService.
- function: `get_sandbox_capabilities(service: SandboxService = Depends(get_sandbox_service))`
  - Retorna informações sobre as capacidades e restrições do sandbox.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
