import { ActivatedRouteSnapshot, Router } from '@angular/router'
import { TestBed } from '@angular/core/testing'
import { BehaviorSubject, firstValueFrom, Observable } from 'rxjs'
import { vi } from 'vitest'

import { AuthService, User } from '../auth/auth.service'
import { NotificationService } from '../notifications/notification.service'
import { RoleGuard } from './auth.guard'

describe('RoleGuard', () => {
  let guard: RoleGuard
  let authReady$: BehaviorSubject<boolean>
  let user$: BehaviorSubject<User | null>
  let routerNavigateSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    authReady$ = new BehaviorSubject<boolean>(false)
    user$ = new BehaviorSubject<User | null>(null)
    routerNavigateSpy = vi.fn()

    TestBed.configureTestingModule({
      providers: [
        RoleGuard,
        {
          provide: AuthService,
          useValue: {
            authReady$,
            user$
          }
        },
        {
          provide: Router,
          useValue: {
            navigate: routerNavigateSpy
          }
        },
        {
          provide: NotificationService,
          useValue: {
            notifyError: vi.fn(),
            notifyWarning: vi.fn()
          }
        }
      ]
    })

    guard = TestBed.inject(RoleGuard)
  })

  it('waits authReady before validating admin role', async () => {
    const route = new ActivatedRouteSnapshot()
    route.data = { roles: ['admin'] }

    const resultPromise = firstValueFrom(guard.canActivate(route) as Observable<boolean>)
    user$.next({
      id: '1',
      roles: ['admin']
    })
    authReady$.next(true)

    const allowed = await resultPromise
    expect(allowed).toBe(true)
    expect(routerNavigateSpy).not.toHaveBeenCalled()
  })

  it('redirects to login when auth is ready but user is missing', async () => {
    const route = new ActivatedRouteSnapshot()
    route.data = { roles: ['admin'] }
    authReady$.next(true)
    user$.next(null)

    const allowed = await firstValueFrom(guard.canActivate(route) as Observable<boolean>)
    expect(allowed).toBe(false)
    expect(routerNavigateSpy).toHaveBeenCalledWith(['/login'])
  })
})
