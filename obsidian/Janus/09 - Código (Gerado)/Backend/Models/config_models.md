---
tipo: codigo
dominio: backend
camada: models
gerado: true
origem: "backend/app/models/config_models.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# config_models

## Objetivo
Modelos SQLAlchemy para Configuration-as-Data.
Permite que o Meta-Agent modifique prompts e configurações dinamicamente.

## Arquivos-fonte
- `backend/app/models/config_models.py`

## Fluxos de uso (chamadores)
- `backend/app/db/postgres_config.py`
- `backend/app/models/__init__.py`
- `backend/app/models/ab_assignment_models.py`
- `backend/app/models/ab_experiment_models.py`
- `backend/app/models/audit_ledger_models.py`
- `backend/app/models/autonomy_models.py`
- `backend/app/models/consent_models.py`
- `backend/app/models/data_governance_models.py`
- `backend/app/models/document_models.py`
- `backend/app/models/knowledge_space_models.py`
- `backend/app/models/outbox_models.py`
- `backend/app/models/pending_action_models.py`
- `backend/app/models/quarantine_models.py`
- `backend/app/models/tool_usage_models.py`
- `backend/app/models/user_models.py`
- `backend/app/repositories/agent_config_repository.py`
- `backend/app/repositories/deployment_repository.py`
- `backend/app/repositories/prompt_repository.py`

## Símbolos
- class: `PriorityLevel`
  - Níveis de prioridade para configurações de agentes.
- class: `OptimizationType`
  - Tipos de otimização realizadas pelo Meta-Agent.
- class: `TargetType`
  - Tipos de alvo para otimizações.
- class: `Prompt`
  - Modelo para armazenar prompts versionados.
Permite que o Meta-Agent atualize prompts dinamicamente.
- method: `Prompt.__repr__(self)`
- class: `AgentConfiguration`
  - Modelo para configurações dinâmicas de agentes.
Permite que o Meta-Agent otimize configurações baseado em performance.
- method: `AgentConfiguration.__repr__(self)`
- class: `OptimizationHistory`
  - Modelo para rastrear otimizações realizadas pelo Meta-Agent.
Permite análise de impacto e rollback se necessário.
- method: `OptimizationHistory.__repr__(self)`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
