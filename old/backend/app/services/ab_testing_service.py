import math
from typing import Any

from app.repositories.ab_experiment_repository import ABExperimentRepository


class ABTestingService:
    def __init__(self, repo: ABExperimentRepository | None = None):
        self._repo = repo or ABExperimentRepository()

    def compute_winner(self, experiment_id: int, metric_name: str = "accuracy") -> dict[str, Any]:
        s = self._repo._get_session()
        try:
            from app.models.ab_experiment_models import ExperimentArm, ExperimentResult

            arms = s.query(ExperimentArm).filter(ExperimentArm.experiment_id == experiment_id).all()
            results = (
                s.query(ExperimentResult)
                .filter(
                    ExperimentResult.experiment_id == experiment_id,
                    ExperimentResult.metric_name == metric_name,
                )
                .all()
            )
            stats: dict[int, dict[str, Any]] = {}
            for r in results:
                a = stats.setdefault(r.arm_id, {"values": []})
                try:
                    a["values"].append(float(r.metric_value))
                except Exception:
                    continue
            for arm in arms:
                d = stats.setdefault(arm.id, {"values": []})
                vals = d["values"]
                n = len(vals)
                mean = sum(vals) / n if n > 0 else 0.0
                var = (sum((v - mean) ** 2 for v in vals) / max(1, n - 1)) if n > 1 else 0.0
                d.update(
                    {
                        "arm_id": arm.id,
                        "name": arm.name,
                        "model_spec": arm.model_spec,
                        "n": n,
                        "mean": mean,
                        "var": var,
                    }
                )
            ranked = sorted(stats.values(), key=lambda x: x.get("mean", 0.0), reverse=True)
            winner = ranked[0] if ranked else {}
            p_value = None
            if len(ranked) >= 2:
                a, b = ranked[0], ranked[1]
                n1, n2 = max(1, a["n"]), max(1, b["n"])
                s1, s2 = a["var"], b["var"]
                denom = math.sqrt((s1 / n1) + (s2 / n2)) if (s1 > 0 or s2 > 0) else 1.0
                z = (a["mean"] - b["mean"]) / denom if denom > 0 else 0.0
                try:
                    import math as _m

                    p_value = 2.0 * (1.0 - 0.5 * (1.0 + _m.erf(abs(z) / _m.sqrt(2))))
                except Exception:
                    p_value = None
            return {"winner": winner, "arms": ranked, "metric": metric_name, "p_value": p_value}
        finally:
            if not self._repo._session:
                s.close()
