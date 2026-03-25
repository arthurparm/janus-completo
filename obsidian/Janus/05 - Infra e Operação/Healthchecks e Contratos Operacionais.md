---
tipo: operacao
dominio: infra
camada: saude
fonte-de-verdade: codigo
status: ativo
---

# Healthchecks e Contratos Operacionais

## Objetivo
Registrar os contratos de prontidão e saúde usados em operação.

## Responsabilidades
- Listar checks explícitos do runtime.
- Relacionar saúde lógica e containers.

## Entradas
- Compose healthchecks.
- Endpoints de status e observabilidade.

## Saídas
- Checklist para validação operacional.

## Dependências
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[06 - Qualidade e Testes/Checklist de Validação]]

## Checks relevantes
- API:
  - `/health`
  - `/healthz`
  - `/api/v1/system/status`
  - `/api/v1/workers/status`
- Frontend:
  - `http://127.0.0.1:4300/`
- Neo4j:
  - `cypher-shell ... RETURN 1`
- Qdrant:
  - porta `6333`
- Ollama:
  - `ollama list`

## Leitura operacional
- O compose já embute critérios mínimos de prontidão.
- O backend também expõe saúde lógica mais profunda via observability e system status.

## Arquivos-fonte
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`
- `backend/app/api/v1/endpoints/observability.py`
- `backend/app/api/v1/endpoints/system_status.py`
- `backend/app/api/v1/endpoints/workers.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[06 - Qualidade e Testes/Mapa de Testes]]

## Riscos/Lacunas
- “Container saudável” não garante que conhecimento, modelos e workers estejam plenamente funcionais.
