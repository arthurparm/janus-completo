# Technical QA Evaluation

This folder stores the versioned dataset and baseline artifacts for technical question evaluation.

## Structure

- `datasets/technical-qa.v1.json`: fixed evaluation dataset.
- `runs/<timestamp>/score.json`: per-run output from the evaluator.
- `runs/<timestamp>/summary.md`: per-run markdown summary.
- `baselines/<dataset_id>/<version>/score.json`: published baseline for direct comparison.
- `baselines/<dataset_id>/<version>/summary.md`: markdown summary for the baseline.
- `baselines/<dataset_id>/index.json`: baseline version index.

## Run

From `janus/`:

```bash
python scripts/eval_technical_qa.py --compare-baseline
```

To publish a new baseline:

```bash
python scripts/eval_technical_qa.py --publish-baseline --compare-baseline
```
