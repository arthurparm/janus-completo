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

Offline recurring run (no API dependency):

```bash
python scripts/eval_technical_qa.py \
  --mode offline-codebase \
  --repo-root .. \
  --compare-baseline \
  --gate-on-regression \
  --require-baseline
```

To publish a new baseline:

```bash
python scripts/eval_technical_qa.py \
  --mode offline-codebase \
  --repo-root .. \
  --publish-baseline \
  --compare-baseline
```

## Regression gate

When `--gate-on-regression` is enabled, the run fails if any configured threshold is violated:

- pass rate drop (`--max-pass-rate-drop`, default `0.02`)
- citation coverage drop (`--max-citation-coverage-drop`, default `0.02`)
- p95 latency increase (`--max-p95-latency-increase-ms`, default `250`)

If `--require-baseline` is set and baseline is missing, the gate fails.
