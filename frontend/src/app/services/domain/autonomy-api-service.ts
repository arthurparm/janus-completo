import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { MetaAgentLatestReportResponse, MetaAgentHeartbeatStatus, Goal, GoalCreateRequest, AutonomyStartRequest, AutonomyStatusResponse, AutonomyPlanResponse, AutonomyPolicyUpdateRequest, AdminBacklogSyncResponse, AdminBacklogSprintType, SelfStudyRun, SelfStudyStatusResponse, AdminCodeQaResponse } from '../../models';
import { AdminActionsApiService } from './admin-actions-api-service';

@Injectable({ providedIn: 'root' })
export class AutonomyApiService {
  constructor(private adminActions: AdminActionsApiService) {}

getMetaAgentLatestReport(): Observable<MetaAgentLatestReportResponse> {
    return this.adminActions.execute<MetaAgentLatestReportResponse>('get_latest_report_api_v1_meta_agent_report_latest_get');
  }

getMetaAgentHeartbeatStatus(): Observable<MetaAgentHeartbeatStatus> {
    return this.adminActions.execute<MetaAgentHeartbeatStatus>('get_heartbeat_status_api_v1_meta_agent_heartbeat_status_get');
  }

startAutonomy(req: AutonomyStartRequest): Observable<{ status: string; interval_seconds: number }> {
    return this.adminActions.execute<{ status: string; interval_seconds: number }>('start_autonomy_api_v1_autonomy_start_post', { payload: { ...req } })
  }

stopAutonomy(): Observable<{ status: string }> {
    return this.adminActions.execute<{ status: string }>('stop_autonomy_api_v1_autonomy_stop_post')
  }

getAutonomyStatus(): Observable<AutonomyStatusResponse> {
    return this.adminActions.execute<AutonomyStatusResponse>('autonomy_status_api_v1_autonomy_status_get')
  }

getAutonomyPlan(): Observable<AutonomyPlanResponse> {
    return this.adminActions.execute<AutonomyPlanResponse>('get_autonomy_plan_api_v1_autonomy_plan_get')
  }

updateAutonomyPlan(plan: { tool: string; args: Record<string, unknown> }[]): Observable<{ status: string; steps_count: number }> {
    return this.adminActions.execute<{ status: string; steps_count: number }>('update_autonomy_plan_api_v1_autonomy_plan_put', { payload: { plan } })
  }

updateAutonomyPolicy(req: AutonomyPolicyUpdateRequest): Observable<{ status: string; policy: Record<string, unknown> }> {
    return this.adminActions.execute<{ status: string; policy: Record<string, unknown> }>('update_policy_api_v1_autonomy_policy_put', { payload: { ...req } })
  }

listGoals(status?: string): Observable<Goal[]> {
    return this.adminActions.execute<Goal[]>('list_goals_api_v1_autonomy_goals_get', {
      queryParams: status ? { status } : {},
    })
  }

getGoal(goal_id: string): Observable<Goal> {
    return this.adminActions.execute<Goal>('get_goal_api_v1_autonomy_goals__goal_id__get', { pathParams: { goal_id } })
  }

createGoal(req: GoalCreateRequest): Observable<Goal> {
    return this.adminActions.execute<Goal>('create_goal_api_v1_autonomy_goals_post', { payload: { ...req } })
  }

updateGoalStatus(goal_id: string, status: 'pending' | 'in_progress' | 'completed' | 'failed'): Observable<Goal> {
    return this.adminActions.execute<Goal>('update_goal_status_api_v1_autonomy_goals__goal_id__status_patch', {
      pathParams: { goal_id },
      payload: { status },
    })
  }

deleteGoal(goal_id: string): Observable<{ status: string; goal_id: string }> {
    return this.adminActions.execute<{ status: string; goal_id: string }>('delete_goal_api_v1_autonomy_goals__goal_id__delete', { pathParams: { goal_id } })
  }

syncAutonomyAdminBacklog(): Observable<AdminBacklogSyncResponse> {
    return this.adminActions.execute<AdminBacklogSyncResponse>('sync_backlog_api_v1_autonomy_admin_backlog_sync_post')
  }

getAutonomyAdminBoard(params: { status?: string; limit?: number } = {}): Observable<{ items: AdminBacklogSprintType[] }> {
    return this.adminActions.execute<{ items: AdminBacklogSprintType[] }>('get_board_api_v1_autonomy_admin_board_get', {
      queryParams: { ...(params.status ? { status: params.status } : {}), limit: params.limit ?? 200 },
    })
  }

runAutonomyAdminSelfStudy(req: { mode: 'incremental' | 'full'; reason?: string }): Observable<{ status: string; run_id: number }> {
    return this.adminActions.execute<{ status: string; run_id: number }>('run_self_study_api_v1_autonomy_admin_self_study_run_post', { payload: { ...req } })
  }

getAutonomyAdminSelfStudyStatus(): Observable<SelfStudyStatusResponse> {
    return this.adminActions.execute<SelfStudyStatusResponse>('self_study_status_api_v1_autonomy_admin_self_study_status_get')
  }

listAutonomyAdminSelfStudyRuns(limit: number = 20): Observable<{ items: SelfStudyRun[] }> {
    return this.adminActions.execute<{ items: SelfStudyRun[] }>('self_study_runs_api_v1_autonomy_admin_self_study_runs_get', { queryParams: { limit } })
  }

askAutonomyAdminCodeQa(req: { question: string; limit?: number; citation_limit?: number }): Observable<AdminCodeQaResponse> {
    return this.adminActions.execute<AdminCodeQaResponse>('code_qa_api_v1_autonomy_admin_code_qa_post', { payload: { ...req } })
  }
}
