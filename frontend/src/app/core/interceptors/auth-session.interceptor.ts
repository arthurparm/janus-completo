import { HttpContextToken, HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http'
import { inject } from '@angular/core'
import { Router } from '@angular/router'
import { catchError, from, switchMap, throwError } from 'rxjs'
import { AuthService } from '../auth/auth.service'
import { NotificationService } from '../notifications/notification.service'
import { getStoredAuthToken } from '../../services/auth.utils'

const SKIP_REFRESH = new HttpContextToken<boolean>(() => false)

export const authSessionInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService)
  const router = inject(Router)
  const notifications = inject(NotificationService)

  if (auth.isAuthRateLimited() && (req.headers.has('Authorization') || isAuthEndpoint(req.url))) {
    const remaining = auth.authRateLimitRemainingSeconds()
    const err = new HttpErrorResponse({
      url: req.url,
      status: 429,
      statusText: 'Too Many Requests',
      error: {
        title: 'Muitas requisições',
        detail: `Aguarde ${Math.max(1, remaining)} segundo(s) para tentar novamente.`
      }
    })
    return throwError(() => err)
  }

  return next(req).pipe(
    catchError((err) => {
      if (err instanceof HttpErrorResponse && err.status === 429) {
        auth.captureRateLimit(err, `${req.method}:${req.url}`)
      }

      if (
        err instanceof HttpErrorResponse &&
        err.status === 401 &&
        !req.context.get(SKIP_REFRESH) &&
        shouldAttemptRefresh(req.url)
      ) {
        if (auth.isVisitorSession()) {
          return throwError(() => err)
        }

        return from(auth.refreshAccessToken()).pipe(
          switchMap((ok) => {
            if (!ok) {
              const url = router.url || ''
              if (!url.startsWith('/login')) {
                notifications.notifyWarning(
                  'Sessão expirada',
                  'Sua sessão expirou. Faça login novamente para continuar.'
                )
                void router.navigate(['/login'], {
                  queryParams: { message: 'Sua sessão expirou. Faça login novamente para continuar.' },
                  replaceUrl: true
                })
              }
              return throwError(() => err)
            }

            const token = getStoredAuthToken()
            if (!token) return throwError(() => err)

            const retried = req.clone({
              setHeaders: { Authorization: `Bearer ${token}` },
              context: req.context.set(SKIP_REFRESH, true)
            })
            return next(retried)
          })
        )
      }

      return throwError(() => err)
    })
  )
}

function isAuthEndpoint(url: string): boolean {
  return url.includes('/v1/auth/local/')
}

function shouldAttemptRefresh(url: string): boolean {
  if (!url.includes('/v1/')) return false
  if (url.includes('/v1/auth/local/login')) return false
  if (url.includes('/v1/auth/local/register')) return false
  if (url.includes('/v1/auth/local/refresh')) return false
  if (url.includes('/v1/auth/local/request-reset')) return false
  if (url.includes('/v1/auth/local/reset')) return false
  return true
}
