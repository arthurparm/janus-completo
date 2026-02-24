import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError, tap } from 'rxjs';
import { AppLoggerService } from '../services/app-logger.service';

/**
 * Log básico de erros HTTP sem alterar o fluxo.
 */
export const errorLoggerInterceptor: HttpInterceptorFn = (req, next) => {
  const logger = inject(AppLoggerService);
  return next(req).pipe(
    tap(() => {
      // noop; poderia adicionar métricas de sucesso aqui
    }),
    catchError((err) => {
      if (err instanceof HttpErrorResponse) {
        logger.warn('[HTTP ERROR]', {
          status: err.status,
          statusText: err.statusText,
          url: req.url,
          message: err.message,
        });
      }
      return throwError(() => err);
    })
  );
};
