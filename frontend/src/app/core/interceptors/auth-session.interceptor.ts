import { HttpContextToken, HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http'
import { inject } from '@angular/core'
import { Router } from '@angular/router'
import { catchError, throwError } from 'rxjs'
import { AuthService } from '../auth/auth.service'
import { NotificationService } from '../notifications/notification.service'

export const SKIP_AUTH_SESSION = new HttpContextToken<boolean>(() => false)

export const authSessionInterceptor: HttpInterceptorFn = (req, next) => {
  if (req.context.get(SKIP_AUTH_SESSION)) return next(req)

  const auth = inject(AuthService)
  const router = inject(Router)
  const notifications = inject(NotificationService)

  return next(req).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        void auth.logout()
        const url = router.url || ''
        if (!url.startsWith('/login')) {
          notifications.notifyWarning(
            'SessÃ£o expirada',
            'Sua sessÃ£o expirou. Autentique-se novamente no provedor de identidade.'
          )
          void router.navigate(['/login'], {
            queryParams: { message: 'Sua sessÃ£o expirou. Autentique-se novamente.' },
            replaceUrl: true
          })
        }
      }
      return throwError(() => error)
    })
  )
}
