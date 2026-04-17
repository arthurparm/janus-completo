import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { MetaAgentLatestReportResponse, MetaAgentHeartbeatStatus, Goal, GoalCreateRequest, AutonomyStartRequest, AutonomyStatusResponse, AutonomyPlanResponse, AutonomyPolicyUpdateRequest, AdminBacklogSyncResponse, AdminBacklogSprintType, SelfStudyRun, SelfStudyStatusResponse, AdminCodeQaResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class AutonomyApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getMetaAgentLatestReport(): Observable<MetaAgentLatestReportResponse> {
    return this.http.get<MetaAgentLatestReportResponse>(this.apiContext.buildUrl(`/api/v1/meta-agent/report/latest`));
  }

getMetaAgentHeartbeatStatus(): Observable<MetaAgentHeartbeatStatus> {
    return this.http.get<MetaAgentHeartbeatStatus>(this.apiContext.buildUrl(`/api/v1/meta-agent/heartbeat/status`));
  }

startAutonomy(req: AutonomyStartRequest): Observable<{ status: string; interval_seconds: number }> {
    return this.http.post<{ status: string; interval_seconds: number }>(this.apiContext.buildUrl(`/api/v1/autonomy/start`), req)
  }

stopAutonomy(): Observable<{ status: string }> {
    return this.http.post<{ status: string }>(this.apiContext.buildUrl(`/api/v1/autonomy/stop`), {})
  }

getAutonomyStatus(): Observable<AutonomyStatusResponse> {
    return this.http.get<AutonomyStatusResponse>(this.apiContext.buildUrl(`/api/v1/autonomy/status`))
  }

getAutonomyPlan(): Observable<AutonomyPlanResponse> {
    return this.http.get<AutonomyPlanResponse>(this.apiContext.buildUrl(`/api/v1/autonomy/plan`))
  }

updateAutonomyPlan(plan: { tool: string; args: Record<string, unknown> }[]): Observable<{ status: string; steps_count: number }> {
    return this.http.put<{ status: string; steps_count: number }>(this.apiContext.buildUrl('/api/v1/autonomy/plan'), { plan })
  }

updateAutonomyPolicy(req: AutonomyPolicyUpdateRequest): Observable<{ status: string; policy: Record<string, unknown> }> {
    return this.http.put<{ status: string; policy: Record<string, unknown> }>(this.apiContext.buildUrl(`/api/v1/autonomy/policy`), req)
  }

listGoals(status?: string): Observable<Goal[]> {
    const qs = new URLSearchParams()
    if (status) qs.set('status', status)
    return this.http.get<Goal[]>(this.apiContext.buildUrl(`/api/v1/autonomy/goals${qs.toString() ? '?' + qs.toString() : ''}`))
  }

getGoal(goal_id: string): Observable<Goal> {
    return this.http.get<Goal>(this.apiContext.buildUrl(`/api/v1/autonomy/goals/${encodeURIComponent(goal_id)}`))
  }

createGoal(req: GoalCreateRequest): Observable<Goal> {
    return this.http.post<Goal>(this.apiContext.buildUrl(`/api/v1/autonomy/goals`), req)
  }

updateGoalStatus(goal_id: string, status: 'pending' | 'in_progress' | 'completed' | 'failed'): Observable<Goal> {
    return this.http.patch<Goal>(this.apiContext.buildUrl(`/api/v1/autonomy/goals/${encodeURIComponent(goal_id)}/status`), { status })
  }

deleteGoal(goal_id: string): Observable<{ status: string; goal_id: string }> {
    return this.http.delete<{ status: string; goal_id: string }>(this.apiContext.buildUrl(`/api/v1/autonomy/goals/${encodeURIComponent(goal_id)}`))
  }

syncAutonomyAdminBacklog(): Observable<AdminBacklogSyncResponse> {
    return this.http.post<AdminBacklogSyncResponse>(this.apiContext.buildUrl(`/api/v1/autonomy/admin/backlog/sync`), {})
  }

getAutonomyAdminBoard(params: { status?: string; limit?: number } = {}): Observable<{ items: AdminBacklogSprintType[] }> {
    const qs = new URLSearchParams()
    if (params.status) qs.set('status', String(params.status))
    qs.set('limit', String(params.limit ?? 200))
    return this.http.get<{ items: AdminBacklogSprintType[] }>(this.apiContext.buildUrl(`/api/v1/autonomy/admin/board?${qs.toString()}`))
  }

runAutonomyAdminSelfStudy(req: { mode: 'incremental' | 'full'; reason?: string }): Observable<{ status: string; run_id: number }> {
    return this.http.post<{ status: string; run_id: number }>(this.apiContext.buildUrl(`/api/v1/autonomy/admin/self-study/run`), req)
  }

getAutonomyAdminSelfStudyStatus(): Observable<SelfStudyStatusResponse> {
    return this.http.get<SelfStudyStatusResponse>(this.apiContext.buildUrl(`/api/v1/autonomy/admin/self-study/status`))
  }

listAutonomyAdminSelfStudyRuns(limit: number = 20): Observable<{ items: SelfStudyRun[] }> {
    const qs = new URLSearchParams()
    qs.set('limit', String(limit))
    return this.http.get<{ items: SelfStudyRun[] }>(this.apiContext.buildUrl(`/api/v1/autonomy/admin/self-study/runs?${qs.toString()}`))
  }

askAutonomyAdminCodeQa(req: { question: string; limit?: number; citation_limit?: number }): Observable<AdminCodeQaResponse> {
    return this.http.post<AdminCodeQaResponse>(this.apiContext.buildUrl(`/api/v1/autonomy/admin/code-qa`), req)
  }
}
