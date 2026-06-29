import { Injectable } from '@angular/core';
import { HttpClient, HttpContext, HttpErrorResponse } from '@angular/common/http';
import { Observable, BehaviorSubject, timer, of } from 'rxjs';
import { catchError, map, switchMap, shareReplay, retry } from 'rxjs/operators';
import { AppLoggerService } from './app-logger.service';
import { API_BASE_URL } from '../../services/api.config';
import { SUPPRESS_HTTP_ERROR_LOG } from '../interceptors/error-logger.interceptor';

export interface SystemStatusResponse {
  app_name: string;
  version: string;
  environment: string;
  status: string;
  uptime_seconds: number | null;
  system?: any;
  process?: any;
  performance?: any;
}

export interface ServiceHealthItem {
  key: string;
  name: string;
  status: 'ok' | 'degraded' | 'error' | 'unknown';
  metric_text?: string;
  capability?: string;
  user_impact?: string;
  recommended_action?: string;
}

export interface ServiceHealthResponse {
  services: ServiceHealthItem[];
}

@Injectable({
  providedIn: 'root',
})
export class SystemStatusService {
  // Reuse the same API base used by the chat/auth flows (defaults to `/api` behind the frontend proxy).
  private apiUrl = `${API_BASE_URL}/v1/system`;
  
  // Cache shareReplay para evitar múltiplas chamadas simultâneas
  private statusCache$: Observable<SystemStatusResponse> | null = null;
  private healthCache$: Observable<ServiceHealthResponse> | null = null;
  private statusConnectivityWarningActive = false;
  private healthConnectivityWarningActive = false;

  // Estado reativo para componentes ouvirem
  private _isSystemHealthy = new BehaviorSubject<boolean>(true);
  public isSystemHealthy$ = this._isSystemHealthy.asObservable();

  constructor(private http: HttpClient, private readonly logger: AppLoggerService) {}

  /**
   * Obtém o status geral do sistema (versão, uptime, etc)
   */
  getSystemStatus(): Observable<SystemStatusResponse> {
    if (!this.statusCache$) {
      this.statusCache$ = timer(0, 30000).pipe( // Polling a cada 30s
        switchMap(() => this.http.get<SystemStatusResponse>(
          `${this.apiUrl}/status`,
          { context: this.healthPollingContext() }
        ).pipe(
          map(response => {
            this.statusConnectivityWarningActive = false;
            return this.normalizeSystemStatusResponse(response);
          }),
          retry(1),
          catchError(err => {
            this.reportPollingFailure(
              'status',
              '[SystemStatusService] Backend indisponivel ao buscar status do sistema',
              '[SystemStatusService] Erro ao buscar status do sistema',
              err
            );
            return of({
              app_name: 'Janus',
              version: 'unknown',
              environment: 'unknown',
              status: 'ERROR',
              uptime_seconds: null
            } as SystemStatusResponse);
          })
        )),
        shareReplay(1)
      );
    }
    return this.statusCache$;
  }

  /**
   * Obtém a saúde detalhada dos microsserviços (Agentes, LLM, Memória)
   */
  getServicesHealth(): Observable<ServiceHealthResponse> {
    if (this.healthCache$) {
      return this.healthCache$;
    }

    // Polling mais frequente para health check (15s)
    this.healthCache$ = timer(0, 15000).pipe(
      switchMap(() => this.http.get<ServiceHealthResponse>(
        `${this.apiUrl}/health/services`,
        { context: this.healthPollingContext() }
      ).pipe(
        map(response => {
          this.healthConnectivityWarningActive = false;
          const normalized = this.normalizeServiceHealthResponse(response);
          // Atualiza o estado global de saúde baseado nos serviços
          const allServicesHealthy =
            normalized.services.length > 0 && normalized.services.every(s => s.status === 'ok');
          this._isSystemHealthy.next(allServicesHealthy);
          return normalized;
        }),
        catchError(err => {
          if (this.isConnectivityFailure(err)) {
            this.reportPollingFailure(
              'health',
              '[SystemStatusService] Backend indisponivel ao buscar saude dos servicos',
              '[SystemStatusService] Erro ao buscar saude dos servicos',
              err
            );
            this._isSystemHealthy.next(false);
            return of({ services: [] } as ServiceHealthResponse);
          }
          this.logger.error('[SystemStatusService] Erro ao buscar saúde dos serviços', err);
          this._isSystemHealthy.next(false);
          return of({ services: [] } as ServiceHealthResponse);
        })
      )),
      shareReplay({ bufferSize: 1, refCount: true })
    );
    return this.healthCache$;
  }

