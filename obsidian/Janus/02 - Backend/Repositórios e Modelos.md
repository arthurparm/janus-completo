---
tipo: dominio
dominio: backend
camada: persistencia
fonte-de-verdade: codigo
status: ativo
---

# Repositórios e Modelos

## Objetivo
Registrar a base de persistência e os tipos de dados explícitos do backend.

## Responsabilidades
- Mapear repositórios por domínio.
- Mapear modelos nomeados usados como contratos internos.

## Entradas
- `backend/app/repositories`
- `backend/app/models`

## Saídas
- Inventário de persistência útil para troubleshooting e extensão.

## Dependências
- [[02 - Backend/Kernel e Startup]]
- [[07 - Glossário e Inventários/Inventário de Entidades]]

## Repositórios centrais
- Chat: `chat_repository`, `chat_repository_sql`
- Conhecimento: `knowledge_repository`, `knowledge_space_repository`
- Memória: `memory_repository`
- Autonomia: `autonomy_*`, `task_repository`, `pending_action_repository`
- Observabilidade: `observability_repository`
- Ferramentas: `tool_repository`, `tool_usage_repository`, `sandbox_repository`
- Documentos e prompts: `document_manifest_repository`, `prompt_repository`
- Usuário e consentimento: `user_repository`, `consent_repository`

## Modelos centrais
- `autonomy_models`
- `document_models`
- `knowledge`
- `knowledge_space_models`
- `pending_action_models`
- `quarantine_models`
- `tool_usage_models`
- `user_models`

## Arquivos-fonte
- `backend/app/repositories/*.py`
- `backend/app/models/*.py`
- `backend/app/db/postgres_config.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Login e Identidade]]
- [[04 - Fluxos End-to-End/Documentos Conhecimento e Memória]]

## Riscos/Lacunas
- Há persistência híbrida entre SQL, grafo, vetorial e fila.
- O significado de algumas entidades depende mais do serviço que do modelo isolado.
