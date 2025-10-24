import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';
import { inject } from '@angular/core';
import { NotificationService } from '../notifications/notification.service';

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
  return next(req).pipe(
    catchError((err) => {
      if (err instanceof HttpErrorResponse) {
        const { title, detail } = extractProblemDetails(err);
        notifications.notify({ type: 'error', message: title, detail });
      }
      return throwError(() => err);
    })
  );
};