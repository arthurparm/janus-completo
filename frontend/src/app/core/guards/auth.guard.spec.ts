import { ActivatedRouteSnapshot, Router } from '@angular/router'
import { TestBed } from '@angular/core/testing'
import { BehaviorSubject, firstValueFrom, Observable } from 'rxjs'
import { vi } from 'vitest'

import { AuthService, User } from '../auth/auth.service'
import { NotificationService } from '../notifications/notification.service'
import { AuthGuard, NoAuthGuard, RoleGuard } from './auth.guard'

describe('AuthGuard', () => {
  let guard: AuthGuard
  let authReady$: BehaviorSubject<boolean>
  let isAuthenticated$: BehaviorSubject<boolean>
  let routerNavigateSpy: ReturnType<typeof vi.fn>
  let notifyWarningSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    authReady$ = new BehaviorSubject<boolean>(false)
    isAuthenticated$ = new BehaviorSubject<boolean>(false)
    routerNavigateSpy = vi.fn()
    notifyWarningSpy = vi.fn()

    TestBed.configureTestingModule({
      providers: [
        AuthGuard,
        {
          provide: AuthService,
          useValue: {
            authReady$,
            isAuthenticated$
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
            notifyWarning: notifyWarningSpy
          }
        }
      ]
    })

    guard = TestBed.inject(AuthGuard)
  })

  it('redirects to login when auth is ready but user is not authenticated', async () => {
    const route = new ActivatedRouteSnapshot()
    const state = { url: '/private' }

    const resultPromise = firstValueFrom(
      guard.canActivate(route, state as never) as Observable<boolean>
    )

    isAuthenticated$.next(false)
    authReady$.next(true)

    const allowed = await resultPromise
    expect(allowed).toBe(false)
    expect(routerNavigateSpy).toHaveBeenCalledWith(
      ['/login'],
      expect.objectContaining({
        queryParams: { returnUrl: '/private' },
        replaceUrl: true
      })
    )
  })

  it('falls back when authReady does not resolve', async () => {
    vi.useFakeTimers()
    try {
      const route = new ActivatedRouteSnapshot()
      const state = { url: '/private' }

      const resultPromise = firstValueFrom(
        guard.canActivate(route, state as never) as Observable<boolean>
      )

      await vi.advanceTimersByTimeAsync(10000)

      const allowed = await resultPromise
      expect(allowed).toBe(false)
      expect(routerNavigateSpy).toHaveBeenCalledWith(
        ['/login'],
        expect.objectContaining({
          queryParams: { returnUrl: '/private' },
          replaceUrl: true
        })
      )
      expect(notifyWarningSpy).toHaveBeenCalledWith(
        'Autenticação indisponível',
        'Não foi possível inicializar a autenticação. Tente novamente.'
      )
    } finally {
      vi.useRealTimers()
    }
  })
})

describe('NoAuthGuard', () => {
  let guard: NoAuthGuard
  let authReady$: BehaviorSubject<boolean>
  let isAuthenticated$: BehaviorSubject<boolean>
  let routerNavigateSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    authReady$ = new BehaviorSubject<boolean>(false)
    isAuthenticated$ = new BehaviorSubject<boolean>(true)
    routerNavigateSpy = vi.fn()

    TestBed.configureTestingModule({
      providers: [
        NoAuthGuard,
        {
          provide: AuthService,
          useValue: {
            authReady$,
            isAuthenticated$
          }
        },
        {
          provide: Router,
          useValue: {
            navigate: routerNavigateSpy
          }
        }
      ]
    })

    guard = TestBed.inject(NoAuthGuard)
  })

  it('allows route when authReady does not resolve', async () => {
    vi.useFakeTimers()
    try {
      const resultPromise = firstValueFrom(guard.canActivate() as Observable<boolean>)

      await vi.advanceTimersByTimeAsync(10000)

      const allowed = await resultPromise
      expect(allowed).toBe(true)
      expect(routerNavigateSpy).not.toHaveBeenCalled()
    } finally {
      vi.useRealTimers()
    }
  })
})

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
