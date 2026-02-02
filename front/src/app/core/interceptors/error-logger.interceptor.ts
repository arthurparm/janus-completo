import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { catchError, throwError, tap } from 'rxjs';

/**
 * Log básico de erros HTTP sem alterar o fluxo.
 */
export const errorLoggerInterceptor: HttpInterceptorFn = (req, next) => {
  return next(req).pipe(
    tap(() => {
      // noop; poderia adicionar métricas de sucesso aqui
    }),
    catchError((err) => {
      if (err instanceof HttpErrorResponse) {
        console.warn('[HTTP ERROR]', err.status, err.statusText, {
          url: req.url,
          message: err.message,
        });
      }
      return throwError(() => err);
    })
  );
};
