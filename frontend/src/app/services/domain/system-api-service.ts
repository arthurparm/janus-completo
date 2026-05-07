import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiContextService } from '../api-context.service';
import { SystemStatus, ServiceHealthResponse, QueueInfoResponse, SystemOverviewResponse, DbValidationResponse, WorkersStatusResponse, AutoAnalysisResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class SystemApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

health(): Observable<{ status: string }> {
    return this.http.get<{ status: string }>(this.apiContext.buildUrl(`/healthz`));
  }

getSystemStatus(): Observable<SystemStatus> {
    return this.http.get<SystemStatus>(this.apiContext.buildUrl(`/api/v1/system/status`), {
      headers: { 'ngsw-bypass': 'true' }
    });
  }

getServicesHealth(): Observable<ServiceHealthResponse> {
    return this.http.get<ServiceHealthResponse>(this.apiContext.buildUrl(`/api/v1/system/health/services`));
  }

getWorkersStatus(): Observable<WorkersStatusResponse> {
    return this.http.get<WorkersStatusResponse>(this.apiContext.buildUrl(`/api/v1/workers/status`));
  }

getQueueInfo(queueName: string): Observable<QueueInfoResponse> {
    return this.http.get<QueueInfoResponse>(
      this.apiContext.buildUrl(`/api/v1/tasks/queue/${encodeURIComponent(queueName)}`)
    );
  }

getSystemOverview(): Observable<SystemOverviewResponse> {
    return this.http.get<SystemOverviewResponse>(this.apiContext.buildUrl(`/api/v1/system/overview`), {
      headers: { 'ngsw-bypass': 'true' }
    });
  }

startAllWorkers(): Observable<{ status: string; workers: string[] }> {
    return this.http.post<{ status: string; workers: string[] }>(this.apiContext.buildUrl(`/api/v1/workers/start-all`), {});
  }

stopAllWorkers(): Observable<{ status: string; workers: string[] }> {
    return this.http.post<{ status: string; workers: string[] }>(this.apiContext.buildUrl(`/api/v1/workers/stop-all`), {});
  }

runAutoAnalysis(): Observable<AutoAnalysisResponse> {
    return this.http.get<AutoAnalysisResponse>(this.apiContext.buildUrl(`/api/v1/auto-analysis/health-check`))
  }

getSystemDbValidate(): Observable<DbValidationResponse> {
    return this.http.get<DbValidationResponse>(this.apiContext.buildUrl(`/api/v1/system/db/validate`))
  }
}
