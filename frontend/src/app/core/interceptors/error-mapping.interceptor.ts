import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';
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

export const errorMappingInterceptor: HttpInterceptorFn = (req, next) => {
  const notifications = inject(NotificationService);
  const demoService = inject(DemoService);

  return next(req).pipe(
    catchError((err) => {
      // Check for connection refusal / offline status / Proxy errors (500/502/503/504)
      const isConnectionError = err.status === 0 || err.status === 504 || err.status === 502 || err.status === 503 || err.status === 500;

      if (isConnectionError) {
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