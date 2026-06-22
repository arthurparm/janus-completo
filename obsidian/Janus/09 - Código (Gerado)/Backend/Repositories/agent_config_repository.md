---
tipo: codigo
dominio: backend
camada: repositories
gerado: true
origem: "backend/app/repositories/agent_config_repository.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# agent_config_repository

## Objetivo
Repositório para gerenciar configurações dinâmicas de agentes.
Permite que o Meta-Agent otimize configurações baseado em performance.

## Arquivos-fonte
- `backend/app/repositories/agent_config_repository.py`

## Fluxos de uso (chamadores)
- `backend/app/core/agents/specialized_agent.py`

## Símbolos
- class: `AgentConfigRepository`
  - Repositório para operações CRUD em configurações de agentes (Async).
- method: `AgentConfigRepository.__init__(self, session: AsyncSession | None = None)`
- method: `AgentConfigRepository._get_session(self)` -> `AsyncSession`
  - Obtém sessão do banco de dados (Async).
- method: `AgentConfigRepository.get_active_config(self, agent_name: str, agent_role: str)` -> `AgentConfiguration | None`
  - Obtém a configuração ativa para um agente específico.
- method: `AgentConfigRepository.get_config_by_id(self, config_id: int)` -> `AgentConfiguration | None`
  - Obtém configuração por ID.
- method: `AgentConfigRepository.get_configs_by_role(self, agent_role: str, active_only: bool = True)` -> `list[AgentConfiguration]`
  - Obtém todas as configurações para um papel específico.
- method: `AgentConfigRepository.get_configs_by_provider(self, llm_provider: str, active_only: bool = True)` -> `list[AgentConfiguration]`
  - Obtém configurações por provedor LLM.
- method: `AgentConfigRepository.create_config(self, agent_name: str, agent_role: str, llm_provider: str, llm_model: str, prompt_id: int | None = None, max_retries: int = 3, timeout_seconds: int = 60, temperature: Decimal = Decimal('0.7'), max_tokens: int = 4096, priority_level: PriorityLevel = PriorityLevel.MEDIUM, cost_budget_usd: Decimal = Decimal('0.05'), performance_threshold: Decimal = Decimal('0.8'), created_by: str = 'meta-agent', activate: bool = False)` -> `AgentConfiguration`
  - Cria uma nova configuração de agente.
- method: `AgentConfigRepository.update_config(self, config_id: int, updates: dict[str, Any], updated_by: str = 'meta-agent')` -> `AgentConfiguration | None`
  - Atualiza uma configuração existente.
- method: `AgentConfigRepository.activate_config(self, config_id: int)` -> `bool`
  - Ativa uma configuração específica.
- method: `AgentConfigRepository._deactivate_config(self, session: AsyncSession, agent_name: str, agent_role: str)`
  - Desativa configuração ativa atual.
- method: `AgentConfigRepository.get_low_performance_configs(self, threshold: float = 0.7)` -> `list[AgentConfiguration]`
  - Obtém configurações com performance abaixo do limiar.
- method: `AgentConfigRepository.get_high_cost_configs(self, cost_limit: Decimal = Decimal('0.10'))` -> `list[AgentConfiguration]`
  - Obtém configurações com custo acima do limite.
- method: `AgentConfigRepository.get_config_stats(self)` -> `dict[str, Any]`
  - Obtém estatísticas das configurações.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
