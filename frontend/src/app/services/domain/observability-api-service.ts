import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiContextService } from '../api-context.service';
import { PostSprintSummaryResponse, MetricsSummary, QuarantinedMessagesResponse, GraphQuarantineListResponse, AuditEventsResponse, ConsentsListResponse, PendingAction, PendingActionLegacyResidueSummary, PoisonPillStats, ObservabilitySystemHealth } from '../../models';
import { AdminActionsApiService } from './admin-actions-api-service';

@Injectable({ providedIn: 'root' })
export class ObservabilityApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService,
    private adminActions: AdminActionsApiService
  ) {}

getObservabilitySystemHealth(): Observable<ObservabilitySystemHealth> {
    return this.adminActions.execute<ObservabilitySystemHealth>('get_system_health_api_v1_observability_health_system_get')
  }

getObservabilityMetricsSummary(): Observable<MetricsSummary> {
    return this.adminActions.execute<MetricsSummary>('get_metrics_summary_api_v1_observability_metrics_summary_get')
  }

getMetricsSummary(): Observable<MetricsSummary> {
    return this.getObservabilityMetricsSummary()
  }

getQuarantinedMessages(queue?: string): Observable<QuarantinedMessagesResponse> {
    return this.adminActions.execute<QuarantinedMessagesResponse>('get_quarantined_messages_api_v1_observability_poison_pills_quarantined_get', {
      queryParams: queue ? { queue } : {},
    })
  }

cleanupQuarantine(): Observable<{ status: string; count: number }> {
    return this.adminActions.execute<{ status: string; count: number }>('cleanup_quarantine_api_v1_observability_poison_pills_cleanup_post')
  }

getPoisonPillStats(queue?: string): Observable<PoisonPillStats> {
    return this.adminActions.execute<PoisonPillStats>('get_poison_pill_stats_api_v1_observability_poison_pills_stats_get', {
      queryParams: queue ? { queue } : {},
    })
  }

listGraphQuarantine(limit: number = 100, offset: number = 0, filters?: { type?: string; reason?: string; confidence_ge?: number }): Observable<GraphQuarantineListResponse> {
    return this.adminActions.execute<GraphQuarantineListResponse>('graph_quarantine_list_api_v1_observability_graph_quarantine_get', {
      queryParams: {
        limit,
        offset,
        ...(filters?.type ? { type: filters.type } : {}),
        ...(filters?.reason ? { reason: filters.reason } : {}),
        ...(typeof filters?.confidence_ge !== 'undefined' ? { confidence_ge: filters.confidence_ge } : {}),
      },
    })
  }

promoteQuarantine(node_id: number): Observable<{ status: string; node_id: number }> {
    return this.adminActions.execute<{ status: string; node_id: number }>('graph_quarantine_promote_api_v1_observability_graph_quarantine_promote_post', { payload: { node_id } })
  }

listAuditEvents(params: { tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number } = {}): Observable<AuditEventsResponse> {
    return this.adminActions.execute<AuditEventsResponse>('audit_events_api_v1_observability_audit_events_get', {
      queryParams: {
        ...(params.tool ? { tool: params.tool } : {}),
        ...(params.status ? { status: params.status } : {}),
        ...(typeof params.start_ts !== 'undefined' ? { start_ts: params.start_ts } : {}),
        ...(typeof params.end_ts !== 'undefined' ? { end_ts: params.end_ts } : {}),
        limit: params.limit ?? 100,
        offset: params.offset ?? 0,
      },
    })
  }

listPendingActions(params: {
    include_graph?: boolean;
    include_sql?: boolean;
    pending_status?: string;
    limit?: number;
  } = {}): Observable<PendingAction[]> {
    const qs = new URLSearchParams()
    if (typeof params.include_graph !== 'undefined') qs.set('include_graph', String(params.include_graph))
    if (typeof params.include_sql !== 'undefined') qs.set('include_sql', String(params.include_sql))
    if (params.pending_status) qs.set('pending_status', params.pending_status)
    if (typeof params.limit !== 'undefined') qs.set('limit', String(params.limit))
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    return this.http.get<PendingAction[]>(this.apiContext.buildUrl(`/api/v1/pending_actions/${suffix}`))
  }

  getPendingActionsLegacyResidue(limit: number = 20): Observable<PendingActionLegacyResidueSummary> {
    return this.adminActions.execute<PendingActionLegacyResidueSummary>('pending_actions_legacy_residue_api_v1_observability_pending_actions_legacy_residue_get', { queryParams: { limit } })
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

listConsents(): Observable<ConsentsListResponse> {
    return this.http.get<ConsentsListResponse>(this.apiContext.buildUrl(`/api/v1/consents/`))
  }

grantConsent(scope: string, granted: boolean = true, expires_at?: string): Observable<{ status: string; scope: string }> {
    const body: Record<string, unknown> = { scope, granted: granted ? 'True' : 'False' }
    if (expires_at) body['expires_at'] = expires_at
    return this.http.post<{ status: string; scope: string }>(this.apiContext.buildUrl(`/api/v1/consents/`), body)
  }

revokeConsent(consent_id: number): Observable<{ status: string; consent_id: string }> {
    return this.http.post<{ status: string; consent_id: string }>(this.apiContext.buildUrl(`/api/v1/consents/${encodeURIComponent(String(consent_id))}/revoke`), {})
  }

exportAuditCSV(params: { tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number }): Observable<string> {
    return this.adminActions.executeText('export_audit_events_api_v1_observability_audit_export_get', {
      queryParams: {
        ...(params.tool ? { tool: params.tool } : {}),
        ...(params.status ? { status: params.status } : {}),
        ...(params.start_ts != null ? { start_ts: params.start_ts } : {}),
        ...(params.end_ts != null ? { end_ts: params.end_ts } : {}),
        ...(params.limit != null ? { limit: params.limit } : {}),
        ...(params.offset != null ? { offset: params.offset } : {}),
      },
    })
  }

exportAuditEvents(
    format: 'csv' | 'json',
    params: { tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number; fields?: string[] } = {}
  ): Observable<string> {
    return this.adminActions.executeText('export_audit_events_api_v1_observability_audit_export_get', {
      queryParams: {
        ...params,
        limit: params.limit ?? 1000,
        offset: params.offset ?? 0,
        format,
        ...(params.fields?.length ? { fields: params.fields.join(',') } : {}),
      },
    })
  }

getReflexionSummary(limit: number = 10): Observable<PostSprintSummaryResponse> {
    const qs = new URLSearchParams({ limit: String(limit) })
    return this.http.get<PostSprintSummaryResponse>(this.apiContext.buildUrl(`/api/v1/reflexion/summary/post_sprint?${qs.toString()}`))
  }
}
