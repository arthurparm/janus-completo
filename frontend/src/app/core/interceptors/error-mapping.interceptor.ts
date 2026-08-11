import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError, tap, throwError } from 'rxjs';
import { inject } from '@angular/core';
import { NotificationService } from '../notifications/notification.service';
import { DemoService } from '../services/demo.service';

function extractProblemDetails(err: HttpErrorResponse): { title: string; detail: string } {
  const body = err.error;
  if (body && typeof body === 'object') {
    const title = (body.title as string) || `Erro HTTP ${err.status}`;
    const detail = (body.detail as string) || err.message;
    return { title, detail };
  }
  // network/offline or non-JSON
  if (err.status === 0) {
    return { title: 'Falha de rede', detail: 'Não foi possível conectar ao servidor. Verifique sua conexão ou tente novamente.' };
  }
  return { title: `Erro HTTP ${err.status}`, detail: err.message };
}

function isJanusBackendRequest(url: string): boolean {
  return url.startsWith('/api/') || url.startsWith('/public-api/') || url.startsWith('/healthz');
}

export const errorMappingInterceptor: HttpInterceptorFn = (req, next) => {
  const notifications = inject(NotificationService);
  const demoService = inject(DemoService);
  const targetsJanusBackend = isJanusBackendRequest(req.url);

  return next(req).pipe(
    tap(() => {
      // A successful response proves that the local backend is reachable again.
      // This prevents a transient startup/proxy failure from latching the banner.
      if (targetsJanusBackend) {
        demoService.resetMode();
      }
    }),
    catchError((err) => {
      // A backend 500 is an operation failure, not proof that the backend is
      // disconnected. Reserve offline mode for transport and gateway failures.
      const isConnectionError = err.status === 0 || err.status === 504 || err.status === 502 || err.status === 503;

      if (isConnectionError && targetsJanusBackend) {
        // Suppress notification for connection/server errors
        // Enable offline mode silently
        demoService.enableOfflineMode();
        return throwError(() => err);
      }

      if (err instanceof HttpErrorResponse) {
        // If we are in offline mode, strictly suppress ALL global error toasts
        if (demoService.isOffline()) {
          return throwError(() => err);
        }

        const { title, detail } = extractProblemDetails(err);
        notifications.notify({ type: 'error', message: title, detail });
      }
      return throwError(() => err);
    })
  );
};
