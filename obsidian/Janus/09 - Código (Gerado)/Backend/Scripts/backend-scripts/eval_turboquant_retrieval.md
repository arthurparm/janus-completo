---
tipo: codigo
dominio: backend
camada: scripts
gerado: true
origem: "backend/scripts/eval_turboquant_retrieval.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# eval_turboquant_retrieval

## Arquivos-fonte
- `backend/scripts/eval_turboquant_retrieval.py`

## Símbolos
- function: `_parser()` -> `argparse.ArgumentParser`
- function: `_recall_at_k(expected_ids: set[str], predicted_ids: list[str], k: int)` -> `float`
- function: `_ndcg_at_k(expected_ids: set[str], predicted_ids: list[str], k: int)` -> `float`
- function: `_score_results(items: list[dict[str, Any]], expected_ids: set[str])` -> `dict[str, float]`
- function: `_evaluate_case(knowledge: Any, case: dict[str, Any])` -> `dict[str, Any]`
- function: `_summarize(cases: list[dict[str, Any]])` -> `dict[str, Any]`
- function: `_write_markdown(path: Path, payload: dict[str, Any])` -> `None`
- function: `_run(args: argparse.Namespace)` -> `dict[str, Any]`
- function: `main()` -> `int`

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
