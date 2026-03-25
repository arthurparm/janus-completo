---
tipo: qualidade
dominio: testes
camada: validacao
fonte-de-verdade: codigo
status: ativo
---

# Checklist de Validação

## Objetivo
Definir os checks mínimos para validar que o vault continua coerente com o sistema.

## Responsabilidades
- Cobrir consistência documental.
- Cobrir validação prática no PC TESTE.

## Entradas
- Vault atual.
- Stack em execução.

## Saídas
- Lista objetiva de validação.

## Dependências
- [[05 - Infra e Operação/Healthchecks e Contratos Operacionais]]
- [[07 - Glossário e Inventários/Inventário de Integrações Externas]]

## Checklist
- Toda nota principal aponta para upstream e downstream.
- Todo fluxo crítico aponta para backend, frontend e dependência runtime.
- Toda integração externa aparece em visão arquitetural e inventário.
- `/health` responde.
- `/api/v1/system/status` responde.
- `/api/v1/workers/status` responde.
- Frontend principal responde em `:4300`.
- O papel de Neo4j, Qdrant e Ollama descrito no vault bate com compose/config.

## Arquivos-fonte
- `docker-compose.pc1.yml`
- `docker-compose.pc2.yml`
- `backend/app/main.py`
- `backend/app/api/v1/endpoints/system_status.py`
- `backend/app/api/v1/endpoints/workers.py`

## Fluxos relacionados
- [[04 - Fluxos End-to-End/Observabilidade]]
- [[05 - Infra e Operação/PC1 PC2 e Docker]]

## Riscos/Lacunas
- Validação prática confirma runtime, mas não substitui leitura periódica da lógica do código.
