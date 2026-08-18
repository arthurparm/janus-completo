import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError, tap, throwError } from 'rxjs';
import { inject } from '@angular/core';
import { NotificationService } from '../notifications/notification.service';
import { BackendAvailabilityService } from '../services/backend-availability.service';
import { API_BASE_URL, PUBLIC_API_BASE_URL } from '../../services/api.config';

function extractProblemDetails(err: HttpErrorResponse): { title: string; detail: string } {
  const body = err.error;
  if (body && typeof body === 'object') {
    const title = (body.title as string) || `Erro HTTP ${err.status}`;
    const detail = (body.detail as string) || err.message;
    return { title, detail };
  }
  // network/offline or non-JSON
  if (err.status === 0) {
    return {
      title: 'Falha de rede',
      detail: 'Não foi possível conectar ao servidor. Verifique sua conexão ou tente novamente.',
    };
  }
  return { title: `Erro HTTP ${err.status}`, detail: err.message };
}

function isJanusBackendRequest(url: string): boolean {
  try {
    const isAbsolute = /^https?:\/\//i.test(url);
    const parsed = new URL(url, 'http://janus.local');
    const hasBackendPath =
      parsed.pathname.startsWith('/api/') ||
      parsed.pathname.startsWith('/public-api/') ||
      parsed.pathname.startsWith('/healthz');
    if (!hasBackendPath || !isAbsolute) {
      return hasBackendPath;
    }

    const configuredOrigins = [API_BASE_URL, PUBLIC_API_BASE_URL]
      .filter((base) => /^https?:\/\//i.test(base))
      .map((base) => new URL(base).origin);
    const browserOrigin = globalThis.location?.origin;
    return parsed.origin === browserOrigin || configuredOrigins.includes(parsed.origin);
  } catch {
    return false;
  }
}

export const errorMappingInterceptor: HttpInterceptorFn = (req, next) => {
  const notifications = inject(NotificationService);
  const backendAvailability = inject(BackendAvailabilityService);
  const targetsJanusBackend = isJanusBackendRequest(req.url);

  return next(req).pipe(
    tap(() => {
      // A successful response proves that the local backend is reachable again.
      // This prevents a transient startup/proxy failure from latching the banner.
      if (targetsJanusBackend) {
        backendAvailability.markAvailable();
      }
    }),
    catchError((err) => {
      // A backend 500 is an operation failure, not proof that the backend is
      // disconnected. Reserve unreachable state for transport and gateway failures.
      const isConnectionError = err.status === 0 || err.status === 504 || err.status === 502;

      if (isConnectionError && targetsJanusBackend) {
        backendAvailability.markUnreachable();
        return throwError(() => err);
      }

      if (err instanceof HttpErrorResponse) {
        if (targetsJanusBackend) {
          if (err.status === 503) {
            backendAvailability.markDegraded();
          } else if (err.status > 0) {
            // Even an application error proves the backend answered.
            backendAvailability.markAvailable();
          }
        }

        const { title, detail } = extractProblemDetails(err);
        notifications.notify({ type: 'error', message: title, detail });
      }
      return throwError(() => err);
    }),
  );
};
