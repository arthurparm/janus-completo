import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiContextService } from '../api-context.service';
import { PostSprintSummaryResponse, MetricsSummary, QuarantinedMessagesResponse, GraphQuarantineListResponse, AuditEventsResponse, ReviewerMetricsResponse, PeriodReportResponse, ConsentsListResponse, PendingAction, PoisonPillStats, ObservabilitySystemHealth } from '../../models';

@Injectable({ providedIn: 'root' })
export class ObservabilityApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getObservabilitySystemHealth(): Observable<ObservabilitySystemHealth> {
    return this.http.get<ObservabilitySystemHealth>(this.apiContext.buildUrl(`/api/v1/observability/health/system`))
  }

getObservabilityMetricsSummary(): Observable<MetricsSummary> {
    return this.http.get<MetricsSummary>(this.apiContext.buildUrl(`/api/v1/observability/metrics/summary`))
  }

getMetricsSummary(): Observable<MetricsSummary> {
    return this.getObservabilityMetricsSummary()
  }

getQuarantinedMessages(queue?: string): Observable<QuarantinedMessagesResponse> {
    const params = queue ? `?queue=${encodeURIComponent(queue)}` : ''
    return this.http.get<QuarantinedMessagesResponse>(this.apiContext.buildUrl(`/api/v1/observability/poison-pills/quarantined${params}`))
  }

cleanupQuarantine(): Observable<{ status: string; count: number }> {
    return this.http.post<{ status: string; count: number }>(this.apiContext.buildUrl(`/api/v1/observability/poison-pills/cleanup`), {})
  }

getPoisonPillStats(queue?: string): Observable<PoisonPillStats> {
    const params = queue ? `?queue=${encodeURIComponent(queue)}` : ''
    return this.http.get<PoisonPillStats>(this.apiContext.buildUrl(`/api/v1/observability/poison-pills/stats${params}`))
  }

listGraphQuarantine(limit: number = 100, offset: number = 0, filters?: { type?: string; reason?: string; confidence_ge?: number }): Observable<GraphQuarantineListResponse> {
    const qs = new URLSearchParams()
    qs.set('limit', String(limit))
    qs.set('offset', String(offset))
    if (filters?.type) qs.set('type', filters.type)
    if (filters?.reason) qs.set('reason', filters.reason)
    if (typeof filters?.confidence_ge !== 'undefined') qs.set('confidence_ge', String(filters?.confidence_ge))
    return this.http.get<GraphQuarantineListResponse>(this.apiContext.buildUrl(`/api/v1/observability/graph/quarantine?${qs.toString()}`))
  }

promoteQuarantine(node_id: number): Observable<{ status: string; node_id: number }> {
    return this.http.post<{ status: string; node_id: number }>(this.apiContext.buildUrl(`/api/v1/observability/graph/quarantine/promote`), { node_id })
  }

rejectQuarantine(node_id: number, reason: string): Observable<{ status: string; node_id: number }> {
    return this.http.post<{ status: string; node_id: number }>(this.apiContext.buildUrl(`/api/v1/observability/graph/quarantine/reject`), { node_id, reason })
  }

registerSynonym(label: string, alias: string, canonical: string): Observable<{ status: string; synonym_id: number }> {
    return this.http.post<{ status: string; synonym_id: number }>(this.apiContext.buildUrl(`/api/v1/observability/graph/entities/synonym`), { label, alias, canonical })
  }

listAuditEvents(params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number } = {}): Observable<AuditEventsResponse> {
    const qs = new URLSearchParams()
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.tool) qs.set('tool', params.tool)
    if (params.status) qs.set('status', params.status)
    if (typeof params.start_ts !== 'undefined') qs.set('start_ts', String(params.start_ts))
    if (typeof params.end_ts !== 'undefined') qs.set('end_ts', String(params.end_ts))
    qs.set('limit', String(params.limit ?? 100))
    qs.set('offset', String(params.offset ?? 0))
    return this.http.get<AuditEventsResponse>(this.apiContext.buildUrl(`/api/v1/observability/audit/events?${qs.toString()}`))
  }

listPendingActions(params: {
    include_graph?: boolean;
    include_sql?: boolean;
    user_id?: string;
    pending_status?: string;
    limit?: number;
  } = {}): Observable<PendingAction[]> {
    const qs = new URLSearchParams()
    if (typeof params.include_graph !== 'undefined') qs.set('include_graph', String(params.include_graph))
    if (typeof params.include_sql !== 'undefined') qs.set('include_sql', String(params.include_sql))
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.pending_status) qs.set('pending_status', params.pending_status)
    if (typeof params.limit !== 'undefined') qs.set('limit', String(params.limit))
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    return this.http.get<PendingAction[]>(this.apiContext.buildUrl(`/api/v1/pending_actions/${suffix}`))
  }

