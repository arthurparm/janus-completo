import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiContextService } from '../api-context.service';
import { LLMProvidersResponse, LLMSubsystemHealth, LLMCacheStatusResponse, CircuitBreakerStatus, DeploymentStageResponse, DeploymentPublishResponse, GPUBudgetResponse, GPUUsageResponse, ABExperimentSetResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class LlmApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

listLLMProviders(): Observable<LLMProvidersResponse> {
    return this.http.get<LLMProvidersResponse>(this.apiContext.buildUrl(`/api/v1/llm/providers`))
  }

getLLMHealth(): Observable<LLMSubsystemHealth> {
    return this.http.get<LLMSubsystemHealth>(this.apiContext.buildUrl(`/api/v1/llm/health`))
  }

getLLMCacheStatus(): Observable<LLMCacheStatusResponse> {
    return this.http.get<LLMCacheStatusResponse>(this.apiContext.buildUrl(`/api/v1/llm/cache/status`))
  }

getLLMCircuitBreakers(): Observable<CircuitBreakerStatus[]> {
    return this.http.get<CircuitBreakerStatus[]>(this.apiContext.buildUrl(`/api/v1/llm/circuit-breakers`))
  }

getBudgetSummary(): Observable<any> {
    return this.http.get(this.apiContext.buildUrl(`/api/v1/llm/budget/summary`))
  }

stageDeployment(model_id: string, rollout_percent: number): Observable<DeploymentStageResponse> {
    return this.http.post<DeploymentStageResponse>(this.apiContext.buildUrl(`/api/v1/deployment/stage`), { model_id, rollout_percent })
  }

publishDeployment(model_id: string): Observable<DeploymentPublishResponse> {
    return this.http.post<DeploymentPublishResponse>(this.apiContext.buildUrl(`/api/v1/deployment/publish?model_id=${encodeURIComponent(model_id)}`), {})
  }

rollbackDeployment(model_id: string): Observable<DeploymentPublishResponse> {
    return this.http.post<DeploymentPublishResponse>(this.apiContext.buildUrl(`/api/v1/deployment/rollback?model_id=${encodeURIComponent(model_id)}`), {})
  }

precheckDeployment(model_id: string): Observable<{ precheck_passed: boolean; bias_score: number; safety_warnings?: string | null }> {
    return this.http.post<{ precheck_passed: boolean; bias_score: number; safety_warnings?: string | null }>(this.apiContext.buildUrl(`/api/v1/deployment/precheck?model_id=${encodeURIComponent(model_id)}`), {})
  }

getGPUUsage(user_id: string): Observable<GPUUsageResponse> {
    return this.http.get<GPUUsageResponse>(this.apiContext.buildUrl(`/api/v1/resources/gpu/usage/${encodeURIComponent(user_id)}`))
  }

setGPUBudget(user_id: string, budget: number): Observable<GPUBudgetResponse> {
    return this.http.post<GPUBudgetResponse>(this.apiContext.buildUrl(`/api/v1/resources/gpu/budget`), { user_id, budget })
  }

setLLMABExperiment(experiment_id: number): Observable<ABExperimentSetResponse> {
    return this.http.post<ABExperimentSetResponse>(this.apiContext.buildUrl(`/api/v1/llm/ab/set-experiment`), { experiment_id })
  }
}
