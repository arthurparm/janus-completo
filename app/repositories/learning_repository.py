import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import hashlib
import os
import time
from fastapi import Depends

from prometheus_client import Counter, Histogram, Gauge

from app.core.infrastructure.filesystem_manager import read_file
from app.core.workers import data_harvester
from app.core.workers.data_harvester import TRAINING_DATA_FILE
# Legacy simulation removed: use NeuralTrainer
from app.core.workers.neural_training_system import TrainingConfig as NTTrainingConfig, ModelType, neural_trainer

ModelInfo = Dict[str, Any]
TrainingSession = Dict[str, Any]

logger = structlog.get_logger(__name__)

class LearningRepository:
    """
    Camada de Repositório para dados de aprendizado e treinamento.
    Abstrai a lógica de armazenamento e a execução de workers.
    """

    def __init__(self):
        self._training_sessions: Dict[str, TrainingSession] = {}
        self._trained_models: Dict[str, ModelInfo] = {}
        self._experiments: Dict[str, Dict[str, Any]] = {}
        self._stats = {
            "total_harvested": 0,
            "total_trained": 0,
            "last_harvest": None,
            "last_training": None,
            "dataset": {
                "version": None,
                "num_examples": 0,
                "hash": None,
                "last_modified": None
            }
        }

        # Metrics
        self._experiments_total = Counter(
            "learning_experiments_total",
            "Total de experimentos de treinamento",
            ["status"]
        )
        self._experiment_duration = Histogram(
            "learning_experiment_duration_seconds",
            "Duração dos experimentos de treinamento"
        )
        self._dataset_examples = Gauge(
            "learning_dataset_examples_count",
            "Número de exemplos no dataset de treino"
        )

    def get_all_models(self) -> List[ModelInfo]:
        """Lista modelos treinados lendo do filesystem (workspace/models)."""
        models_dir = os.path.join("/app", "workspace", "models")
        results: List[ModelInfo] = []
        try:
            if not os.path.isdir(models_dir):
                return list(self._trained_models.values())
            for entry in os.listdir(models_dir):
                model_path = os.path.join(models_dir, entry)
                if not os.path.isdir(model_path):
                    continue
                meta_path = os.path.join(model_path, "metadata.json")
                if not os.path.isfile(meta_path):
                    continue
                try:
                    import json
                    with open(meta_path, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                    stat = os.stat(meta_path)
                    results.append({
                        "model_id": entry,
                        "model_name": metadata.get("model_name", entry),
                        "model_version": metadata.get("model_version"),
                        "model_type": metadata.get("model_type"),
                        "status": "trained",
                        "created_at": datetime.utcfromtimestamp(stat.st_mtime).isoformat(),
                        "training_examples": metadata.get("num_examples", 0),
                        "accuracy": metadata.get("accuracy"),
                        "loss": metadata.get("loss"),
                        "path": model_path
                    })
                except Exception:
                    continue
            # Mantém também quaisquer modelos salvos via API antiga
            results.extend(list(self._trained_models.values()))
            return results
        except Exception:
            # Fallback para memória
            return list(self._trained_models.values())

    def find_model_by_id(self, model_id: str) -> Optional[ModelInfo]:
        """Busca modelo pelo id (nome da pasta) lendo do filesystem."""
        # Primeiro, verifica memória
        if model_id in self._trained_models:
            return self._trained_models.get(model_id)
        models_dir = os.path.join("/app", "workspace", "models")
        model_path = os.path.join(models_dir, model_id)
        meta_path = os.path.join(model_path, "metadata.json")
        if os.path.isfile(meta_path):
            try:
                import json
                with open(meta_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)
                stat = os.stat(meta_path)
                return {
                    "model_id": model_id,
                    "model_name": metadata.get("model_name", model_id),
                    "model_version": metadata.get("model_version"),
                    "model_type": metadata.get("model_type"),
                    "status": "trained",
                    "created_at": datetime.utcfromtimestamp(stat.st_mtime).isoformat(),
                    "training_examples": metadata.get("num_examples", 0),
                    "accuracy": metadata.get("accuracy"),
                    "loss": metadata.get("loss"),
                    "path": model_path
                }
            except Exception:
                return None
        return None

    def save_model(self, model_info: ModelInfo) -> ModelInfo:
        model_id = model_info['model_id']
        self._trained_models[model_id] = model_info
        self._stats["total_trained"] += 1
        self._stats["last_training"] = datetime.utcnow().isoformat()
        return model_info

    def get_active_training_session(self) -> Optional[TrainingSession]:
        for session in self._training_sessions.values():
            if session.get("status") == "training":
                return session
        return None

    def get_stats(self) -> Dict[str, Any]:
        # Atualiza info de dataset antes de retornar
        self._update_dataset_version()
        stats = self._stats.copy()
        stats["active_training_sessions"] = 1 if self.get_active_training_session() else 0
        stats["avg_training_time_minutes"] = 2.5  # Mock
        return stats

    def increment_harvested_count(self, count: int):
        self._stats["total_harvested"] += count
        self._stats["last_harvest"] = datetime.utcnow().isoformat()

    async def run_training_process(
        self,
        dataset_version: Optional[str] = None,
        model_name: Optional[str] = None,
        training_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Executa o processo de treinamento com NeuralTrainer e tracking de experimento."""
        logger.debug("Executando processo de treinamento via NeuralTrainer.")

        # Atualiza/obtém versão do dataset
        dataset_info = self._update_dataset_version()
        if dataset_version:
            dataset_info["version"] = dataset_version

        # Cria sessão/experimento
        experiment_id = self._create_experiment(dataset_info)
        start_ts = time.perf_counter()
        self._experiments_total.labels("created").inc()

        # Monta configuração de treinamento
        tp = training_params or {}
        model_type_str = str(tp.get("model_type" or "classifier")).lower()
        try:
            model_type = ModelType(model_type_str)
        except Exception:
            model_type = ModelType.CLASSIFIER

        config = NTTrainingConfig(
            model_type=model_type,
            model_name=model_name or f"janus-{model_type.value}",
            learning_rate=float(tp.get("learning_rate", 1e-5)),
            batch_size=int(tp.get("batch_size", 8)),
            num_epochs=int(tp.get("num_epochs", tp.get("epochs", 3))),
            validation_split=float(tp.get("validation_split", 0.2)),
            early_stopping=bool(tp.get("early_stopping", True)),
            save_checkpoints=bool(tp.get("save_checkpoints", True)),
            max_examples=tp.get("max_examples")
        )

        try:
            result = await neural_trainer.train_model(config)
            elapsed = time.perf_counter() - start_ts
            self._experiment_duration.observe(elapsed)

            # Atualiza experimento
            exp = self._experiments.get(experiment_id, {})
            exp.update({
                "status": "completed" if result.status.value == "completed" else "failed",
                "completed_at": datetime.utcnow().isoformat(),
                "summary": f"Acurácia: {result.accuracy}, exemplos: {result.num_examples}",
                "duration_seconds": elapsed
            })
            self._experiments[experiment_id] = exp
            self._experiments_total.labels(exp["status"]).inc()

            # Retorna payload enriquecido
            enriched = {
                "message": "Treinamento concluído.",
                "summary": f"Modelo {result.model_name} v{result.model_version} salvo.",
                "experiment_id": experiment_id,
                "dataset_version": dataset_info.get("version"),
                "dataset_num_examples": dataset_info.get("num_examples"),
                "model_name": result.model_name,
                "model_version": result.model_version,
                "accuracy": result.accuracy,
                "loss": result.loss
            }
            return enriched
        except Exception as e:
            elapsed = time.perf_counter() - start_ts
            self._experiment_duration.observe(elapsed)
            self._experiments_total.labels("error").inc()
            exp = self._experiments.get(experiment_id, {})
            exp.update({
                "status": "error",
                "completed_at": datetime.utcnow().isoformat(),
                "error": str(e),
                "duration_seconds": elapsed
            })
            self._experiments[experiment_id] = exp
            logger.error("Erro no processo de treinamento", exc_info=e)
            return {"message": "Falha no treino.", "summary": str(e), "experiment_id": experiment_id}

    async def run_harvesting(self, limit: int, query: Optional[str] = None, min_score: Optional[float] = None) -> Dict[
        str, Any]:
        """Abstrai a execução do worker de coleta de dados."""
        logger.debug("Executando coleta de dados via repositório.", query=query, min_score=min_score)
        return await data_harvester.harvest_data_for_training(limit=limit, query=query, min_score=min_score)

    def is_harvester_healthy(self) -> bool:
        """Verifica a saúde do worker de coleta de dados."""
        return hasattr(data_harvester, 'harvester')

    # ===== Dataset Versioning =====

    def _update_dataset_version(self) -> Dict[str, Any]:
        """Computa versão do dataset baseada no conteúdo atual do JSONL."""
        try:
            content = read_file(os.path.join("workspace", TRAINING_DATA_FILE))
            if content.startswith("Erro:"):
                info = {
                    "version": None,
                    "num_examples": 0,
                    "hash": None,
                    "last_modified": None
                }
                self._stats["dataset"].update(info)
                self._dataset_examples.set(0)
                return info

            lines = [ln for ln in content.strip().split('\n') if ln.strip()]
            num_examples = len(lines)
            sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
            # Versão simplificada: num_exemplos + prefixo do hash
            version = f"v{num_examples}-{sha[:8]}"
            last_modified = datetime.utcnow().isoformat()
            info = {
                "version": version,
                "num_examples": num_examples,
                "hash": sha,
                "last_modified": last_modified
            }
            self._stats["dataset"].update(info)
            self._dataset_examples.set(num_examples)
            return info
        except Exception:
            # Em caso de erro, não quebrar chamadas de stats
            return self._stats.get("dataset", {})

    def get_dataset_version_info(self) -> Dict[str, Any]:
        return self._update_dataset_version()

    # ===== Experiments Tracking =====

    def _create_experiment(self, dataset_info: Dict[str, Any]) -> str:
        exp_id = f"exp-{int(time.time())}-{hashlib.sha256(os.urandom(8)).hexdigest()[:6]}"
        self._experiments[exp_id] = {
            "experiment_id": exp_id,
            "status": "training",
            "dataset_version": dataset_info.get("version"),
            "num_examples": dataset_info.get("num_examples"),
            "started_at": datetime.utcnow().isoformat()
        }
        # também registrar sessão ativa
        self._training_sessions[exp_id] = {
            "current_model": None,
            "progress": 0.0,
            "status": "training"
        }
        return exp_id

    def list_experiments(self) -> List[Dict[str, Any]]:
        return list(self._experiments.values())

    def get_experiment(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        return self._experiments.get(experiment_id)


# Padrão de Injeção de Dependência: Getter para o repositório
def get_learning_repository() -> LearningRepository:
    return LearningRepository()
