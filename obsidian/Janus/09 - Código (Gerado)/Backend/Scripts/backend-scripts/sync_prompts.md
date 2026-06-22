---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "backend/scripts/sync_prompts.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# sync_prompts

## Arquivos-fonte
- `backend/scripts/sync_prompts.py`

## Símbolos
- function: `_ensure_tables()` -> `None`
- function: `sync_prompts()`
  - Reads all .txt files from backend/app/prompts/ and updates the database.
Creates new versions if content differs.

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
