import {Injectable} from '@angular/core';
import {HttpClient} from '@angular/common/http';
import {Observable} from 'rxjs';

export interface SystemStatus {
  app_name: string;
  version: string;
  environment: string;
  status: string;
  timestamp?: string;
  uptime_seconds?: number;
  system?: Record<string, any>;
  process?: Record<string, any>;
  performance?: Record<string, any>;
  config?: Record<string, any>;
}

export interface ServiceHealthItem {
  key: string;
  name: string;
  status: string;
  metric_text?: string | null;
}

export interface ServiceHealthResponse {
  services: ServiceHealthItem[];
}

export interface WorkersStatusItem {
  name: string;
  running: boolean;
  done: boolean;
  cancelled: boolean;
  exception?: string | null;
}

export interface WorkersStatusResponse {
  tracked: number;
  workers: WorkersStatusItem[];
}

export interface LLMProviderInfo { [key: string]: any }
export interface LLMHealth { status: string; details?: Record<string, any> }
export interface LLMCacheEntry { [key: string]: any }
export interface LLMCacheStatusResponse { total_cached: number; cache_entries: LLMCacheEntry[] }
export interface CircuitBreakerStatus { provider: string; state: string; failure_count: number; last_failure_time?: number | null }

export interface MetricsSummary {
  llm: { cached_llms: number; circuit_breakers: Record<string, { state: string; failure_count: number }> };
  multi_agent: { active_agents: number; workspace_tasks: number; workspace_artifacts: number };
  poison_pills: Record<string, any>;
}

export interface QuarantinedMessage {
  message_id: string; queue: string; reason: string; failure_count: number; quarantined_at: string;
}

export interface QuarantinedMessagesResponse {
  total_quarantined: number; messages: QuarantinedMessage[];
}

export interface ContextInfo { [key: string]: any }
export interface WebSearchResult { [key: string]: any }
export interface WebCacheStatus { [key: string]: any }

@Injectable({providedIn: 'root'})
export class JanusApiService {
  constructor(private http: HttpClient) {}

  // Basic API health (useful for quick checks)
  health(): Observable<{status: string}> {
    return this.http.get<{status: string}>(`/healthz`);
  }

  // System status overview
  getSystemStatus(): Observable<SystemStatus> {
    return this.http.get<SystemStatus>(`/api/v1/system/status`);
  }

  // Services health breakdown
  getServicesHealth(): Observable<ServiceHealthResponse> {
    return this.http.get<ServiceHealthResponse>(`/api/v1/system/health/services`);
  }

  // Workers orchestration
  getWorkersStatus(): Observable<WorkersStatusResponse> {
    return this.http.get<WorkersStatusResponse>(`/api/v1/workers/status`);
  }

  startAllWorkers(): Observable<any> {
    return this.http.post(`/api/v1/workers/start-all`, {});
  }

  stopAllWorkers(): Observable<any> {
    return this.http.post(`/api/v1/workers/stop-all`, {});
  }
  // LLM subsystem
  listLLMProviders(): Observable<any> {
    return this.http.get<any>(`/api/v1/llm/providers`)
  }

  getLLMHealth(): Observable<any> {
    return this.http.get<any>(`/api/v1/llm/health`)
  }

  getLLMCacheStatus(): Observable<LLMCacheStatusResponse> {
    return this.http.get<LLMCacheStatusResponse>(`/api/v1/llm/cache/status`)
  }

  getLLMCircuitBreakers(): Observable<CircuitBreakerStatus[]> {
    return this.http.get<CircuitBreakerStatus[]>(`/api/v1/llm/circuit-breakers`)
  }

  // Observability
  getObservabilitySystemHealth(): Observable<any> {
    return this.http.get<any>(`/api/v1/observability/health/system`)
  }

  getObservabilityMetricsSummary(): Observable<MetricsSummary> {
    return this.http.get<MetricsSummary>(`/api/v1/observability/metrics/summary`)
  }

  getQuarantinedMessages(queue?: string): Observable<QuarantinedMessagesResponse> {
    const params = queue ? `?queue=${encodeURIComponent(queue)}` : ''
    return this.http.get<QuarantinedMessagesResponse>(`/api/v1/observability/poison-pills/quarantined${params}`)
  }

  cleanupQuarantine(): Observable<any> {
    return this.http.post(`/api/v1/observability/poison-pills/cleanup`, {})
  }

  getPoisonPillStats(queue?: string): Observable<any> {
    const params = queue ? `?queue=${encodeURIComponent(queue)}` : ''
    return this.http.get<any>(`/api/v1/observability/poison-pills/stats${params}`)
  }

  // Context
  getCurrentContext(): Observable<ContextInfo> {
    return this.http.get<ContextInfo>(`/api/v1/context/current`)
  }

  searchWeb(query: string, max_results: number = 5, search_depth: 'basic' | 'advanced' = 'basic'): Observable<WebSearchResult> {
    const params = new URLSearchParams({ query, max_results: String(max_results), search_depth })
    return this.http.get<WebSearchResult>(`/api/v1/context/web-search?${params.toString()}`)
  }

  getWebCacheStatus(): Observable<WebCacheStatus> {
    return this.http.get<WebCacheStatus>(`/api/v1/context/web-cache/status`)
  }

  invalidateWebCache(query?: string): Observable<any> {
    return this.http.post(`/api/v1/context/web-cache/invalidate`, { query })
  }
}