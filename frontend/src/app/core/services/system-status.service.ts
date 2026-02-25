import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, timer, of } from 'rxjs';
import { catchError, map, switchMap, shareReplay, retry } from 'rxjs/operators';
import { AppLoggerService } from './app-logger.service';
import { API_BASE_URL } from '../../services/api.config';

export interface SystemStatusResponse {
  app_name: string;
  version: string;
  environment: string;
  status: string;
  uptime_seconds: number;
  system?: any;
  process?: any;
  performance?: any;
}

export interface ServiceHealthItem {
  key: string;
  name: string;
  status: 'ok' | 'degraded' | 'error' | 'unknown';
  metric_text?: string;
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
        switchMap(() => this.http.get<SystemStatusResponse>(`${this.apiUrl}/status`).pipe(
          retry(1),
          catchError(err => {
            this.logger.error('[SystemStatusService] Erro ao buscar status do sistema', err);
            return of({
              app_name: 'Janus',
              version: 'unknown',
              environment: 'unknown',
              status: 'ERROR',
              uptime_seconds: 0
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
    // Polling mais frequente para health check (15s)
    return timer(0, 15000).pipe(
      switchMap(() => this.http.get<ServiceHealthResponse>(`${this.apiUrl}/health/services`).pipe(
        map(response => {
          // Atualiza o estado global de saúde baseado nos serviços
          const hasError = response.services.some(s => s.status === 'error');
          this._isSystemHealthy.next(!hasError);
          return response;
        }),
        catchError(err => {
          this.logger.error('[SystemStatusService] Erro ao buscar saúde dos serviços', err);
          this._isSystemHealthy.next(false);
          return of({ services: [] } as ServiceHealthResponse);
        })
      )),
      shareReplay(1)
    );
  }

  /**
   * Força uma atualização imediata (útil quando o usuário abre o HUD)
   */
  refreshHealth() {
    // A implementação com timer/switchMap atualiza automaticamente, 
    // mas se precisarmos de refresh manual, podemos resetar o cache ou usar um Subject de trigger.
    // Por enquanto, o polling automático é suficiente.
  }
}
