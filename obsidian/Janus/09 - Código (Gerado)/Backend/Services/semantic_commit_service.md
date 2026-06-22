---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/semantic_commit_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# semantic_commit_service

## Objetivo
Semantic Commit Message Service.

## Arquivos-fonte
- `backend/app/services/semantic_commit_service.py`

## Símbolos
- function: `get_git_diff(repo_path: str = '.', staged_only: bool = True)` -> `str`
  - Get git diff for the repository.
- function: `get_changed_files(repo_path: str = '.', staged_only: bool = True)` -> `list[str]`
  - Get list of changed files.
- function: `_clean_commit_message(response_content: str)` -> `str`
  - Robust method to clean LLM response and extract commit message.
- function: `generate_semantic_commit(repo_path: str = '.', staged_only: bool = True, max_diff_chars: int = 8000)` -> `dict[str, Any]`
  - Generate a semantic commit message based on git diff.
- function: `suggest_commit_type(files: list[str])` -> `str`
  - Suggest a commit type based on file paths (heuristic).

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
