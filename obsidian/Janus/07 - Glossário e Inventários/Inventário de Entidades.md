---
tipo: inventario
dominio: backend
camada: referencia
fonte-de-verdade: codigo
status: ativo
---

# Inventário de Entidades

## Objetivo
Listar os grupos de modelos explícitos do backend.

## Responsabilidades
- Dar um mapa semântico dos tipos persistidos.

## Entradas
- `backend/app/models/*.py`

## Saídas
- Índice de entidades/modelos.

## Dependências
- [[02 - Backend/Repositórios e Modelos]]

## Modelos
- `ab_assignment_models`
- `ab_experiment_models`
- `autonomy_models`
- `config_models`
- `consent_models`
- `consent_scopes`
- `document_models`
- `knowledge`
- `knowledge_space_models`
- `outbox_models`
- `pending_action_models`
- `quarantine_models`
- `schemas`
- `tool_usage_models`
- `user_models`

## Arquivos-fonte
- `backend/app/models/*.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[04 - Fluxos End-to-End/Autonomia]]
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]

## Riscos/Lacunas
- O comportamento de cada entidade depende fortemente do serviço que a manipula.
