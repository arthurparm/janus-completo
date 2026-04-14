from __future__ import annotations

from typing import Any

from app.core.llm import ModelPriority, ModelRole
from app.repositories.deployment_repository import DeploymentRepository
from app.services.bias_check_service import BiasCheckService
from app.services.llm_service import LLMService

from .runtime import ExperimentalTurboQuantRuntime, LocalInferenceRuntime, OllamaRuntime


class InferenceFacade:
    def __init__(
        self,
        *,
        llm_service: LLMService,
        deployment_repository: DeploymentRepository | None = None,
        bias_check_service: BiasCheckService | None = None,
        local_runtime: LocalInferenceRuntime | None = None,
        experimental_runtime: LocalInferenceRuntime | None = None,
    ):
        self._llm_service = llm_service
        self._deployment_repo = deployment_repository or DeploymentRepository()
        self._bias_check_service = bias_check_service or BiasCheckService()
        self._local_runtime = local_runtime or OllamaRuntime()
        self._experimental_runtime = experimental_runtime or ExperimentalTurboQuantRuntime()

    async def invoke(
        self,
        *,
        prompt: str,
        role: str,
        priority: str,
        timeout_seconds: int | None,
        task_type: str | None = None,
        complexity: str | None = None,
        policy_overrides: dict[str, Any] | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
        objective_id: str | None = None,
    ) -> dict[str, Any]:
        return await self._llm_service.invoke_llm(
            prompt=prompt,
            role=ModelRole(role),
            priority=ModelPriority(priority),
            timeout_seconds=timeout_seconds,
            task_type=task_type,
            complexity=complexity,
            policy_overrides=policy_overrides,
            user_id=user_id,
            project_id=project_id,
            objective_id=objective_id,
        )

    async def provider_snapshot(
        self,
        *,
        role: str,
        priority: str,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        selected = await self._llm_service.select_provider_and_model(
            role=ModelRole(role),
            priority=ModelPriority(priority),
            user_id=user_id,
            project_id=project_id,
        )
        selected["local_runtime"] = self._local_runtime.name
        selected["experimental_runtime"] = self._experimental_runtime.name
        return selected

    def stage_model(self, *, model_id: str, rollout_percent: int) -> dict[str, Any]:
        return self._deployment_repo.stage(model_id, rollout_percent)

    def publish_model(self, *, model_id: str) -> dict[str, Any]:
        return self._deployment_repo.publish(model_id)

    def rollback_model(self, *, model_id: str) -> dict[str, Any]:
        return self._deployment_repo.rollback(model_id)

    def precheck(self, *, model_id: str) -> dict[str, Any]:
        return self._bias_check_service.run_precheck(model_id)

