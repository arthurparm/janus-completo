---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/assistant_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# assistant_service

## Arquivos-fonte
- `backend/app/services/assistant_service.py`

## Fluxos de uso (chamadores)
- `backend/app/api/v1/endpoints/assistant.py`
- `backend/app/core/kernel.py`

## Símbolos
- class: `AssistantExecutionStep`
- class: `AssistantService`
  - Serviço de orquestração automática de ferramentas a partir de uma solicitação do usuário.
- method: `AssistantService.__init__(self, llm_service: LLMService)`
- method: `AssistantService.execute_request(self, user_request: str, risk_profile: str = RiskProfile.BALANCED, allowlist: list[str] | None = None, blocklist: list[str] | None = None, max_steps: int = 8, timeout_seconds: int = 30, metrics: dict[str, Any] | None = None)` -> `dict[str, Any]`
  - Executa uma solicitação do usuário de ponta a ponta, sem exigir escolha manual de ferramentas.
- method: `AssistantService._consolidate_results(self, steps: list[AssistantExecutionStep])` -> `str`
  - Cria uma saída human-readable consolidada a partir dos resultados das ferramentas.
- function: `get_assistant_service(request: Request)` -> `AssistantService`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
