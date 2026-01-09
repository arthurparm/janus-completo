import json
import os
from typing import Any


class BiasCheckServiceError(Exception):
    pass


class BiasCheckService:
    def run_precheck(self, model_id: str) -> dict[str, Any]:
        try:
            meta_path = os.path.join("/app", "workspace", "models", model_id, "metadata.json")
            meta = {}
            if os.path.isfile(meta_path):
                with open(meta_path, encoding="utf-8") as f:
                    meta = json.load(f)
            # Simulação: calcula um score de bias a partir de metadados quando disponíveis
            acc = float(meta.get("accuracy") or 0.0)
            bias_score = max(0.0, 1.0 - acc)  # proxy simples
            passed = acc >= 0.7 and bias_score <= 0.3
            warnings = None if passed else "Bias alto ou acurácia insuficiente"
            return {
                "precheck_passed": bool(passed),
                "bias_score": float(bias_score),
                "safety_warnings": warnings,
            }
        except Exception as e:
            raise BiasCheckServiceError(str(e))
