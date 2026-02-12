# Component Inventory - Backend (`janus`)

## Resumo

No backend, o inventario de componentes e orientado a modulos de dominio e infraestrutura (nao UI).

## Componentes de API

- Pasta `app/api/v1/endpoints`: 39 modulos especializados
- Router central em `app/api/v1/router.py`

## Componentes de Servico

- Pasta `app/services`: servicos para chat, llm, memory, observabilidade, autonomia, tools e orquestracao

## Componentes de Runtime Core

- `app/core/workers`: workers e orchestrator
- `app/core/llm`: roteamento, cache, resiliencia, custo
- `app/core/memory`: grafo, vetores, protecao, circuit breaker
- `app/core/infrastructure`: broker, auth, middleware, tracing, sandbox
- `app/core/tools`: ferramentas executaveis por agentes

## Componentes de Persistencia

- `app/models`: schemas SQLAlchemy/Pydantic
- `app/repositories`: encapsulamento de acesso a dados
- `app/db`: configuracao de conexao e adaptadores

## Observacao

A composicao e fortemente modular e orientada a capacidades, com fronteiras claras por pacote.

---

_Gerado pelo workflow BMAD `document-project`_
