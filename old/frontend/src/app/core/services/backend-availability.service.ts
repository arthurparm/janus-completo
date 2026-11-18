import { HttpBackend, HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, computed, signal } from '@angular/core';
import { firstValueFrom, timeout } from 'rxjs';

import { AppLoggerService } from './app-logger.service';

export type BackendAvailabilityState =
  | 'unknown'
  | 'checking'
  | 'available'
  | 'degraded'
  | 'unreachable';

export interface BackendAvailabilitySnapshot {
  state: BackendAvailabilityState;
  checkedAt: Date | null;
  detail: string | null;
}

const INITIAL_SNAPSHOT: BackendAvailabilitySnapshot = {
  state: 'unknown',
  checkedAt: null,
  detail: null,
};

@Injectable({ providedIn: 'root' })
export class BackendAvailabilityService {
  private readonly rawHttp: HttpClient;
  private readonly snapshotState = signal<BackendAvailabilitySnapshot>(INITIAL_SNAPSHOT);
  private activeProbe: Promise<boolean> | null = null;

  readonly snapshot = this.snapshotState.asReadonly();
  readonly hasIssue = computed(() => {
    const state = this.snapshotState().state;
    return state === 'checking' || state === 'degraded' || state === 'unreachable';
  });
  readonly isChecking = computed(() => this.snapshotState().state === 'checking');

  constructor(
    httpBackend: HttpBackend,
    private readonly logger: AppLoggerService,
  ) {
    // Bypass interceptors so an explicit recovery probe cannot recursively
    // mutate availability or generate duplicate global notifications.
    this.rawHttp = new HttpClient(httpBackend);
  }

  markAvailable(): void {
    this.update('available', null);
  }

  markDegraded(detail = 'O backend respondeu, mas informou indisponibilidade temporária.'): void {
    this.update('degraded', detail);
  }

  markUnreachable(detail = 'Não foi possível estabelecer conexão com o backend Janus.'): void {
    this.update('unreachable', detail);
  }

  checkNow(): Promise<boolean> {
    if (this.activeProbe) {
      return this.activeProbe;
    }

    this.snapshotState.update((current) => ({ ...current, state: 'checking' }));
    this.activeProbe = this.performProbe().finally(() => {
      this.activeProbe = null;
    });
    return this.activeProbe;
  }

  private async performProbe(): Promise<boolean> {
    try {
      await firstValueFrom(
        this.rawHttp.get('/healthz/user', { responseType: 'text' }).pipe(timeout(8_000)),
      );
      this.markAvailable();
      return true;
    } catch (error) {
      if (error instanceof HttpErrorResponse && error.status > 0) {
        if (error.status === 503) {
          this.markDegraded();
          return false;
        }
        if (error.status !== 502 && error.status !== 504) {
          // Authentication and application errors still prove that Janus
          // answered the probe; availability is not the operation result.
          this.markAvailable();
          return true;
        }
      }
      this.markUnreachable();
      return false;
    }
  }

  private update(state: BackendAvailabilityState, detail: string | null): void {
    const current = this.snapshotState();
    if (current.state === state && current.detail === detail) {
      return;
    }
    const previous = current.state;
    this.snapshotState.set({ state, checkedAt: new Date(), detail });
    if (previous !== state) {
      this.logger.info('[BackendAvailability] State changed.', { previous, state });
    }
  }
}
