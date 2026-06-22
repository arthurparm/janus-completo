---
tipo: codigo
dominio: backend
camada: models
gerado: true
origem: "backend/app/models/quarantine_models.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# quarantine_models

## Objetivo
Modelos para persistência de itens em quarentena do GraphGuardian.

## Arquivos-fonte
- `backend/app/models/quarantine_models.py`

## Fluxos de uso (chamadores)
- `backend/app/core/memory/graph_guardian.py`
- `backend/app/models/__init__.py`

## Símbolos
- class: `QuarantineStatus`
- class: `QuarantineItem`
  - Armazena itens (entidades ou relações) que foram rejeitados pelo GraphGuardian
para revisão posterior ou auditoria.
- method: `QuarantineItem.__repr__(self)`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
