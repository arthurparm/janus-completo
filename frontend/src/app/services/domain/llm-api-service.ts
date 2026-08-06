import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiContextService } from '../api-context.service';
import { LLMProvidersResponse, LLMSubsystemHealth, LLMCacheStatusResponse, CircuitBreakerStatus, DeploymentStageResponse, DeploymentPublishResponse, GPUBudgetResponse, GPUUsageResponse, ABExperimentSetResponse } from '../../models';
import { AdminActionsApiService } from './admin-actions-api-service';

@Injectable({ providedIn: 'root' })
export class LlmApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService,
    private adminActions: AdminActionsApiService
  ) {}

listLLMProviders(): Observable<LLMProvidersResponse> {
    return this.http.get<LLMProvidersResponse>(this.apiContext.buildUrl(`/api/v1/llm/providers`))
  }

getLLMHealth(): Observable<LLMSubsystemHealth> {
    return this.adminActions.execute<LLMSubsystemHealth>('llm_health_api_v1_llm_health_get')
  }

getLLMCacheStatus(): Observable<LLMCacheStatusResponse> {
    return this.adminActions.execute<LLMCacheStatusResponse>('get_cache_status_api_v1_llm_cache_status_get')
  }

getLLMCircuitBreakers(): Observable<CircuitBreakerStatus[]> {
    return this.adminActions.execute<CircuitBreakerStatus[]>('get_circuit_breaker_status_api_v1_llm_circuit_breakers_get')
  }

getBudgetSummary(): Observable<any> {
    return this.http.get(this.apiContext.buildUrl(`/api/v1/llm/budget/summary`))
  }

stageDeployment(model_id: string, rollout_percent: number): Observable<DeploymentStageResponse> {
    return this.adminActions.execute<DeploymentStageResponse>('stage_api_v1_deployment_stage_post', { payload: { model_id, rollout_percent } })
  }

publishDeployment(model_id: string): Observable<DeploymentPublishResponse> {
    return this.adminActions.execute<DeploymentPublishResponse>('publish_api_v1_deployment_publish_post', { queryParams: { model_id } })
  }

rollbackDeployment(model_id: string): Observable<DeploymentPublishResponse> {
    return this.adminActions.execute<DeploymentPublishResponse>('rollback_api_v1_deployment_rollback_post', { queryParams: { model_id } })
  }

precheckDeployment(model_id: string): Observable<{ precheck_passed: boolean; bias_score: number; safety_warnings?: string | null }> {
    return this.adminActions.execute<{ precheck_passed: boolean; bias_score: number; safety_warnings?: string | null }>('precheck_api_v1_deployment_precheck_post', { queryParams: { model_id } })
  }

getGPUUsage(_userId: string): Observable<GPUUsageResponse> {
    return this.http.get<GPUUsageResponse>(this.apiContext.buildUrl(`/api/v1/resources/gpu/usage/self`))
  }

setGPUBudget(_userId: string, budget: number): Observable<GPUBudgetResponse> {
    return this.http.post<GPUBudgetResponse>(this.apiContext.buildUrl(`/api/v1/resources/gpu/budget`), { budget })
  }

setLLMABExperiment(experiment_id: number): Observable<ABExperimentSetResponse> {
    return this.adminActions.execute<ABExperimentSetResponse>('set_ab_experiment_api_v1_llm_ab_set_experiment_post', { payload: { experiment_id } })
  }
}
