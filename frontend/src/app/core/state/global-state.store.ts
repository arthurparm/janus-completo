import { Injectable, signal } from '@angular/core';
import { BackendApiService, SystemStatus, ServiceHealthItem, WorkerStatusResponse, SystemOverviewResponse } from '../../services/backend-api.service';
import { take, timeout, retry } from 'rxjs/operators';
import { Subscription, timer } from 'rxjs';
import { switchMap } from 'rxjs';
import { AppLoggerService } from '../services/app-logger.service';

@Injectable({ providedIn: 'root' })
export class GlobalStateStore {
  // Signals para reuso entre páginas
  readonly loading = signal<boolean>(false);
  readonly apiHealthy = signal<'unknown' | 'ok'>('unknown');
  readonly systemStatus = signal<SystemStatus | undefined>(undefined);
  readonly services = signal<ServiceHealthItem[]>([]);
  readonly workers = signal<WorkerStatusResponse[]>([]);

  // Controle interno
  private initialized = false;
  private pollSub?: Subscription;
  private spinnerSafetyTimeout?: ReturnType<typeof setTimeout>;

  constructor(private api: BackendApiService, private logger: AppLoggerService) { }

  // Uma única carga (usada internamente pelo startPolling)
  private fetchOverviewOnce(): Promise<boolean> {
    return new Promise((resolve) => {
      this.logger.debug('[Store] Fetching system overview');
      this.api.getSystemOverview().pipe(
        take(1),
        timeout({ each: 5000 }),
        retry({ count: 1 })
      ).subscribe({
        next: (overview: SystemOverviewResponse) => {
          this.logger.debug('[Store] System overview received', overview);
          this.apiHealthy.set(overview.system_status.status === 'ok' ? 'ok' : 'unknown');
          this.systemStatus.set(overview.system_status);
          this.services.set(overview.services_status || []);
          this.workers.set(overview.workers_status || []);
          resolve(true);
        },
        error: (error) => {
          this.logger.error('[Store] Failed to fetch system overview', error);
          resolve(false);
        }
      });
    });
  }

  // Inicia polling controlado (primeiro tick mostra spinner, demais silenciosos)
  startPolling(intervalMs: number): void {
    if (this.pollSub) this.pollSub.unsubscribe();
    const showSpinner = !this.initialized;
    if (showSpinner) this.loading.set(true);
    this.logger.debug('[Store] startPolling', { intervalMs, showSpinner });

    // Fallback de segurança: garante que o spinner não fique infinito
    if (showSpinner) {
      if (this.spinnerSafetyTimeout) clearTimeout(this.spinnerSafetyTimeout);
      this.spinnerSafetyTimeout = setTimeout(() => {
        if (!this.initialized) {
          this.loading.set(false);
          this.initialized = true;
          this.logger.debug('[Store] safety timeout -> spinner off');
        }
      }, Math.min(intervalMs + 5000, 10000));
    }

    this.pollSub = timer(0, intervalMs).pipe(
      switchMap(() => {
        this.logger.debug('[Store] polling tick');
        return this.api.getSystemOverview().pipe(
          take(1),
          timeout({ each: 5000 }),
          retry({ count: 1 })
        )
      })
    ).subscribe({
      next: (overview: SystemOverviewResponse) => {
        this.logger.debug('[Store] overview received', {
          apiStatus: overview.system_status.status,
          services: (overview.services_status || []).length,
          workers: (overview.workers_status || []).length
        });
        this.apiHealthy.set(overview.system_status.status === 'ok' ? 'ok' : 'unknown');
        this.systemStatus.set(overview.system_status);
        this.services.set(overview.services_status || []);
        this.workers.set(overview.workers_status || []);
        if (showSpinner && !this.initialized) {
          this.loading.set(false);
          this.initialized = true;
          if (this.spinnerSafetyTimeout) { clearTimeout(this.spinnerSafetyTimeout); this.spinnerSafetyTimeout = undefined; }
          this.logger.debug('[Store] first load complete; spinner off');
        }
      },
      error: (err) => {
        this.logger.debug('[Store] overview error', err?.message || err);
        if (showSpinner && !this.initialized) {
          this.loading.set(false);
          this.initialized = true;
          if (this.spinnerSafetyTimeout) { clearTimeout(this.spinnerSafetyTimeout); this.spinnerSafetyTimeout = undefined; }
          this.logger.debug('[Store] first load error; spinner off');
        }
      }
    });
  }

  stopPolling(): void {
    this.pollSub?.unsubscribe();
    this.pollSub = undefined;
    if (this.spinnerSafetyTimeout) { clearTimeout(this.spinnerSafetyTimeout); this.spinnerSafetyTimeout = undefined; }
    this.logger.debug('[Store] stopPolling');
  }

  // Ações de workers
  startAllWorkers(): void {
    this.logger.debug('[Store] startAllWorkers');
    this.api.startAllWorkers().pipe(take(1)).subscribe({
      next: () => { this.logger.debug('[Store] startAllWorkers -> ok'); this.refreshWorkers(); },
      error: (e) => { this.logger.debug('[Store] startAllWorkers -> error', e?.message || e); }
    });
  }

  stopAllWorkers(): void {
    this.logger.debug('[Store] stopAllWorkers');
    this.api.stopAllWorkers().pipe(take(1)).subscribe({
      next: () => { this.logger.debug('[Store] stopAllWorkers -> ok'); this.refreshWorkers(); },
      error: (e) => { this.logger.debug('[Store] stopAllWorkers -> error', e?.message || e); }
    });
  }

  refreshWorkers(): void {
    this.logger.debug('[Store] refreshWorkers');
    this.api.getWorkersStatus().pipe(take(1)).subscribe({
      next: (resp) => { this.logger.debug('[Store] refreshWorkers -> received', (resp.workers || []).length); this.workers.set(resp.workers || []); },
      error: (e) => { this.logger.debug('[Store] refreshWorkers -> error', e?.message || e); }
    });
  }

  refreshSystemStatus(): void {
    this.logger.debug('[Store] refreshSystemStatus (manual)');
    this.fetchOverviewOnce().then(ok => {
      this.logger.debug('[Store] refreshSystemStatus completed', ok ? 'successfully' : 'with errors');
    });
  }
}