  /**
   * Força uma atualização imediata (útil quando o usuário abre o HUD)
   */
  refreshHealth() {
    // A implementação com timer/switchMap atualiza automaticamente, 
    // mas se precisarmos de refresh manual, podemos resetar o cache ou usar um Subject de trigger.
    // Por enquanto, o polling automático é suficiente.
  }

  private reportPollingFailure(
    channel: 'status' | 'health',
    connectivityMessage: string,
    errorMessage: string,
    err: unknown
  ): void {
    if (this.isConnectivityFailure(err)) {
      if (channel === 'status') {
        if (!this.statusConnectivityWarningActive) {
          this.logger.warn(connectivityMessage, err);
          this.statusConnectivityWarningActive = true;
        }
        return;
      }

      if (!this.healthConnectivityWarningActive) {
        this.logger.warn(connectivityMessage, err);
        this.healthConnectivityWarningActive = true;
      }
      return;
    }

    if (channel === 'status') {
      this.statusConnectivityWarningActive = false;
    } else {
      this.healthConnectivityWarningActive = false;
    }
    this.logger.error(errorMessage, err);
  }

  private isConnectivityFailure(err: unknown): boolean {
    return err instanceof HttpErrorResponse && err.status === 0;
  }

  private healthPollingContext(): HttpContext {
    return new HttpContext().set(SUPPRESS_HTTP_ERROR_LOG, true);
  }

  private normalizeSystemStatusResponse(response: unknown): SystemStatusResponse {
    const raw = response && typeof response === 'object' ? (response as Record<string, unknown>) : {};

    return {
      app_name: this.readNonEmptyString(raw['app_name']) ?? 'Janus',
      version: this.readNonEmptyString(raw['version']) ?? 'unknown',
      environment: this.readNonEmptyString(raw['environment']) ?? 'unknown',
      status: this.normalizeSystemStatus(raw['status']),
      uptime_seconds: this.readFiniteNonNegativeNumber(raw['uptime_seconds']),
      system: this.readRecord(raw['system']),
      process: this.readRecord(raw['process']),
      performance: this.readRecord(raw['performance']),
    };
  }

  private normalizeSystemStatus(rawStatus: unknown): string {
    const status = this.readNonEmptyString(rawStatus)?.toLowerCase();
    switch (status) {
      case 'operational':
      case 'ok':
      case 'healthy':
        return 'OPERATIONAL';
      case 'degraded':
      case 'warning':
      case 'unknown':
        return 'DEGRADED';
      case 'error':
      case 'critical':
      case 'unhealthy':
        return 'ERROR';
      default:
        return 'DEGRADED';
    }
  }

  private readFiniteNonNegativeNumber(value: unknown): number | null {
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) {
      return null;
    }
    return value;
  }

  private readRecord(value: unknown): Record<string, unknown> | undefined {
    if (!value || typeof value !== 'object' || Array.isArray(value)) {
      return undefined;
    }
    return value as Record<string, unknown>;
  }

  private normalizeServiceHealthResponse(response: unknown): ServiceHealthResponse {
    const rawServices =
      response && typeof response === 'object' && Array.isArray((response as { services?: unknown }).services)
        ? (response as { services: unknown[] }).services
        : [];

    return {
      services: rawServices.map((item, index) => this.normalizeServiceHealthItem(item, index)),
    };
  }

  private normalizeServiceHealthItem(item: unknown, index: number): ServiceHealthItem {
    const raw = item && typeof item === 'object' ? (item as Record<string, unknown>) : {};
    const key = this.readNonEmptyString(raw['key']) ?? `service-${index + 1}`;
    const name = this.readNonEmptyString(raw['name']) ?? 'Servico sem nome';
    const status = this.normalizeServiceStatus(raw['status']);
    const metricText = this.readNonEmptyString(raw['metric_text']);
    const capability = this.readNonEmptyString(raw['capability']);
    const userImpact = this.readNonEmptyString(raw['user_impact']);
    const recommendedAction = this.readNonEmptyString(raw['recommended_action']);

    return {
      key,
      name,
      status,
      metric_text: metricText,
      capability,
      user_impact: userImpact,
      recommended_action: recommendedAction,
    };
  }

  private normalizeServiceStatus(rawStatus: unknown): ServiceHealthItem['status'] {
    const status = this.readNonEmptyString(rawStatus)?.toLowerCase();
    if (status === 'ok' || status === 'degraded' || status === 'error' || status === 'unknown') {
      return status;
    }
    return 'unknown';
  }

  private readNonEmptyString(value: unknown): string | undefined {
    if (typeof value !== 'string') return undefined;
    const trimmed = value.trim();
    return trimmed || undefined;
  }
}
