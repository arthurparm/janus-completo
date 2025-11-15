import {CanMatchFn, Router} from '@angular/router'
import {inject} from '@angular/core'
import {JanusApiService} from '../../services/janus-api.service'
import {AUTH_TOKEN_KEY} from '../../services/api.config'
import {decodeTokenUserId} from '../../services/auth.utils'
import {map, catchError, of} from 'rxjs'

export const hitlRoleGuard: CanMatchFn = (route, segments) => {
  const router = inject(Router)
  const api = inject(JanusApiService)
  let uid: number | null = null
  try {
    uid = decodeTokenUserId(localStorage.getItem(AUTH_TOKEN_KEY))
  } catch {
    uid = null
  }
  if (!uid) {
    return router.parseUrl('/login')
  }
  return api.getUserRoles(uid).pipe(
    map(res => {
      const roles = res.roles || []
      const allowed = roles.includes('REVISOR') || roles.includes('AUDITOR') || roles.includes('ADMIN')
      return allowed ? true : router.parseUrl('/')
    }),
    catchError(() => of(router.parseUrl('/login')))
  )
}