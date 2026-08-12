from typing import Any

from app.services.model_artifact_service import (
    ModelArtifactError,
    load_model_metadata,
    resolve_model_file,
)


class BiasCheckServiceError(Exception):
    pass


class BiasCheckService:
    def run_precheck(self, model_id: str) -> dict[str, Any]:
        try:
            metadata = load_model_metadata(model_id)
            model_path = resolve_model_file(model_id, "model.json")
            artifact_present = model_path.is_file()
            evaluation = metadata.get("evaluation_metrics")
            performance_present = isinstance(evaluation, dict) and bool(evaluation)
            fairness_raw = metadata.get("fairness_evaluation")
            fairness = fairness_raw if isinstance(fairness_raw, dict) else None
            bias_score = None
            fairness_measured = False
            if fairness is not None:
                try:
                    candidate_score = float(fairness["bias_score"])
                    examples_evaluated = int(fairness["examples_evaluated"])
                    fairness_measured = bool(
                        fairness.get("measured") is True
                        and str(fairness.get("dataset") or "").strip()
                        and str(fairness.get("method") or "").strip()
                        and examples_evaluated > 0
                        and 0.0 <= candidate_score <= 1.0
                    )
                    if fairness_measured:
                        bias_score = candidate_score
                except (KeyError, TypeError, ValueError):
                    fairness_measured = False
            warnings: list[str] = []
            if not artifact_present:
                warnings.append("Model artifact model.json was not found.")
            if not performance_present:
                warnings.append("Holdout performance metrics are missing.")
            if not fairness_measured:
                warnings.append(
                    "Fairness was not measured on a declared evaluation dataset; "
                    "accuracy is not a bias metric."
                )
            return {
                "precheck_passed": bool(
                    artifact_present and performance_present and fairness_measured
                ),
                "bias_score": bias_score,
                "safety_warnings": warnings or None,
                "evidence": {
                    "artifact_present": artifact_present,
                    "performance_metrics_present": performance_present,
                    "fairness_metrics_present": fairness_measured,
                },
            }
        except ModelArtifactError:
            raise
        except Exception as e:
            raise BiasCheckServiceError(str(e))
