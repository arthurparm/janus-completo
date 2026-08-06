import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiContextService } from '../api-context.service';
import { SystemStatus, ServiceHealthResponse, QueueInfoResponse, SystemOverviewResponse, DbValidationResponse, WorkersStatusResponse, AutoAnalysisResponse } from '../../models';
import { AdminActionsApiService } from './admin-actions-api-service';

@Injectable({ providedIn: 'root' })
export class SystemApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService,
    private adminActions: AdminActionsApiService
  ) {}

health(): Observable<{ status: string }> {
    return this.http.get<{ status: string }>(this.apiContext.buildUrl(`/healthz/user`));
}

getSystemStatus(): Observable<SystemStatus> {
    return this.http.get<SystemStatus>(this.apiContext.buildUrl(`/api/v1/system/status/user`), {
      headers: { 'ngsw-bypass': 'true' }
    });
  }

getServicesHealth(): Observable<ServiceHealthResponse> {
    return this.adminActions.execute<ServiceHealthResponse>('get_services_health_api_v1_system_health_services_get');
  }

getWorkersStatus(): Observable<WorkersStatusResponse> {
    return this.adminActions.execute<WorkersStatusResponse>('workers_status_api_v1_workers_status_get');
  }

getQueueInfo(queueName: string): Observable<QueueInfoResponse> {
    return this.adminActions.execute<QueueInfoResponse>('get_queue_info_api_v1_tasks_queue__queue_name__get', { pathParams: { queue_name: queueName } });
  }

getSystemOverview(): Observable<SystemOverviewResponse> {
    return this.adminActions.execute<SystemOverviewResponse>('get_system_overview_api_v1_system_overview_get');
  }

startAllWorkers(): Observable<{ status: string; workers: string[] }> {
    return this.adminActions.execute<{ status: string; workers: string[] }>('start_workers_api_v1_workers_start_all_post');
  }

stopAllWorkers(): Observable<{ status: string; workers: string[] }> {
    return this.adminActions.execute<{ status: string; workers: string[] }>('stop_workers_api_v1_workers_stop_all_post');
  }

runAutoAnalysis(): Observable<AutoAnalysisResponse> {
    return this.adminActions.execute<AutoAnalysisResponse>('auto_analyze_api_v1_auto_analysis_health_check_get')
  }

getSystemDbValidate(): Observable<DbValidationResponse> {
    return this.adminActions.execute<DbValidationResponse>('validate_db_schema_api_v1_system_db_validate_get')
  }
}