approvePendingAction(action: PendingAction): Observable<PendingAction> {
    if (typeof action?.action_id === 'number') {
      return this.http.post<PendingAction>(
        this.apiContext.buildUrl(`/api/v1/pending_actions/action/${encodeURIComponent(String(action.action_id))}/approve`),
        {}
      )
    }
    if (!action?.thread_id) {
      throw new Error('Invalid pending action: missing action_id/thread_id')
    }
    return this.http.post<PendingAction>(
      this.apiContext.buildUrl(`/api/v1/pending_actions/${encodeURIComponent(action.thread_id)}/approve`),
      {}
    )
  }

rejectPendingAction(action: PendingAction): Observable<PendingAction> {
    if (typeof action?.action_id === 'number') {
      return this.http.post<PendingAction>(
        this.apiContext.buildUrl(`/api/v1/pending_actions/action/${encodeURIComponent(String(action.action_id))}/reject`),
        {}
      )
    }
    if (!action?.thread_id) {
      throw new Error('Invalid pending action: missing action_id/thread_id')
    }
    return this.http.post<PendingAction>(
      this.apiContext.buildUrl(`/api/v1/pending_actions/${encodeURIComponent(action.thread_id)}/reject`),
      {}
    )
  }

getReviewerMetrics(user_id: number, start_ts?: number, end_ts?: number): Observable<ReviewerMetricsResponse> {
    const qs = new URLSearchParams()
    qs.set('user_id', String(user_id))
    if (typeof start_ts !== 'undefined') qs.set('start_ts', String(start_ts))
    if (typeof end_ts !== 'undefined') qs.set('end_ts', String(end_ts))
    return this.http.get<ReviewerMetricsResponse>(this.apiContext.buildUrl(`/api/v1/observability/hitl/metrics/reviewer?${qs.toString()}`))
  }

getHitlReports(period: 'daily' | 'weekly' | 'monthly' = 'daily', start_ts?: number, end_ts?: number): Observable<PeriodReportResponse> {
    const qs = new URLSearchParams()
    qs.set('period', period)
    if (typeof start_ts !== 'undefined') qs.set('start_ts', String(start_ts))
    if (typeof end_ts !== 'undefined') qs.set('end_ts', String(end_ts))
    return this.http.get<PeriodReportResponse>(this.apiContext.buildUrl(`/api/v1/observability/hitl/reports?${qs.toString()}`))
  }

listConsents(user_id: number): Observable<ConsentsListResponse> {
    return this.http.get<ConsentsListResponse>(this.apiContext.buildUrl(`/api/v1/consents/?user_id=${encodeURIComponent(String(user_id))}`))
  }

grantConsent(user_id: number, scope: string, granted: boolean = true, expires_at?: string): Observable<{ status: string; scope: string }> {
    const body: Record<string, unknown> = { user_id: String(user_id), scope, granted: granted ? 'True' : 'False' }
    if (expires_at) body['expires_at'] = expires_at
    return this.http.post<{ status: string; scope: string }>(this.apiContext.buildUrl(`/api/v1/consents/`), body)
  }

revokeConsent(consent_id: number): Observable<{ status: string; consent_id: string }> {
    return this.http.post<{ status: string; consent_id: string }>(this.apiContext.buildUrl(`/api/v1/consents/${encodeURIComponent(String(consent_id))}/revoke`), {})
  }

exportAuditCSV(params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number }): Observable<string> {
    const qs = new URLSearchParams()
    if (params.user_id) qs.set('user_id', String(params.user_id))
    if (params.tool) qs.set('tool', String(params.tool))
    if (params.status) qs.set('status', String(params.status))
    if (params.start_ts != null) qs.set('start_ts', String(params.start_ts))
    if (params.end_ts != null) qs.set('end_ts', String(params.end_ts))
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.offset != null) qs.set('offset', String(params.offset))
    return this.http.get(this.apiContext.buildUrl(`/api/v1/observability/audit/export?${qs.toString()}`), { responseType: 'text' })
  }

exportAuditEvents(
    format: 'csv' | 'json',
    params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number; fields?: string[] } = {}
  ): Observable<string> {
    const qs = new URLSearchParams()
    if (params.user_id) qs.set('user_id', String(params.user_id))
    if (params.tool) qs.set('tool', String(params.tool))
    if (params.status) qs.set('status', String(params.status))
    if (params.start_ts != null) qs.set('start_ts', String(params.start_ts))
    if (params.end_ts != null) qs.set('end_ts', String(params.end_ts))
    qs.set('limit', String(params.limit ?? 1000))
    qs.set('offset', String(params.offset ?? 0))
    qs.set('format', format)
    if (params.fields && params.fields.length) qs.set('fields', params.fields.join(','))
    return this.http.get(this.apiContext.buildUrl(`/api/v1/observability/audit/export?${qs.toString()}`), { responseType: 'text' })
  }

getReflexionSummary(limit: number = 10): Observable<PostSprintSummaryResponse> {
    const qs = new URLSearchParams({ limit: String(limit) })
    return this.http.get<PostSprintSummaryResponse>(this.apiContext.buildUrl(`/api/v1/reflexion/summary/post_sprint?${qs.toString()}`))
  }
}
