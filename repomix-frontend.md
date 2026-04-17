This file is a merged representation of a subset of the codebase, containing files not matching ignore patterns, combined into a single document by Repomix.

<file_summary>
This section contains a summary of this file.

<purpose>
This file contains a packed representation of a subset of the repository's contents that is considered the most important context.
It is designed to be easily consumable by AI systems for analysis, code review,
or other automated processes.
</purpose>

<file_format>
The content is organized as follows:
1. This summary section
2. Repository information
3. Directory structure
4. Repository files (if enabled)
5. Multiple file entries, each consisting of:
  - File path as an attribute
  - Full contents of the file
</file_format>

<usage_guidelines>
- This file should be treated as read-only. Any changes should be made to the
  original repository files, not this packed version.
- When processing this file, use the file path to distinguish
  between different files in the repository.
- Be aware that this file may contain sensitive information. Handle it with
  the same level of security as you would the original repository.
</usage_guidelines>

<notes>
- Some files may have been excluded based on .gitignore rules and Repomix's configuration
- Binary files are not included in this packed representation. Please refer to the Repository Structure section for a complete list of file paths, including binary files
- Files matching these patterns are excluded: **/node_modules/**, **/assets/**
- Files matching patterns in .gitignore are excluded
- Files matching default ignore patterns are excluded
- Files are sorted by Git change count (files with more changes are at the bottom)
</notes>

</file_summary>

<directory_structure>
app/
  core/
    auth/
      auth.service.spec.ts
      auth.service.ts
    guards/
      auth.guard.spec.ts
      auth.guard.ts
      index.ts
    interceptors/
      auth.interceptor.ts
      base-url.interceptor.ts
      error-logger.interceptor.ts
      error-mapping.interceptor.ts
      http.interceptor.ts
    layout/
      header/
        header.html
        header.scss
        header.spec.ts
        header.ts
      sidebar/
        sidebar.html
        sidebar.scss
        sidebar.spec.ts
        sidebar.ts
    notifications/
      notification.service.ts
    resolvers/
      app.resolver.ts
    services/
      agent-events.service.ts
      app-logger.service.ts
      demo.service.ts
      loading-state.service.spec.ts
      loading-state.service.ts
      system-status.service.ts
      system-status.spec.ts
      tailscale.service.ts
    state/
      global-state.store.ts
    types/
      angular.types.ts
      index.ts
      janus-gateway.types.ts
      speech.types.ts
    core-module.ts
    core-routing-module.ts
    README.md
  features/
    admin/
      autonomia/
        admin-autonomia.html
        admin-autonomia.scss
        admin-autonomia.ts
    auth/
      login/
        login.a11y.spec.ts
        login.html
        login.scss
        login.spec.ts
        login.ts
      register/
        register.html
        register.scss
        register.ts
    conversations/
      admin-code-qa.util.spec.ts
      admin-code-qa.util.ts
      conversations.html
      conversations.scss
      conversations.spec.ts
      conversations.ts
    home/
      widgets/
        autonomy-widget/
          autonomy-widget.html
          autonomy-widget.scss
          autonomy-widget.spec.ts
          autonomy-widget.ts
        knowledge-widget/
          knowledge-widget.html
          knowledge-widget.scss
          knowledge-widget.spec.ts
          knowledge-widget.ts
        learning-widget/
          learning-widget.html
          learning-widget.scss
          learning-widget.spec.ts
          learning-widget.ts
      home.html
      home.scss
      home.ts
    observability/
      widgets/
        database-health-widget/
          database-health-widget.html
          database-health-widget.scss
          database-health-widget.ts
        knowledge-health-widget/
          knowledge-health-widget.html
          knowledge-health-widget.scss
          knowledge-health-widget.ts
        system-status-widget/
          system-status-widget.html
          system-status-widget.scss
          system-status-widget.ts
      observability.html
      observability.scss
      observability.ts
    tools/
      tools.html
      tools.scss
      tools.ts
  models/
    autonomy.models.ts
    chat.models.ts
    core.models.ts
    index.ts
    knowledge.models.ts
    llm.models.ts
    memory.models.ts
    observability.models.ts
    productivity.models.ts
    system.models.ts
    tools.models.ts
  services/
    domain/
      autonomy-api-service.ts
      chat-api-service.ts
      context-api-service.ts
      documents-api-service.ts
      experiment-api-service.ts
      feedback-api-service.ts
      graph-api-service.ts
      knowledge-api-service.ts
      llm-api-service.ts
      memory-api-service.ts
      observability-api-service.ts
      productivity-api-service.ts
      system-api-service.ts
      tools-api-service.ts
      users-api-service.ts
      web-rtcapi-service.ts
    api-context.service.ts
    api.config.ts
    api.service.ts
    auth.utils.ts
    auto-analysis.service.ts
    backend-api.service.ts
    chat-auth-headers.util.spec.ts
    chat-auth-headers.util.ts
    chat-stream.service.ts
    conversation-refresh.service.ts
    graph-api.service.ts
    mock-auto-analysis.service.ts
    response-time-estimator.service.ts
    ux-metrics.service.ts
  shared/
    components/
      confirm-dialog/
        confirm-dialog.component.ts
      jarvis-avatar/
        jarvis-avatar.component.ts
      loading/
        loading.component.spec.ts
        loading.component.ts
      loading-dialog/
        loading-dialog.component.ts
      message-content/
        message-content.component.html
      skeleton/
        skeleton.component.spec.ts
        skeleton.component.ts
      ui/
        button/
          button.component.ts
        dialog/
          dialog-container.component.ts
          dialog-ref.ts
          dialog.service.ts
          dialog.tokens.ts
        icon/
          icon.component.ts
        spinner/
          spinner.component.ts
        system-hud/
          system-hud.html
          system-hud.scss
          system-hud.spec.ts
          system-hud.ts
        toast/
          toast.component.ts
          toast.service.ts
          toast.types.ts
          toaster.component.ts
        ui-badge/
          ui-badge.component.html
          ui-badge.component.scss
          ui-badge.component.ts
        ui-button/
          ui-button.directive.ts
        ui-card/
          ui-card.component.html
          ui-card.component.scss
          ui-card.component.ts
        ui-table/
          ui-table.component.html
          ui-table.component.scss
          ui-table.component.ts
        index.ts
    icons/
      icons.module.ts
    pipes/
      markdown.pipe.ts
    services/
      markdown.service.spec.ts
      markdown.service.ts
      ui.service.ts
    _index.scss
    icon.component.ts
    icons.ts
    README.md
    shared.module.ts
  app.config.ts
  app.html
  app.routes.ts
  app.scss
  app.spec.ts
  app.ts
environments/
  environment.prod.ts
  environment.ts
styles/
  _animations.scss
  _components.scss
  _markdown.scss
  _mixins.scss
  _tokens.scss
  _utilities.scss
env.d.ts
index.html
main.ts
styles.scss
tailwind-styles.scss
test-setup.ts
</directory_structure>

<files>
This section contains the contents of the repository's files.

<file path="app/core/auth/auth.service.spec.ts">
import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'
import { AuthService } from './auth.service'
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../../services/api.config'

describe('AuthService', () => {
  let http: HttpTestingController
  const meEndpoint = `${API_BASE_URL}/v1/auth/local/me`

  const waitForAuthReady = async (svc: AuthService, maxTicks = 8): Promise<void> => {
    for (let i = 0; i < maxTicks; i += 1) {
      if (svc.authReady()) return
      await Promise.resolve()
    }
  }

  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
    })
    http = TestBed.inject(HttpTestingController)
  })

  afterEach(() => {
    http.verify()
    localStorage.clear()
    sessionStorage.clear()
  })

  it('deve fazer login com remember=true e salvar token no localStorage', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.loginWithPassword('a@b.com', '123456', true)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    expect(req.request.method).toBe('POST')
    expect(req.request.body).toEqual({ email: 'a@b.com', password: '123456' })
    req.flush({ token: 'janus.jwt', user: { id: 'uid-123', email: 'a@b.com', roles: ['user'] } })

    const result = await promise
    expect(result.ok).toBe(true)
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('janus.jwt')
    expect(sessionStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
  })

  it('deve fazer login com remember=false e salvar token no sessionStorage', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.loginWithPassword('a@b.com', '123456', false)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    req.flush({ token: 'janus.jwt', user: { id: 'uid-123', email: 'a@b.com', roles: ['user'] } })

    const result = await promise
    expect(result.ok).toBe(true)
    expect(sessionStorage.getItem(AUTH_TOKEN_KEY)).toBe('janus.jwt')
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
  })

  it('deve retornar erro mapeado para 401', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.loginWithPassword('a@b.com', '123456', true)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    req.flush({ detail: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' })

    const result = await promise
    expect(result.ok).toBe(false)
    expect(result.statusCode).toBe(401)
    expect(result.reason).toBe('invalid_credentials')
  })

  it('deve retornar erro mapeado para 422', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.loginWithPassword('bad-email', '123456', true)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    req.flush({ detail: 'validation error' }, { status: 422, statusText: 'Unprocessable Content' })

    const result = await promise
    expect(result.ok).toBe(false)
    expect(result.statusCode).toBe(422)
    expect(result.reason).toBe('invalid_request')
  })

  it('deve mapear 401 com orientacao para recuperar acesso', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.loginWithPassword('a@b.com', '12345678', true)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    req.flush({ detail: 'Invalid credentials' }, { status: 401, statusText: 'Unauthorized' })

    const result = await promise
    expect(result.ok).toBe(false)
    expect(result.error).toContain('Recuperar acesso')
  })

  it('deve mapear 422 com erro de senha minima', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.loginWithPassword('a@b.com', '123', true)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/login`)
    req.flush(
      { detail: [{ msg: 'String should have at least 8 characters', loc: ['body', 'password'] }] },
      { status: 422, statusText: 'Unprocessable Content' }
    )

    const result = await promise
    expect(result.ok).toBe(false)
    expect(result.error).toContain('minimo 8')
  })

  it('deve mapear reset com token invalido', async () => {
    const svc = TestBed.inject(AuthService)
    const promise = svc.resetPassword('invalid', 'NovaSenha@123')
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/local/reset`)
    req.flush({ detail: 'Invalid token' }, { status: 400, statusText: 'Bad Request' })

    const result = await promise
    expect(result.ok).toBe(false)
    expect(result.error).toContain('Token invalido ou expirado')
  })

  it('deve restaurar sessao quando existir token local', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'persisted.jwt')

    const svc = TestBed.inject(AuthService)
    const req = http.expectOne(meEndpoint)
    expect(req.request.method).toBe('GET')
    req.flush({ id: 'uid-123', email: 'a@b.com', roles: ['user'] })

    await waitForAuthReady(svc)
    expect(svc.isAuthenticated()).toBe(true)
    expect(svc.currentUserValue?.email).toBe('a@b.com')
    expect(svc.authReady()).toBe(true)
  })

  it('deve restaurar sessao quando existir token na sessionStorage', async () => {
    sessionStorage.setItem(AUTH_TOKEN_KEY, 'persisted.jwt')

    const svc = TestBed.inject(AuthService)
    const req = http.expectOne(meEndpoint)
    expect(req.request.method).toBe('GET')
    req.flush({ id: 'uid-123', email: 'a@b.com', roles: ['user'] })

    await waitForAuthReady(svc)
    expect(svc.isAuthenticated()).toBe(true)
    expect(svc.currentUserValue?.email).toBe('a@b.com')
    expect(svc.authReady()).toBe(true)
  })

  it('deve concluir inicializacao sem chamar /me quando nao houver token persistido', async () => {
    const svc = TestBed.inject(AuthService)

    http.expectNone(meEndpoint)
    await waitForAuthReady(svc)

    expect(svc.isAuthenticated()).toBe(false)
    expect(svc.currentUserValue).toBeNull()
    expect(svc.authReady()).toBe(true)
  })

  it('deve limpar sessao persistida quando restauracao via /me falhar', async () => {
    localStorage.setItem(AUTH_TOKEN_KEY, 'persisted.jwt')
    sessionStorage.setItem(AUTH_TOKEN_KEY, 'persisted.jwt')

    const svc = TestBed.inject(AuthService)
    const req = http.expectOne(meEndpoint)
    expect(req.request.method).toBe('GET')
    req.flush({ detail: 'Unauthorized' }, { status: 401, statusText: 'Unauthorized' })

    await waitForAuthReady(svc)

    expect(svc.isAuthenticated()).toBe(false)
    expect(svc.currentUserValue).toBeNull()
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
    expect(sessionStorage.getItem(AUTH_TOKEN_KEY)).toBeNull()
    expect(svc.authReady()).toBe(true)
  })
})
</file>

<file path="app/core/auth/auth.service.ts">
import { Injectable, inject, signal, computed } from '@angular/core'
import { HttpClient, HttpErrorResponse } from '@angular/common/http'
import { API_BASE_URL, VISITOR_MODE_KEY } from '../../services/api.config'
import { firstValueFrom } from 'rxjs'
import { toObservable } from '@angular/core/rxjs-interop'
import { AppLoggerService } from '../services/app-logger.service'
import { clearStoredAuthToken, getStoredAuthToken, storeAuthToken } from '../../services/auth.utils'

export interface User {
  id: string
  email?: string
  username?: string
  display_name?: string
  roles?: string[]
  permissions?: string[]
  [key: string]: unknown
}

export interface LocalAuthResponse {
  token: string
  user: User
}

export interface AuthActionResult {
  ok: boolean
  error?: string
}

export interface LoginResult extends AuthActionResult {
  statusCode?: number
  reason?: 'invalid_credentials' | 'invalid_request' | 'rate_limited' | 'unknown'
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly _isAuthenticated = signal<boolean>(false)
  private readonly _user = signal<User | null>(null)
  private readonly _firebaseAuthReady = signal<boolean>(false)
  private readonly _authReady = signal<boolean>(false)

  readonly isAuthenticated = this._isAuthenticated.asReadonly()
  readonly user = this._user.asReadonly()
  readonly firebaseAuthReady = this._firebaseAuthReady.asReadonly()
  readonly authReady = this._authReady.asReadonly()

  readonly isAuthenticated$ = toObservable(this._isAuthenticated)
  readonly user$ = toObservable(this._user)
  readonly firebaseAuthReady$ = toObservable(this._firebaseAuthReady)
  readonly authReady$ = toObservable(this._authReady)

  readonly isAdmin = computed(() => this._user()?.roles?.includes('admin') ?? false)
  readonly userEmail = computed(() => this._user()?.email ?? '')

  get currentUserValue(): User | null {
    return this._user()
  }

  private http = inject(HttpClient)
  private logger = inject(AppLoggerService)

  constructor() {
    this.initializeAuth()
  }

  private async initializeAuth(): Promise<void> {
    this._authReady.set(false)
    this._firebaseAuthReady.set(true)

    const token = getStoredAuthToken()
    if (token) {
      try {
        const user = await firstValueFrom(
          this.http.get<User>(`${API_BASE_URL}/v1/auth/local/me`)
        )
        this._isAuthenticated.set(true)
        this._user.set(user)
      } catch {
        this.clearSession()
      }
    } else {
      this._isAuthenticated.set(false)
      this._user.set(null)
    }

    this._authReady.set(true)
  }

  async loginWithPassword(email: string, password: string, remember: boolean): Promise<LoginResult> {
    try {
      const out = await firstValueFrom(
        this.http.post<LocalAuthResponse>(`${API_BASE_URL}/v1/auth/local/login`, {
          email,
          password
        })
      )
      const token = String(out?.token || '')
      if (token) {
        storeAuthToken(token, remember)
        localStorage.removeItem(VISITOR_MODE_KEY)
        this._isAuthenticated.set(true)
        this._user.set(out.user)
        return { ok: true }
      }
      return { ok: false, error: 'Falha no login. Tente novamente.' }
    } catch (err) {
      return this.extractLoginError(err)
    }
  }

  async loginWithProvider(provider: 'google' | 'github'): Promise<boolean> {
    this.logger.warn('Login via provider not supported in local auth mode', { provider })
    return false
  }

  async registerLocal(payload: {
    username: string
    fullName: string
    cpf?: string
    phone?: string
    email: string
    password: string
    terms: boolean
  }): Promise<AuthActionResult> {
    try {
      const out = await firstValueFrom(
        this.http.post<LocalAuthResponse>(`${API_BASE_URL}/v1/auth/local/register`, {
          username: payload.username,
          full_name: payload.fullName,
          cpf: payload.cpf,
          phone: payload.phone,
          email: payload.email,
          password: payload.password,
          terms: payload.terms
        })
      )
      const token = String(out?.token || '')
      if (token) {
        storeAuthToken(token, true)
        localStorage.removeItem(VISITOR_MODE_KEY)
        this._isAuthenticated.set(true)
        this._user.set(out.user)
        return { ok: true }
      }
      return { ok: false, error: 'Falha ao registrar. Verifique seus dados.' }
    } catch (err) {
      return { ok: false, error: this.extractErrorDetail(err) }
    }
  }

  async requestPasswordReset(email: string): Promise<string | null> {
    try {
      const out = await firstValueFrom(
        this.http.post<{ status: string; reset_token?: string | null }>(
          `${API_BASE_URL}/v1/auth/local/request-reset`,
          { email }
        )
      )
      return out?.reset_token ?? null
    } catch {
      return null
    }
  }

  async resetPassword(token: string, password: string): Promise<AuthActionResult> {
    try {
      const out = await firstValueFrom(
        this.http.post<{ status: string }>(`${API_BASE_URL}/v1/auth/local/reset`, {
          token,
          password
        })
      )
      return out?.status === 'ok'
        ? { ok: true }
        : { ok: false, error: 'Nao foi possivel redefinir a senha. Tente novamente.' }
    } catch (err) {
      if (err instanceof HttpErrorResponse) {
        if (err.status === 400) {
          return { ok: false, error: 'Token invalido ou expirado. Solicite um novo link de recuperacao.' }
        }
        if (err.status === 422) {
          return { ok: false, error: 'A nova senha precisa ter no minimo 8 caracteres.' }
        }
      }
      return { ok: false, error: 'Falha ao redefinir senha. Tente novamente.' }
    }
  }

  private clearSession() {
    clearStoredAuthToken()
    localStorage.removeItem(VISITOR_MODE_KEY)
    this._isAuthenticated.set(false)
    this._user.set(null)
  }

  async logout(): Promise<void> {
    this.clearSession()
  }

  private extractErrorDetail(err: unknown): string {
    if (err instanceof HttpErrorResponse) {
      const body = err.error
      if (body && typeof body === 'object') {
        const detail = (body as { detail?: unknown }).detail
        if (typeof detail === 'string' && detail.trim()) return detail.trim()
        const message = (body as { message?: unknown }).message
        if (typeof message === 'string' && message.trim()) return message.trim()
      }
      if (typeof body === 'string' && body.trim()) return body.trim()
    }
    return 'Falha ao registrar. Verifique seus dados.'
  }

  private extractLoginError(err: unknown): LoginResult {
    if (err instanceof HttpErrorResponse) {
      if (err.status === 401) {
        const detail = this.readErrorDetail(err)
        const invalidCredentials = detail.includes('invalid credentials')
        return {
          ok: false,
          statusCode: 401,
          reason: 'invalid_credentials',
          error: invalidCredentials
            ? 'Email/usuario ou senha invalidos. Verifique os dados ou use "Recuperar acesso".'
            : 'Sessao nao autorizada. Faca login novamente.'
        }
      }
      if (err.status === 422) {
        const detail = this.readErrorDetail(err)
        const passwordMinLen = detail.includes('least 8') || detail.includes('min_length')
        const emailInvalid = detail.includes('email')
        return {
          ok: false,
          statusCode: 422,
          reason: 'invalid_request',
          error: passwordMinLen
            ? 'Senha invalida: use no minimo 8 caracteres.'
            : emailInvalid
              ? 'Email invalido. Revise o formato e tente novamente.'
              : 'Dados de login invalidos. Revise email e senha e tente novamente.'
        }
      }
      if (err.status === 429) {
        return {
          ok: false,
          statusCode: 429,
          reason: 'rate_limited',
          error: 'Muitas tentativas. Aguarde 1 minuto e tente novamente.'
        }
      }
      return {
        ok: false,
        statusCode: err.status,
        reason: 'unknown',
        error: 'Falha no login. Tente novamente.'
      }
    }
    return { ok: false, reason: 'unknown', error: 'Falha no login. Tente novamente.' }
  }

  private readErrorDetail(err: HttpErrorResponse): string {
    const body = err.error
    if (body && typeof body === 'object') {
      const detail = (body as { detail?: unknown }).detail
      if (typeof detail === 'string') return detail.toLowerCase()
      if (Array.isArray(detail)) {
        return detail
          .map(item => {
            if (item && typeof item === 'object') {
              return String((item as { msg?: unknown }).msg ?? '')
            }
            return String(item ?? '')
          })
          .join(' ')
          .toLowerCase()
      }
      const message = (body as { message?: unknown }).message
      if (typeof message === 'string') return message.toLowerCase()
    }
    if (typeof body === 'string') return body.toLowerCase()
    return ''
  }
}
</file>

<file path="app/core/guards/auth.guard.spec.ts">
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
</file>

<file path="app/core/guards/auth.guard.ts">
/**
 * Guards de autenticação e autorização para rotas Angular
 * Implementa proteção de rotas baseada em autenticação e permissões
 */

import { Injectable, inject } from '@angular/core';
import { CanActivate, CanActivateChild, CanLoad, Router, ActivatedRouteSnapshot, RouterStateSnapshot, Route, UrlSegment } from '@angular/router';
import { Observable, combineLatest, filter, map, take } from 'rxjs';
import { AuthService } from '../auth/auth.service';
import { NotificationService } from '../notifications/notification.service';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard implements CanActivate, CanActivateChild, CanLoad {
  private authService = inject(AuthService);
  private router = inject(Router);
  private notificationService = inject(NotificationService);

  canActivate(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean> | Promise<boolean> | boolean {
    return this.checkAuth(route, state);
  }

  canActivateChild(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<boolean> | Promise<boolean> | boolean {
    return this.canActivate(route, state);
  }

  canLoad(
    _route: Route,
    _segments: UrlSegment[]
  ): Observable<boolean> | Promise<boolean> | boolean {
    return this.checkAuthForLoad();
  }

  private checkAuth(route?: ActivatedRouteSnapshot, state?: RouterStateSnapshot): Observable<boolean> {
    return combineLatest([this.authService.authReady$, this.authService.isAuthenticated$]).pipe(
      filter(([ready]) => ready),
      take(1),
      map(([, isAuthenticated]) => {
        if (isAuthenticated) {
          return true;
        }

        // Redirecionar para login com URL de retorno
        const returnUrl = state?.url || route?.url?.join('/') || '/';
        this.router.navigate(['/login'], {
          queryParams: { returnUrl },
          replaceUrl: true
        });

        this.notificationService.notifyWarning('Acesso negado', 'Por favor, faça login para acessar esta página');
        return false;
      })
    );
  }

  private checkAuthForLoad(): Observable<boolean> {
    return combineLatest([this.authService.authReady$, this.authService.isAuthenticated$]).pipe(
      filter(([ready]) => ready),
      take(1),
      map(([, isAuthenticated]) => {
        if (!isAuthenticated) {
          this.notificationService.notifyWarning('Acesso negado', 'Por favor, faça login para acessar este módulo');
        }
        return isAuthenticated;
      })
    );
  }
}

@Injectable({
  providedIn: 'root'
})
export class RoleGuard implements CanActivate {
  private authService = inject(AuthService);
  private router = inject(Router);
  private notificationService = inject(NotificationService);

  canActivate(route: ActivatedRouteSnapshot): Observable<boolean> | Promise<boolean> | boolean {
    const requiredRoles = route.data['roles'] as string[];

    if (!requiredRoles || requiredRoles.length === 0) {
      return true;
    }

    return combineLatest([this.authService.authReady$, this.authService.user$]).pipe(
      filter(([ready]) => ready),
      take(1),
      map(([, user]) => {
        if (!user) {
          this.router.navigate(['/login']);
          return false;
        }

        const hasRole = requiredRoles.some(role => user.roles?.includes(role) || false);

        if (!hasRole) {
          this.notificationService.notifyError('Acesso negado', 'Você não tem permissão para acessar esta página');
          this.router.navigate(['/']);
          return false;
        }

        return true;
      })
    );
  }
}

@Injectable({
  providedIn: 'root'
})
export class PermissionGuard implements CanActivate {
  private authService = inject(AuthService);
  private router = inject(Router);
  private notificationService = inject(NotificationService);

  canActivate(route: ActivatedRouteSnapshot): Observable<boolean> | Promise<boolean> | boolean {
    const requiredPermissions = route.data['permissions'] as string[];

    if (!requiredPermissions || requiredPermissions.length === 0) {
      return true;
    }

    return this.authService.user$.pipe(
      take(1),
      map(user => {
        if (!user) {
          this.router.navigate(['/login']);
          return false;
        }

        const hasPermission = requiredPermissions.every(permission =>
          user.permissions?.includes(permission) || false
        );

        if (!hasPermission) {
          this.notificationService.notifyError('Acesso negado', 'Você não tem as permissões necessárias para acessar esta página');
          this.router.navigate(['/']);
          return false;
        }

        return true;
      })
    );
  }
}

@Injectable({
  providedIn: 'root'
})
export class NoAuthGuard implements CanActivate {
  private authService = inject(AuthService);
  private router = inject(Router);

  canActivate(): Observable<boolean> | Promise<boolean> | boolean {
    return combineLatest([this.authService.authReady$, this.authService.isAuthenticated$]).pipe(
      filter(([ready]) => ready),
      take(1),
      map(([, isAuthenticated]) => {
        if (!isAuthenticated) {
          return true;
        }

        // Se já está autenticado, redirecionar para dashboard
        this.router.navigate(['/']);
        return false;
      })
    );
  }
}

/**
 * Guard para verificar se o sistema está pronto
 * Útil para verificar configurações iniciais, conexões, etc.
 */
@Injectable({
  providedIn: 'root'
})
export class SystemReadyGuard implements CanActivate {
  private authService = inject(AuthService);
  private router = inject(Router);
  private notificationService = inject(NotificationService);

  canActivate(): Observable<boolean> | Promise<boolean> | boolean {
    // Verificar se o sistema está configurado e pronto
    return this.checkSystemReadiness().pipe(
      map(isReady => {
        if (!isReady) {
          this.notificationService.notifyWarning('Sistema não pronto', 'O sistema ainda está sendo configurado. Por favor, aguarde.');
          this.router.navigate(['/setup']);
          return false;
        }
        return true;
      })
    );
  }

  private checkSystemReadiness(): Observable<boolean> {
    // Implementar lógica de verificação do sistema
    // Por exemplo: verificar configurações, conexões, etc.
    return this.authService.isAuthenticated$;
  }
}
</file>

<file path="app/core/guards/index.ts">
/**
 * Index de exportação para guards e resolvers
 */

// Guards
export * from './auth.guard';

// Resolvers
export * from '../resolvers/app.resolver';
</file>

<file path="app/core/interceptors/auth.interceptor.ts">
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { decodeTokenUserId, getStoredAuthToken } from '../../services/auth.utils';
import { AppLoggerService } from '../services/app-logger.service';

/**
 * Opcionalmente anexa Authorization: Bearer <token> quando disponível.
 * - Lê token de localStorage/sessionStorage
 * - Não sobrescreve cabeçalhos Authorization existentes
 * - Não impõe credenciais; requests anônimas continuam funcionando
 */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const logger = inject(AppLoggerService);
  try {
    const token = getStoredAuthToken();
    const setHeaders: Record<string, string> = {};

    if (!req.headers.has('Authorization') && token) {
      setHeaders['Authorization'] = `Bearer ${token}`;
    }

    if (!req.headers.has('X-User-Id') && token) {
      const uid = decodeTokenUserId(token);
      if (uid !== null) {
        setHeaders['X-User-Id'] = String(uid);
      }
    }

    // Debug: Log requests to chat history
    if (req.url.includes('/api/v1/chat/') && req.url.includes('/history')) {
      logger.debug('[AuthInterceptor] Chat history request', {
        url: req.url,
        hasAuthHeader: req.headers.has('Authorization'),
        hasUserIdHeader: req.headers.has('X-User-Id'),
        headers: req.headers.keys(),
        method: req.method
      });
    }

    if (Object.keys(setHeaders).length > 0) {
      const cloned = req.clone({ setHeaders });
      return next(cloned);
    }

    return next(req);
  } catch {
    return next(req);
  }
};
</file>

<file path="app/core/interceptors/base-url.interceptor.ts">
import { HttpInterceptorFn } from '@angular/common/http';
import { API_BASE_URL } from '../../services/api.config';

/**
 * Prepend API_BASE_URL to relative requests.
 * - Skips absolute URLs (http/https)
 * - Avoids double-prepending when path already starts with API_BASE_URL
 * - Skips well-known root health endpoints (`/healthz`, `/readyz`)
 */
export const baseUrlInterceptor: HttpInterceptorFn = (req, next) => {
  const isAbsolute = /^https?:\/\//i.test(req.url);
  let url = req.url;

  if (!isAbsolute) {
    const normalizedBase = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
    const normalizedUrl = url.startsWith('/') ? url : `/${url}`;

    const skipExact = ['/healthz', '/readyz', '/favicon.ico'];
    const skipPrefix = ['/assets/'];
    const skipExt = ['.csv'];
    const hasSkipExt = skipExt.some(ext => normalizedUrl.toLowerCase().endsWith(ext));
    const shouldSkip = skipExact.some((p) => normalizedUrl === p || normalizedUrl.startsWith(p + '?')) 
      || skipPrefix.some((p) => normalizedUrl.startsWith(p))
      || hasSkipExt;

    if (shouldSkip) {
      url = normalizedUrl; // keep as-is for health checks
    } else if (normalizedUrl.startsWith(normalizedBase + '/')) {
      url = normalizedUrl; // ensure single leading slash when already starts with base
    } else {
      url = normalizedBase + normalizedUrl;
    }
  }

  return next(req.clone({ url }));
};
</file>

<file path="app/core/interceptors/error-logger.interceptor.ts">
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
</file>

<file path="app/core/interceptors/error-mapping.interceptor.ts">
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
</file>

<file path="app/core/interceptors/http.interceptor.ts">
/**
 * Interceptors HTTP para tratamento global de erros e loading
 * Implementa tratamento centralizado de erros e estados de carregamento
 */

import { Injectable, inject } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError, finalize, catchError, timeout } from 'rxjs';
import { LoadingStateService } from '../services/loading-state.service';
import { NotificationService } from '../notifications/notification.service';

import { Router } from '@angular/router';
import { AUTH_OPTIONAL, VISITOR_MODE_KEY } from '../../services/api.config';

@Injectable()
export class LoadingInterceptor implements HttpInterceptor {
  private loadingStateService = inject(LoadingStateService);
  private activeRequests = 0;

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    // Não mostrar loading para requisições específicas
    if (this.shouldSkipLoading(req)) {
      return next.handle(req);
    }

    this.activeRequests++;
    if (this.activeRequests === 1) {
      this.loadingStateService.startLoading('http-request', 'Carregando...');
    }

    return next.handle(req).pipe(
      finalize(() => {
        this.activeRequests--;
        if (this.activeRequests === 0) {
          this.loadingStateService.stopLoading('http-request');
        }
      })
    );
  }

  private shouldSkipLoading(req: HttpRequest<any>): boolean {
    // Skip loading for specific endpoints
    const skipUrls = [
      '/api/notifications',
      '/api/health',
      '/api/ping'
    ];

    return skipUrls.some(url => req.url.includes(url));
  }
}

@Injectable()
export class ErrorInterceptor implements HttpInterceptor {
  private notificationService = inject(NotificationService);

  private router = inject(Router);
  private isVisitorMode(): boolean {
    try {
      return localStorage.getItem(VISITOR_MODE_KEY) === '1';
    } catch {
      return false;
    }
  }

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return next.handle(req).pipe(
      catchError((error: HttpErrorResponse) => {
        this.handleError(error);
        return throwError(() => error);
      })
    );
  }

  private handleError(error: HttpErrorResponse): void {
    let message = 'Ocorreu um erro inesperado';
    let title = 'Erro';

    switch (error.status) {
      case 400:
        title = 'Requisição Inválida';
        message = error.error?.message || 'Dados inválidos fornecidos';
        break;

      case 401:
        title = 'Não Autorizado';
        message = 'Sessão expirada. Por favor, faça login novamente.';
        this.handleUnauthorized();
        break;

      case 403:
        title = 'Acesso Negado';
        message = 'Você não tem permissão para realizar esta ação.';
        break;

      case 404:
        title = 'Não Encontrado';
        message = 'O recurso solicitado não foi encontrado.';
        break;

      case 409:
        title = 'Conflito';
        message = error.error?.message || 'Conflito com o estado atual do recurso.';
        break;

      case 422:
        title = 'Entidade Não Processável';
        message = error.error?.message || 'Os dados fornecidos não puderam ser processados.';
        break;

      case 429:
        title = 'Muitas Requisições';
        message = 'Você excedeu o limite de requisições. Por favor, aguarde.';
        break;

      case 500:
        title = 'Erro do Servidor';
        message = 'Ocorreu um erro no servidor. Por favor, tente novamente.';
        break;

      case 502:
      case 503:
      case 504:
        title = 'Serviço Indisponível';
        message = 'O serviço está temporariamente indisponível. Por favor, tente novamente.';
        break;

      default:
        if (error.status >= 400 && error.status < 500) {
          title = 'Erro de Cliente';
          message = error.error?.message || 'Ocorreu um erro na requisição.';
        } else if (error.status >= 500) {
          title = 'Erro do Servidor';
          message = 'Ocorreu um erro no servidor. Por favor, tente novamente.';
        }
        break;
    }

    this.notificationService.notifyError(title, message);
  }

  private handleUnauthorized(): void {
    if (AUTH_OPTIONAL || this.isVisitorMode()) {
      return;
    }
    // Limpar dados de autenticação
    // Limpar autenticação local
    localStorage.removeItem('token');
    localStorage.removeItem('user');

    // Redirecionar para login com mensagem
    this.router.navigate(['/login'], {
      queryParams: {
        message: 'Sessão expirada. Por favor, faça login novamente.'
      }
    });
  }
}

@Injectable()
export class TimeoutInterceptor implements HttpInterceptor {
  private readonly DEFAULT_TIMEOUT = 30000; // 30 segundos

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    const timeoutValue = req.headers.get('timeout') || this.DEFAULT_TIMEOUT;
    const timeoutMs = typeof timeoutValue === 'string' ? parseInt(timeoutValue, 10) : timeoutValue;

    return next.handle(req).pipe(
      timeout(timeoutMs),
      catchError(error => {
        if (error.name === 'TimeoutError') {
          const notificationService = inject(NotificationService);
          notificationService.notifyWarning('Tempo Limite Excedido', 'A requisição demorou muito tempo para responder.');
        }
        return throwError(() => error);
      })
    );
  }
}

@Injectable()
export class RetryInterceptor implements HttpInterceptor {
  private readonly MAX_RETRIES = 3;
  private readonly RETRY_DELAY = 1000; // 1 segundo

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return this.handleRequest(req, next, 0);
  }

  private handleRequest(req: HttpRequest<any>, next: HttpHandler, retryCount: number): Observable<HttpEvent<any>> {
    return next.handle(req).pipe(
      catchError((error: HttpErrorResponse) => {
        if (this.shouldRetry(error, retryCount)) {
          return this.delay(this.RETRY_DELAY).pipe(
            switchMap(() => this.handleRequest(req, next, retryCount + 1))
          );
        }
        return throwError(() => error);
      })
    );
  }

  private shouldRetry(error: HttpErrorResponse, retryCount: number): boolean {
    // Não tentar novamente se já atingiu o limite
    if (retryCount >= this.MAX_RETRIES) {
      return false;
    }

    // Não tentar novamente para erros de cliente (4xx)
    if (error.status >= 400 && error.status < 500) {
      return false;
    }

    // Tentar novamente para erros de servidor (5xx) e erros de rede
    return error.status >= 500 || !error.status;
  }

  private delay(ms: number): Observable<void> {
    return new Observable<void>(observer => {
      setTimeout(() => {
        observer.next();
        observer.complete();
      }, ms);
    });
  }
}

// Import necessário para o switchMap
import { switchMap } from 'rxjs/operators';
</file>

<file path="app/core/layout/header/header.html">
<header class="app-header">
  <div class="wrap">
    <div class="brand" routerLink="/">
      <app-jarvis-avatar [size]="32" state="idle"></app-jarvis-avatar>
      <span class="brand-text">JANUS<span class="dot">AI</span></span>
    </div>

    <!-- System HUD (Substitui métricas antigas) -->
    <div class="system-metrics desktop-only">
      <app-system-hud></app-system-hud>
    </div>

    <button class="menu-toggle" aria-label="Abrir menu" [attr.aria-expanded]="isMenuOpen" (click)="toggleMenu()">
      <span class="bar"></span>
      <span class="bar"></span>
      <span class="bar"></span>
    </button>

    <nav class="nav" id="primary-navigation" aria-label="Navegacao principal" [class.open]="isMenuOpen">
      <a routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{ exact: true }" (click)="closeMenu()">
        Inicio
      </a>

      @if (isAuthenticated$ | async) {
      <button class="logout-btn" (click)="logout()">Sair</button>
      }
    </nav>
  </div>
</header>
</file>

<file path="app/core/layout/header/header.scss">
/* Header Styles - Jarvis Theme */

.app-header {
  height: 64px;
  background: rgba(var(--janus-bg-dark-rgb), 0.72);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--janus-border);
  box-shadow: 0 12px 30px rgba(7, 10, 18, 0.5), var(--janus-shadow-glow);
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 50;
}

.wrap {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 clamp(16px, 4vw, 40px);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  cursor: pointer;
  transition: opacity 0.2s;

  &:hover {
    opacity: 0.9;
  }
}

.brand-text {
  font-family: var(--janus-font-display);
  font-weight: 700;
  font-size: 1.25rem;
  letter-spacing: 1.4px;
  color: var(--janus-text-primary);
  text-shadow: 0 0 12px rgba(var(--janus-secondary-rgb), 0.45);

  .dot {
    color: var(--janus-secondary);
    animation: pulse 2s infinite;
  }
}

@keyframes pulse {

  0%,
  100% {
    opacity: 1;
    text-shadow: 0 0 10px var(--janus-secondary);
  }

  50% {
    opacity: 0.5;
    text-shadow: 0 0 5px var(--janus-secondary);
  }
}

.nav {
  display: flex;
  gap: 4px;
  align-items: center;

  a {
    color: var(--janus-text-secondary);
    text-decoration: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-size: 0.85rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 1px;
    transition: all 0.3s ease;
    border: 1px solid transparent;

    &:hover {
      color: var(--janus-secondary);
      background: rgba(var(--janus-secondary-rgb), 0.12);
      border-color: rgba(var(--janus-secondary-rgb), 0.24);
      box-shadow: 0 0 16px rgba(var(--janus-secondary-rgb), 0.18);
      text-shadow: 0 0 6px rgba(var(--janus-secondary-rgb), 0.45);
    }

    &.active {
      color: var(--janus-secondary);
      background: rgba(var(--janus-secondary-rgb), 0.08);
      border-color: rgba(var(--janus-secondary-rgb), 0.32);
      box-shadow: inset 0 0 12px rgba(var(--janus-secondary-rgb), 0.14);
    }
  }

  // Hide mobile links on desktop
  .mobile-link {
    display: none;
  }
}

.logout-btn {
  margin-left: 1rem;
  background: transparent;
  border: 1px solid var(--janus-border);
  color: var(--janus-text-muted);
  padding: 6px 16px;
  border-radius: 20px;
  cursor: pointer;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 1px;
  transition: all 0.3s;

  &:hover {
    border-color: var(--destructive);
    color: var(--destructive);
    background: rgba(var(--error-rgb), 0.12);
    box-shadow: 0 0 15px rgba(var(--error-rgb), 0.25);
  }
}

.system-metrics {
  margin-left: auto;
  margin-right: 2rem;
  /* Removido o estilo de .metric antigo pois agora usamos o HUD */
}

.menu-toggle {
  display: none;
  background: transparent;
  border: 1px solid var(--janus-border);
  border-radius: 4px;
  padding: 8px;
  cursor: pointer;

  .bar {
    display: block;
    width: 24px;
    height: 2px;
    background: var(--janus-text-primary);
    margin: 4px 0;
    transition: 0.3s;
  }
}

/* Mobile Responsive */
@media (max-width: 980px) {
  .desktop-only {
    display: none !important;
  }

  .menu-toggle {
    display: block;
  }

  .nav {
    display: none;
    position: absolute;
    top: 64px;
    left: 0;
    right: 0;
    flex-direction: column;
    background: rgba(var(--janus-bg-dark-rgb), 0.95);
    backdrop-filter: blur(16px);
    padding: var(--janus-spacing-md);
    border-bottom: 1px solid var(--janus-border);
    gap: 8px;

    &.open {
      display: flex;
    }

    a {
      width: 100%;
      text-align: center;
      padding: 12px;
    }

    .mobile-link {
      display: block;
    }

    .logout-btn {
      margin: 12px 0 0;
      width: 100%;
    }
  }
}
</file>

<file path="app/core/layout/header/header.spec.ts">
import {ComponentFixture, TestBed} from '@angular/core/testing';
import {RouterTestingModule} from '@angular/router/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import {of} from 'rxjs';
import { vi } from 'vitest';
import {AuthService} from '../../auth/auth.service';
import {Database} from '@angular/fire/database';
import { Router } from '@angular/router';

import {Header} from './header';

describe('Header', () => {
  let component: Header;
  let fixture: ComponentFixture<Header>;
  const authMock = {
    isAuthenticated$: of(false),
    logout: vi.fn().mockResolvedValue(undefined),
  };

  beforeEach(async () => {
    authMock.logout.mockClear();
    await TestBed.configureTestingModule({
      imports: [Header, RouterTestingModule, HttpClientTestingModule],
      providers: [
        { provide: AuthService, useValue: authMock },
        { provide: Database, useValue: {} }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(Header);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should logout and navigate to login', async () => {
    const router = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    await component.logout();

    expect(authMock.logout).toHaveBeenCalled();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
  });
});
</file>

<file path="app/core/layout/header/header.ts">
import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../auth/auth.service';
import { CommonModule } from '@angular/common';
import { JarvisAvatarComponent } from '../../../shared/components/jarvis-avatar/jarvis-avatar.component';
import { SystemHud } from '../../../shared/components/ui/system-hud/system-hud'; // Importar SystemHud
import { Router } from '@angular/router';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, CommonModule, JarvisAvatarComponent, SystemHud],
  templateUrl: './header.html',
  styleUrl: './header.scss'
})
export class Header {
  private auth = inject(AuthService);
  private router = inject(Router);

  isMenuOpen = false;
  isAuthenticated$ = this.auth.isAuthenticated$;

  // metrics$ logic removed in favor of SystemHud component

  toggleMenu() {
    this.isMenuOpen = !this.isMenuOpen;
  }

  closeMenu() {
    this.isMenuOpen = false;
  }

  async logout(): Promise<void> {
    await this.auth.logout();
    this.closeMenu();
    await this.router.navigate(['/login']);
  }
}
</file>

<file path="app/core/layout/sidebar/sidebar.html">
<aside class="sidebar">
  <div class="sidebar-status">
    <div class="status-row">
      <div class="status-label-group">
        <span class="status-dot" [class.ok]="apiHealthy() === 'ok'"></span>
        <span class="status-label">API</span>
      </div>
      <span class="status-value">{{ apiHealthy() === 'ok' ? 'OK' : 'UNKNOWN' }}</span>
    </div>
    <div class="status-row">
      <span class="status-label">Services</span>
      <span class="status-value">{{ services().length }}</span>
    </div>
    <div class="status-row">
      <span class="status-label">Workers</span>
      <span class="status-value">{{ runningWorkers() }}/{{ workers().length }}</span>
    </div>
  </div>

  <div class="sidebar-section">
    <h3 class="section-title">CORE</h3>
    <nav class="side-nav">
      <a class="side-link" routerLink="/" routerLinkActive="active" [routerLinkActiveOptions]="{exact: true}">
        <ui-icon class="icon">home</ui-icon>
        <span class="label">Inicio</span>
      </a>
      <a class="side-link" routerLink="/conversations" routerLinkActive="active">
        <ui-icon class="icon">chat</ui-icon>
        <span class="label">Conversas</span>
      </a>
    </nav>
  </div>

  <div class="sidebar-section">
    <h3 class="section-title">MISSAO</h3>
    <nav class="side-nav">
      <a class="side-link" routerLink="/autonomy" routerLinkActive="active">
        <ui-icon class="icon">settings_suggest</ui-icon>
        <span class="label">Autonomia</span>
      </a>
      <a class="side-link" routerLink="/goals" routerLinkActive="active">
        <ui-icon class="icon">flag</ui-icon>
        <span class="label">Metas</span>
      </a>
      <a class="side-link" routerLink="/sprints" routerLinkActive="active">
        <ui-icon class="icon">event</ui-icon>
        <span class="label">Sprints</span>
      </a>
    </nav>
  </div>

  @if (isAdmin()) {
    <div class="sidebar-section">
      <h3 class="section-title">ADMIN</h3>
      <nav class="side-nav">
        <a class="side-link" routerLink="/admin/autonomia" routerLinkActive="active">
          <ui-icon class="icon">admin_panel_settings</ui-icon>
          <span class="label">Autonomia Admin</span>
        </a>
      </nav>
    </div>
  }

  <div class="sidebar-section">
    <h3 class="section-title">OBSERVABILIDADE</h3>
    <nav class="side-nav">
      <a class="side-link" routerLink="/auto-analysis" routerLinkActive="active">
        <ui-icon class="icon">insights</ui-icon>
        <span class="label">Auto-Analise</span>
      </a>
      <a class="side-link" routerLink="/agent-events" routerLinkActive="active">
        <ui-icon class="icon">hub</ui-icon>
        <span class="label">Agent Events</span>
      </a>
      <a class="side-link" routerLink="/hitl" routerLinkActive="active">
        <ui-icon class="icon">reviews</ui-icon>
        <span class="label">HITL</span>
      </a>
      <a class="side-link" routerLink="/poison-pills" routerLinkActive="active">
        <ui-icon class="icon">warning</ui-icon>
        <span class="label">Poison Pills</span>
      </a>
    </nav>
  </div>

  <div class="sidebar-section">
    <h3 class="section-title">LLM & TOOLS</h3>
    <nav class="side-nav">
      <a class="side-link" routerLink="/ops" routerLinkActive="active">
        <ui-icon class="icon">science</ui-icon>
        <span class="label">LLMOps</span>
      </a>
      <a class="side-link" routerLink="/budget" routerLinkActive="active">
        <ui-icon class="icon">monetization_on</ui-icon>
        <span class="label">Budget</span>
      </a>
      <a class="side-link" routerLink="/tools" routerLinkActive="active">
        <ui-icon class="icon">build</ui-icon>
        <span class="label">Ferramentas</span>
      </a>
    </nav>
  </div>

  <div class="sidebar-section">
    <h3 class="section-title">CONHECIMENTO</h3>
    <nav class="side-nav">
      <a class="side-link" routerLink="/brain" routerLinkActive="active">
        <ui-icon class="icon">psychology</ui-icon>
        <span class="label">Memoria</span>
      </a>
      <a class="side-link" routerLink="/knowledge-graph" routerLinkActive="active">
        <ui-icon class="icon">share</ui-icon>
        <span class="label">Knowledge Graph</span>
      </a>
      <a class="side-link" routerLink="/documents" routerLinkActive="active">
        <ui-icon class="icon">folder</ui-icon>
        <span class="label">Documentos</span>
      </a>
      <a class="side-link" routerLink="/documentacao" routerLinkActive="active">
        <ui-icon class="icon">menu_book</ui-icon>
        <span class="label">Documentacao</span>
      </a>
    </nav>
  </div>

  <div class="sidebar-section">
    <h3 class="section-title">INTERFACES</h3>
    <nav class="side-nav">
      <a class="side-link" routerLink="/senses" routerLinkActive="active">
        <ui-icon class="icon">settings_ethernet</ui-icon>
        <span class="label">Senses</span>
      </a>
      <a class="side-link" routerLink="/ux" routerLinkActive="active">
        <ui-icon class="icon">insights</ui-icon>
        <span class="label">UX Dashboard</span>
      </a>
    </nav>
  </div>
</aside>
</file>

<file path="app/core/layout/sidebar/sidebar.scss">
/* Sidebar - Tech/Jarvis Style */

.sidebar {
    padding: 1.5rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 2rem;
}

.sidebar-status {
    border: 1px solid var(--janus-border);
    border-radius: var(--janus-radius-md);
    background: rgba(var(--janus-secondary-rgb), 0.06);
    padding: 0.75rem;
    display: grid;
    gap: 0.5rem;
}

.status-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
}

.status-label-group {
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--janus-text-muted);
    box-shadow: none;

    &.ok {
        background: var(--janus-secondary);
        box-shadow: 0 0 6px var(--janus-secondary);
    }
}

.status-label {
    font-size: 0.6rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--janus-text-muted);
}

.status-value {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--janus-text-primary);
    font-family: var(--janus-font-mono);
}

.section-title {
    font-size: 0.7rem;
    color: var(--janus-text-muted);
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 0.75rem;
    padding-left: 0.75rem;
    opacity: 0.8;
}

.side-nav {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.side-link {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 0.75rem 1rem;
    text-decoration: none;
    color: var(--janus-text-secondary);
    border-radius: var(--janus-radius-md);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border: 1px solid transparent;
    position: relative;
    overflow: hidden;

    .icon {
        font-size: 1.25rem;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        filter: grayscale(100%);
        transition: filter 0.3s;
    }

    .label {
        font-size: 0.9rem;
        font-weight: 500;
    }

    &:hover {
        background: rgba(var(--janus-secondary-rgb), 0.08);
        color: var(--janus-secondary);
        padding-left: 1.25rem;
        /* Slide effect */
        border-color: rgba(var(--janus-secondary-rgb), 0.2);

        .icon {
            filter: grayscale(0%);
        }

        &::before {
            opacity: 1;
        }
    }

    &.active {
        background: linear-gradient(90deg, rgba(var(--janus-secondary-rgb), 0.18), transparent);
        color: var(--janus-secondary);
        border-left: 3px solid var(--janus-secondary);
        border-radius: 0 var(--janus-radius-md) var(--janus-radius-md) 0;

        .icon {
            filter: grayscale(0%);
        }
    }

    /* Hover glow line */
    &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 2px;
        background: var(--janus-secondary);
        opacity: 0;
        transition: opacity 0.3s;
    }
}
</file>

<file path="app/core/layout/sidebar/sidebar.spec.ts">
import {ComponentFixture, TestBed} from '@angular/core/testing';
import {signal} from '@angular/core';
import {RouterTestingModule} from '@angular/router/testing';

import {Sidebar} from './sidebar';
import {AuthService} from '../../auth/auth.service';
import {GlobalStateStore} from '../../state/global-state.store';

class MockGlobalStateStore {
  apiHealthy = signal<'unknown' | 'ok'>('ok');
  services = signal<any[]>([]);
  workers = signal<any[]>([]);
}

const authMock = {
  isAdmin: signal(false)
};

describe('Sidebar', () => {
  let component: Sidebar;
  let fixture: ComponentFixture<Sidebar>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Sidebar, RouterTestingModule],
      providers: [
        { provide: AuthService, useValue: authMock },
        { provide: GlobalStateStore, useClass: MockGlobalStateStore }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(Sidebar);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
</file>

<file path="app/core/layout/sidebar/sidebar.ts">
import { Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { UiIconComponent } from '../../../shared/components/ui/icon/icon.component';
import { AuthService } from '../../auth/auth.service';
import { GlobalStateStore } from '../../state/global-state.store';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, CommonModule, UiIconComponent],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss'
})
export class Sidebar {
  private store = inject(GlobalStateStore);
  private auth = inject(AuthService);

  readonly apiHealthy = this.store.apiHealthy;
  readonly services = this.store.services;
  readonly workers = this.store.workers;
  readonly isAdmin = this.auth.isAdmin;
  readonly runningWorkers = computed(() =>
    this.workers().filter((worker) => {
      const status = 'state' in worker ? worker.state : worker.status;
      return String(status || '').toLowerCase() === 'running';
    }).length
  );
}
</file>

<file path="app/core/notifications/notification.service.ts">
import { Injectable } from '@angular/core';
import { Subject, Observable } from 'rxjs';

export type NotificationType = 'error' | 'info' | 'success' | 'warning';

export interface NotificationMessage {
  type: NotificationType;
  message: string;
  title?: string;
  detail?: string;
  timestamp?: number;
}

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private subject = new Subject<NotificationMessage>();
  readonly stream$: Observable<NotificationMessage> = this.subject.asObservable();

  notify(msg: NotificationMessage): void {
    this.subject.next({ ...msg, timestamp: Date.now() });
  }

  notifyError(message: string, detail?: string, title?: string): void {
    this.notify({ type: 'error', message, detail, title });
  }

  notifyInfo(message: string, detail?: string, title?: string): void {
    this.notify({ type: 'info', message, detail, title });
  }

  notifyWarning(message: string, detail?: string, title?: string): void {
    this.notify({ type: 'warning', message, detail, title });
  }

  notifySuccess(message: string, detail?: string, title?: string): void {
    this.notify({ type: 'success', message, detail, title });
  }
}
</file>

<file path="app/core/resolvers/app.resolver.ts">
/**
 * Resolvers para pré-carregamento de dados antes da ativação de rotas
 * Implementa carregamento inteligente de dados para melhorar performance
 */

import { Injectable, inject } from '@angular/core';
import { Resolve, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { Observable, of, catchError, tap } from 'rxjs';
import { LoadingStateService } from '../services/loading-state.service';
import { NotificationService } from '../notifications/notification.service';
import { ChatMessage } from '../../services/backend-api.service';

/**
 * Interface base para resolvers com loading e tratamento de erros
 */
export interface BaseResolver<T> {
  resolve(
    route: ActivatedRouteSnapshot,
    state: RouterStateSnapshot
  ): Observable<T> | Promise<T> | T;
}

export interface DashboardMetric {
  label: string;
  value: string | number;
  trend: 'up' | 'down' | 'stable';
}

export interface DashboardWidget {
  id: string;
  type: 'chart' | 'metric';
  title: string;
}

export interface DashboardData {
  metrics: DashboardMetric[];
  widgets: DashboardWidget[];
  notifications: unknown[];
}

/**
 * Resolver de dashboard com pré-carregamento de dados principais
 */
@Injectable({
  providedIn: 'root'
})
export class DashboardResolver implements Resolve<DashboardData | null> {
  private loadingState = inject(LoadingStateService);
  private notificationService = inject(NotificationService);

  resolve(
    _route: ActivatedRouteSnapshot,
    _state: RouterStateSnapshot
  ): Observable<DashboardData | null> {
    this.loadingState.startLoading('dashboard', { message: 'Carregando dashboard...' });

    // Simular carregamento de dados do dashboard
    return of({
      metrics: this.loadDashboardMetrics(),
      widgets: this.loadDashboardWidgets(),
      notifications: this.loadNotifications()
    }).pipe(
      tap(() => this.loadingState.stopLoading('dashboard')),
      catchError(_error => {
        this.loadingState.stopLoading('dashboard');
        this.notificationService.notifyError('Erro ao carregar dashboard', 'Não foi possível carregar os dados do dashboard');
        return of(null);
      })
    );
  }

  private loadDashboardMetrics(): DashboardMetric[] {
    // Implementar carregamento real de métricas
    return [
      { label: 'Total de Conversas', value: 1234, trend: 'up' },
      { label: 'Taxa de Sucesso', value: '98.5%', trend: 'stable' },
      { label: 'Tempo Médio', value: '2.3s', trend: 'down' }
    ];
  }

  private loadDashboardWidgets(): DashboardWidget[] {
    // Implementar carregamento real de widgets
    return [
      { id: 'chat', type: 'chart', title: 'Conversas por Hora' },
      { id: 'performance', type: 'metric', title: 'Performance do Sistema' }
    ];
  }

  private loadNotifications(): unknown[] {
    // Implementar carregamento real de notificações
    return [];
  }
}

export interface ChatResolverData {
  conversation: { id: string; title: string } | null;
  messages: ChatMessage[];
}

/**
 * Resolver de chat com pré-carregamento de histórico
 */
@Injectable({
  providedIn: 'root'
})
export class ChatResolver implements Resolve<ChatResolverData> {
  private loadingState = inject(LoadingStateService);
  private notificationService = inject(NotificationService);

  resolve(
    route: ActivatedRouteSnapshot,
    _state: RouterStateSnapshot
  ): Observable<ChatResolverData> {
    const conversationId = route.paramMap.get('conversationId');

    if (!conversationId) {
      return of({ conversation: null, messages: [] });
    }

    this.loadingState.startLoading('chat', { message: 'Carregando conversa...' });

    // Simular carregamento de dados da conversa
    return of({
      conversation: { id: conversationId, title: 'Conversa #' + conversationId },
      messages: this.loadMessages(conversationId)
    }).pipe(
      tap(() => this.loadingState.stopLoading('chat')),
      catchError(_error => {
        this.loadingState.stopLoading('chat');
        this.notificationService.notifyError('Erro ao carregar conversa', 'Não foi possível carregar os dados da conversa');
        return of({ conversation: null, messages: [] });
      })
    );
  }

  private loadMessages(_conversationId: string): ChatMessage[] {
    // Implementar carregamento real de mensagens
    return [];
  }
}

export interface SettingsData {
  userSettings: Record<string, unknown>;
  systemSettings: Record<string, unknown>;
  preferences: Record<string, unknown>;
}

/**
 * Resolver de configurações com pré-carregamento
 */
@Injectable({
  providedIn: 'root'
})
export class SettingsResolver implements Resolve<SettingsData> {
  private loadingState = inject(LoadingStateService);
  private notificationService = inject(NotificationService);

  resolve(
    _route: ActivatedRouteSnapshot,
    _state: RouterStateSnapshot
  ): Observable<SettingsData> {
    this.loadingState.startLoading('settings', { message: 'Carregando configurações...' });

    // Simular carregamento de configurações
    return of({
      userSettings: this.loadUserSettings(),
      systemSettings: this.loadSystemSettings(),
      preferences: this.loadPreferences()
    }).pipe(
      tap(() => this.loadingState.stopLoading('settings')),
      catchError(_error => {
        this.loadingState.stopLoading('settings');
        this.notificationService.notifyError('Erro ao carregar configurações', 'Não foi possível carregar as configurações');
        return of({ userSettings: {}, systemSettings: {}, preferences: {} });
      })
    );
  }

  private loadUserSettings(): Record<string, unknown> {
    // Implementar carregamento real de configurações do usuário
    return {
      theme: 'dark',
      language: 'pt-BR',
      notifications: true
    };
  }

  private loadSystemSettings(): Record<string, unknown> {
    // Implementar carregamento real de configurações do sistema
    return {
      apiUrl: 'https://api.example.com',
      timeout: 30000,
      retries: 3
    };
  }

  private loadPreferences(): Record<string, unknown> {
    // Implementar carregamento real de preferências
    return {
      autoRefresh: true,
      showNotifications: true,
      soundEnabled: false
    };
  }
}

export interface UserData {
  profile: Record<string, unknown> | null;
  permissions: string[];
  roles: string[];
}

/**
 * Resolver de dados de usuário
 */
@Injectable({
  providedIn: 'root'
})
export class UserResolver implements Resolve<UserData> {
  private loadingState = inject(LoadingStateService);
  private notificationService = inject(NotificationService);

  resolve(
    _route: ActivatedRouteSnapshot,
    _state: RouterStateSnapshot
  ): Observable<UserData> {
    this.loadingState.startLoading('user', { message: 'Carregando dados do usuário...' });

    // Simular carregamento de dados do usuário
    return of({
      profile: this.loadUserProfile(),
      permissions: this.loadUserPermissions(),
      roles: this.loadUserRoles()
    }).pipe(
      tap(() => this.loadingState.stopLoading('user')),
      catchError(_error => {
        this.loadingState.stopLoading('user');
        this.notificationService.notifyError('Erro ao carregar dados do usuário', 'Não foi possível carregar os dados do usuário');
        return of({ profile: null, permissions: [], roles: [] });
      })
    );
  }

  private loadUserProfile(): Record<string, unknown> {
    // Implementar carregamento real de perfil do usuário
    return {
      id: '1',
      name: 'Usuário',
      email: 'usuario@example.com',
      avatar: 'assets/avatar.png'
    };
  }

  private loadUserPermissions(): string[] {
    // Implementar carregamento real de permissões
    return ['read', 'write'];
  }

  private loadUserRoles(): string[] {
    // Implementar carregamento real de roles
    return ['user'];
  }
}
</file>

<file path="app/core/services/agent-events.service.ts">
import { Injectable, NgZone } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { API_BASE_URL } from '../../services/api.config';
import { AuthService } from '../auth/auth.service';
import { AppLoggerService } from './app-logger.service';

export interface AgentEvent {
    task_id: string;
    agent_role: string;
    event_type: string;
    content: string;
    conversation_id: string;
    timestamp: number;
}

@Injectable({
    providedIn: 'root'
})
export class AgentEventsService {
    private eventSource?: EventSource;
    private _events$ = new Subject<AgentEvent>();
    private currentConversationId?: string;

    constructor(
        private zone: NgZone,
        private auth: AuthService,
        private logger: AppLoggerService
    ) { }

    public get events$(): Observable<AgentEvent> {
        return this._events$.asObservable();
    }

    public connect(conversationId: string): void {
        if (this.eventSource) {
            this.eventSource.close();
        }
        this.currentConversationId = conversationId;

        // Prepare URL with user_id param for simple auth/tracking
        let url = `${API_BASE_URL}/v1/chat/${conversationId}/events`;

        // Attempt to get current user ID
        // Note: AuthService might expose it synchronously or we might need to subscribe.
        // For simplicity, we assume we can get it from localStorage or AuthService state if available.
        // Let's rely on backend 'http.state' (cookies) mostly, but ideally we pass query param.
        // Assuming auth.currentUser value is available or we decode token.
        const user = this.auth.currentUserValue; // Hypothetical accessor
        if (user?.id) {
            url += `?user_id=${user.id}`;
        }

        this.logger.info('[AgentEvents] Connecting', { url });

        this.eventSource = new EventSource(url);

        this.eventSource.onmessage = (event) => {
            this.zone.run(() => {
                try {
                    const data = JSON.parse(event.data);
                    this._events$.next(this.normalizeEvent(data));
                } catch (e) {
                    this.logger.error('[AgentEvents] Error parsing event', e);
                }
            });
        };

        this.eventSource.onerror = (_error) => {
            this.zone.run(() => {
                // EventSource automatically retries, but we logs it
                // If state is CLOSED (2), we might need manual reconnect logic or let it be.
                if (this.eventSource?.readyState === EventSource.CLOSED) {
                    this.logger.warn('[AgentEvents] Connection closed');
                }
            });
        };

        // Listen for named events if the backend sends them (e.g. event: agent_event)
        this.eventSource.addEventListener('agent_event', (event: MessageEvent) => {
            this.zone.run(() => {
                try {
                    const data = JSON.parse(event.data);
                    this._events$.next(this.normalizeEvent(data));
                } catch (e) {
                    this.logger.error('[AgentEvents] Error parsing named event', e);
                }
            });
        });
    }

    public disconnect(): void {
        if (this.eventSource) {
            this.logger.info('[AgentEvents] Disconnecting');
            this.eventSource.close();
            this.eventSource = undefined;
        }
        this.currentConversationId = undefined;
    }

    /**
     * Normaliza eventos vindos do SSE para o formato esperado pelo HUD.
     * Backend pode enviar chaves diferentes (type vs event_type, agent vs agent_role).
     */
    private normalizeEvent(data: any): AgentEvent {
        const now = Date.now();
        return {
            event_type: data?.event_type || data?.type || 'unknown',
            agent_role: data?.agent_role || data?.agent || 'unknown',
            content: data?.content || '',
            conversation_id: data?.conversation_id || this.currentConversationId || '',
            task_id: data?.task_id || data?.thread_id || data?.conversation_id || this.currentConversationId || '',
            timestamp: data?.timestamp ? Number(data.timestamp) : now
        };
    }
}
</file>

<file path="app/core/services/app-logger.service.ts">
import { Injectable } from '@angular/core'
import { environment } from '../../../environments/environment'

type LogLevel = 'debug' | 'info' | 'warn' | 'error'

const LOG_PRIORITY: Record<LogLevel, number> = {
  debug: 10,
  info: 20,
  warn: 30,
  error: 40,
}

@Injectable({ providedIn: 'root' })
export class AppLoggerService {
  private readonly activeLevel: LogLevel = this.resolveLevel(environment.logging?.level)

  debug(message: string, meta?: unknown): void {
    this.write('debug', message, meta)
  }

  info(message: string, meta?: unknown): void {
    this.write('info', message, meta)
  }

  warn(message: string, meta?: unknown): void {
    this.write('warn', message, meta)
  }

  error(message: string, meta?: unknown): void {
    this.write('error', message, meta)
  }

  private write(level: LogLevel, message: string, meta?: unknown): void {
    if (!this.shouldLog(level)) return

    const now = new Date().toISOString()
    const payload = meta === undefined ? undefined : this.safeSerialize(meta)
    const line = `[${now}] [${level.toUpperCase()}] ${message}`

    const sink = globalThis.console?.[level]
    if (typeof sink !== 'function') return

    if (payload === undefined) {
      sink.call(globalThis.console, line)
      return
    }

    sink.call(globalThis.console, line, payload)
  }

  private shouldLog(level: LogLevel): boolean {
    return LOG_PRIORITY[level] >= LOG_PRIORITY[this.activeLevel]
  }

  private resolveLevel(value: string | undefined): LogLevel {
    if (value === 'debug' || value === 'info' || value === 'warn' || value === 'error') {
      return value
    }
    return environment.production ? 'warn' : 'debug'
  }

  private safeSerialize(meta: unknown): unknown {
    if (meta === null || meta === undefined) return meta
    if (typeof meta !== 'object') return meta

    try {
      return JSON.parse(JSON.stringify(meta))
    } catch {
      return String(meta)
    }
  }
}
</file>

<file path="app/core/services/demo.service.ts">
import { Injectable, signal } from '@angular/core';
import { AppLoggerService } from './app-logger.service';

@Injectable({
    providedIn: 'root'
})
export class DemoService {
    // Signal to track if we are in offline/demo mode
    // Default to false, potentially set to true on first error
    readonly isOffline = signal<boolean>(false);

    constructor(private readonly logger: AppLoggerService) {
        // Always start fresh, let the app discover if backend is down
        this.isOffline.set(false);
    }

    /**
     * Enable offline mode.
     * Can be called by interceptors when critical failures occur.
     */
    enableOfflineMode(): void {
        if (!this.isOffline()) {
            this.logger.warn('[DemoService] Backend unreachable. Switching to Demo/Offline Mode.');
            this.isOffline.set(true);
            // sessionStorage.setItem('JANUS_OFFLINE_MODE', 'true');
        }
    }

    /**
     * Reset offline mode (e.g. if user manually retries).
     */
    resetMode(): void {
        this.isOffline.set(false);
        sessionStorage.removeItem('JANUS_OFFLINE_MODE');
    }
}
</file>

<file path="app/core/services/loading-state.service.spec.ts">
import { TestBed } from '@angular/core/testing'
import { LoadingStateService } from './loading-state.service'
import { LoadingConfig } from '../types'

describe('LoadingStateService', () => {
  let service: LoadingStateService

  beforeEach(() => {
    TestBed.configureTestingModule({})
    service = TestBed.inject(LoadingStateService)
  })

  it('should be created', () => {
    expect(service).toBeTruthy()
  })

  describe('startLoading', () => {
    it('should start loading with default config', () => {
      service.startLoading('test-key')
      
      expect(service.isKeyLoading('test-key')).toBe(true)
      expect(service.isLoading()).toBe(true)
      
      const state = service.getLoadingState('test-key')
      expect(state?.isLoading).toBe(true)
      expect(state?.timestamp).toBeDefined()
    })

    it('should start loading with custom config', () => {
      const config: LoadingConfig = {
        message: 'Test message',
        progress: 50,
        global: true,
        http: true
      }
      
      service.startLoading('test-key', config)
      
      const state = service.getLoadingState('test-key')
      expect(state?.message).toBe('Test message')
      expect(state?.progress).toBe(50)
      expect(service.isGlobalLoading()).toBe(true)
      expect(service.isHttpLoading()).toBe(true)
    })
  })

  describe('stopLoading', () => {
    it('should stop loading and update state', (done) => {
      service.startLoading('test-key')
      expect(service.isKeyLoading('test-key')).toBe(true)
      
      service.stopLoading('test-key')
      
      // Should still be loading immediately after stop
      expect(service.isKeyLoading('test-key')).toBe(false)
      
      // State should be removed after delay
      setTimeout(() => {
        expect(service.getLoadingState('test-key')).toBeUndefined()
        expect(service.isLoading()).toBe(false)
        done()
      }, 400)
    })

    it('should update global loading state', (done) => {
      service.startLoading('key1', { global: true })
      service.startLoading('key2', { global: true })
      
      expect(service.isGlobalLoading()).toBe(true)
      
      service.stopLoading('key1')
      expect(service.isGlobalLoading()).toBe(true) // Still have key2
      
      service.stopLoading('key2')
      
      setTimeout(() => {
        expect(service.isGlobalLoading()).toBe(false)
        done()
      }, 400)
    })
  })

  describe('updateProgress', () => {
    it('should update progress for existing loading state', () => {
      service.startLoading('test-key')
      
      service.updateProgress('test-key', 75)
      
      const state = service.getLoadingState('test-key')
      expect(state?.progress).toBe(75)
    })

    it('should not update progress for non-existing key', () => {
      service.updateProgress('non-existing', 100)
      
      expect(service.getLoadingState('non-existing')).toBeUndefined()
    })
  })

  describe('updateMessage', () => {
    it('should update message for existing loading state', () => {
      service.startLoading('test-key')
      
      service.updateMessage('test-key', 'New message')
      
      const state = service.getLoadingState('test-key')
      expect(state?.message).toBe('New message')
    })

    it('should not update message for non-existing key', () => {
      service.updateMessage('non-existing', 'New message')
      
      expect(service.getLoadingState('non-existing')).toBeUndefined()
    })
  })

  describe('clearAll', () => {
    it('should clear all loading states', () => {
      service.startLoading('key1')
      service.startLoading('key2')
      service.startLoading('key3', { global: true, http: true })
      
      expect(service.isLoading()).toBe(true)
      expect(service.isGlobalLoading()).toBe(true)
      expect(service.isHttpLoading()).toBe(true)
      
      service.clearAll()
      
      expect(service.isLoading()).toBe(false)
      expect(service.isGlobalLoading()).toBe(false)
      expect(service.isHttpLoading()).toBe(false)
      expect(service.loadingKeys()).toEqual([])
    })
  })

  describe('forceStopAll', () => {
    it('should force stop all active loadings', (done) => {
      service.startLoading('key1')
      service.startLoading('key2')
      
      expect(service.isLoading()).toBe(true)
      
      service.forceStopAll()
      
      setTimeout(() => {
        expect(service.isLoading()).toBe(false)
        expect(service.loadingKeys()).toEqual([])
        done()
      }, 400)
    })
  })

  describe('loadingKeys', () => {
    it('should return only active loading keys', () => {
      service.startLoading('key1')
      service.startLoading('key2')
      service.stopLoading('key1')
      
      const keys = service.loadingKeys()
      expect(keys).toEqual(['key2'])
    })
  })
})
</file>

<file path="app/core/services/loading-state.service.ts">
import { Injectable, signal, computed } from '@angular/core'
import { LoadingState, LoadingConfig } from '../types'

/**
 * Serviço global para gerenciamento de estados de loading
 * Fornece controle granular de loading para diferentes partes da aplicação
 */
@Injectable({
  providedIn: 'root'
})
export class LoadingStateService {
  private readonly loadingStates = signal<Map<string, LoadingState>>(new Map())
  private readonly globalLoading = signal<boolean>(false)
  private readonly httpLoading = signal<boolean>(false)

  readonly isLoading = computed(() => {
    const states = this.loadingStates()
    return states.size > 0 && Array.from(states.values()).some(state => state.isLoading)
  })

  readonly isGlobalLoading = computed(() => this.globalLoading())
  readonly isHttpLoading = computed(() => this.httpLoading())

  readonly loadingKeys = computed(() => {
    const states = this.loadingStates()
    return Array.from(states.entries())
      .filter(([, state]) => state.isLoading)
      .map(([key]) => key)
  })

  /**
   * Inicia estado de loading para uma chave específica
   */
  startLoading(key: string, config?: LoadingConfig): void
  startLoading(key: string, message?: string): void
  startLoading(key: string, configOrMessage?: LoadingConfig | string): void {
    const config: LoadingConfig = typeof configOrMessage === 'string'
      ? { message: configOrMessage }
      : configOrMessage || {}
    const currentStates = this.loadingStates()
    const newState: LoadingState = {
      isLoading: true,
      message: config?.message || '',
      progress: config?.progress || 0,
      timestamp: Date.now()
    }

    currentStates.set(key, newState)
    this.loadingStates.set(new Map(currentStates))

    if (config?.global) {
      this.globalLoading.set(true)
    }

    if (config?.http) {
      this.httpLoading.set(true)
    }
  }

  /**
   * Atualiza progresso de loading para uma chave específica
   */
  updateProgress(key: string, progress: number): void {
    const currentStates = this.loadingStates()
    const existingState = currentStates.get(key)

    if (existingState) {
      existingState.progress = progress
      this.loadingStates.set(new Map(currentStates))
    }
  }

  /**
   * Atualiza mensagem de loading para uma chave específica
   */
  updateMessage(key: string, message: string): void {
    const currentStates = this.loadingStates()
    const existingState = currentStates.get(key)

    if (existingState) {
      existingState.message = message
      this.loadingStates.set(new Map(currentStates))
    }
  }

  /**
   * Finaliza estado de loading para uma chave específica
   */
  stopLoading(key: string): void {
    const currentStates = this.loadingStates()
    const existingState = currentStates.get(key)

    if (existingState) {
      existingState.isLoading = false
      existingState.completedAt = Date.now()

      // Remove após um pequeno delay para permitir animações
      setTimeout(() => {
        const states = this.loadingStates()
        states.delete(key)
        this.loadingStates.set(new Map(states))

        // Verifica se ainda há loading global/HTTP ativo
        const hasGlobalLoading = Array.from(states.values()).some(s => s.isLoading && s.global)
        const hasHttpLoading = Array.from(states.values()).some(s => s.isLoading && s.http)

        this.globalLoading.set(hasGlobalLoading)
        this.httpLoading.set(hasHttpLoading)
      }, 300)
    }
  }

  /**
   * Verifica se uma chave específica está em loading
   */
  isKeyLoading(key: string): boolean {
    const state = this.loadingStates().get(key)
    return state?.isLoading || false
  }

  /**
   * Obtém estado de loading para uma chave específica
   */
  getLoadingState(key: string): LoadingState | undefined {
    return this.loadingStates().get(key)
  }

  /**
   * Limpa todos os estados de loading
   */
  clearAll(): void {
    this.loadingStates.set(new Map())
    this.globalLoading.set(false)
    this.httpLoading.set(false)
  }

  /**
   * Força finalização de todos os loadings ativos
   */
  forceStopAll(): void {
    const states = this.loadingStates()
    states.forEach((state, _key) => {
      state.isLoading = false
      state.completedAt = Date.now()
    })

    setTimeout(() => {
      this.clearAll()
    }, 300)
  }
}
</file>

<file path="app/core/services/system-status.service.ts">
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, timer, of } from 'rxjs';
import { catchError, map, switchMap, shareReplay, retry } from 'rxjs/operators';
import { AppLoggerService } from './app-logger.service';
import { API_BASE_URL } from '../../services/api.config';

export interface SystemStatusResponse {
  app_name: string;
  version: string;
  environment: string;
  status: string;
  uptime_seconds: number;
  system?: any;
  process?: any;
  performance?: any;
}

export interface ServiceHealthItem {
  key: string;
  name: string;
  status: 'ok' | 'degraded' | 'error' | 'unknown';
  metric_text?: string;
}

export interface ServiceHealthResponse {
  services: ServiceHealthItem[];
}

@Injectable({
  providedIn: 'root',
})
export class SystemStatusService {
  // Reuse the same API base used by the chat/auth flows (defaults to `/api` behind the frontend proxy).
  private apiUrl = `${API_BASE_URL}/v1/system`;
  
  // Cache shareReplay para evitar múltiplas chamadas simultâneas
  private statusCache$: Observable<SystemStatusResponse> | null = null;
  private healthCache$: Observable<ServiceHealthResponse> | null = null;

  // Estado reativo para componentes ouvirem
  private _isSystemHealthy = new BehaviorSubject<boolean>(true);
  public isSystemHealthy$ = this._isSystemHealthy.asObservable();

  constructor(private http: HttpClient, private readonly logger: AppLoggerService) {}

  /**
   * Obtém o status geral do sistema (versão, uptime, etc)
   */
  getSystemStatus(): Observable<SystemStatusResponse> {
    if (!this.statusCache$) {
      this.statusCache$ = timer(0, 30000).pipe( // Polling a cada 30s
        switchMap(() => this.http.get<SystemStatusResponse>(`${this.apiUrl}/status`).pipe(
          retry(1),
          catchError(err => {
            this.logger.error('[SystemStatusService] Erro ao buscar status do sistema', err);
            return of({
              app_name: 'Janus',
              version: 'unknown',
              environment: 'unknown',
              status: 'ERROR',
              uptime_seconds: 0
            } as SystemStatusResponse);
          })
        )),
        shareReplay(1)
      );
    }
    return this.statusCache$;
  }

  /**
   * Obtém a saúde detalhada dos microsserviços (Agentes, LLM, Memória)
   */
  getServicesHealth(): Observable<ServiceHealthResponse> {
    // Polling mais frequente para health check (15s)
    return timer(0, 15000).pipe(
      switchMap(() => this.http.get<ServiceHealthResponse>(`${this.apiUrl}/health/services`).pipe(
        map(response => {
          // Atualiza o estado global de saúde baseado nos serviços
          const hasError = response.services.some(s => s.status === 'error');
          this._isSystemHealthy.next(!hasError);
          return response;
        }),
        catchError(err => {
          this.logger.error('[SystemStatusService] Erro ao buscar saúde dos serviços', err);
          this._isSystemHealthy.next(false);
          return of({ services: [] } as ServiceHealthResponse);
        })
      )),
      shareReplay(1)
    );
  }

  /**
   * Força uma atualização imediata (útil quando o usuário abre o HUD)
   */
  refreshHealth() {
    // A implementação com timer/switchMap atualiza automaticamente, 
    // mas se precisarmos de refresh manual, podemos resetar o cache ou usar um Subject de trigger.
    // Por enquanto, o polling automático é suficiente.
  }
}
</file>

<file path="app/core/services/system-status.spec.ts">
import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';

import { SystemStatusService } from './system-status.service';

describe('SystemStatusService', () => {
  let service: SystemStatusService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule]
    });
    service = TestBed.inject(SystemStatusService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
</file>

<file path="app/core/services/tailscale.service.ts">
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';
import { AppLoggerService } from './app-logger.service';

export interface TailscaleConfig {
  enabled: boolean;
  host?: string;
  backendUrl?: string;
  frontendUrl?: string;
}

export interface SystemHealth {
  status: string;
  service: string;
  version: string;
  environment: string;
  tailscale?: TailscaleConfig;
}

@Injectable({
  providedIn: 'root'
})
export class TailscaleService {
  private tailscaleConfig: TailscaleConfig | null = null;
  private apiUrl: string;

  constructor(private http: HttpClient, private readonly logger: AppLoggerService) {
    this.apiUrl = this.getApiUrl();
  }

  /**
   * Get the appropriate API URL based on Tailscale configuration
   */
  private getApiUrl(): string {
    // Check if Tailscale is enabled and configured
    if (environment.tailscale?.enabled && environment.tailscale?.apiUrl) {
      return environment.tailscale.apiUrl;
    }
    
    // Fall back to default API URL
    return environment.apiUrl;
  }

  /**
   * Check if Tailscale Serve is enabled and configured
   */
  isTailscaleEnabled(): boolean {
    return environment.tailscale?.enabled || false;
  }

  /**
   * Get current Tailscale configuration
   */
  getTailscaleConfig(): Observable<TailscaleConfig> {
    if (this.tailscaleConfig) {
      return of(this.tailscaleConfig);
    }

    // Try to get Tailscale config from backend health endpoint
    return this.http.get<SystemHealth>(`${this.apiUrl}/health`).pipe(
      map(health => {
        this.tailscaleConfig = health.tailscale || {
          enabled: false
        };
        return this.tailscaleConfig;
      }),
      catchError(() => {
        // If health endpoint fails, return local config
        this.tailscaleConfig = {
          enabled: this.isTailscaleEnabled(),
          backendUrl: environment.tailscale?.apiUrl,
          frontendUrl: environment.tailscale?.frontendUrl
        };
        return of(this.tailscaleConfig);
      })
    );
  }

  /**
   * Get system health including Tailscale status
   */
  getSystemHealth(): Observable<SystemHealth> {
    return this.http.get<SystemHealth>(`${this.apiUrl}/health`);
  }

  /**
   * Test connectivity to backend via Tailscale
   */
  testBackendConnectivity(): Observable<boolean> {
    return this.http.get<SystemHealth>(`${this.apiUrl}/health`).pipe(
      map(() => true),
      catchError(() => of(false))
    );
  }

  /**
   * Get Tailscale status information
   */
  getTailscaleStatus(): Observable<any> {
    return this.http.get(`${this.apiUrl}/system/status`).pipe(
      catchError(error => {
        this.logger.warn('[TailscaleService] Failed to get system status', error);
        return of(null);
      })
    );
  }

  /**
   * Update API URL dynamically (useful for switching between local and Tailscale)
   */
  updateApiUrl(url: string): void {
    this.apiUrl = url;
  }

  /**
   * Get the current API URL
   */
  getCurrentApiUrl(): string {
    return this.apiUrl;
  }

  /**
   * Check if we're currently using Tailscale URLs
   */
  isUsingTailscaleUrls(): boolean {
    return this.isTailscaleEnabled() && 
           this.apiUrl.includes('.ts.net');
  }
}
</file>

<file path="app/core/state/global-state.store.ts">
import { Injectable, signal } from '@angular/core';
import {
  BackendApiService,
  OrchestratorWorkerTaskStatus,
  ServiceHealthItem,
  SystemOverviewResponse,
  SystemStatus,
  WorkerStatusResponse,
} from '../../services/backend-api.service';
import { take, timeout, retry } from 'rxjs/operators';
import { Subscription, timer } from 'rxjs';
import { switchMap } from 'rxjs';
import { AppLoggerService } from '../services/app-logger.service';

@Injectable({ providedIn: 'root' })
export class GlobalStateStore {
  // Signals para reuso entre páginas
  readonly loading = signal<boolean>(false);
  readonly apiHealthy = signal<'unknown' | 'ok'>('unknown');
  readonly systemStatus = signal<SystemStatus | undefined>(undefined);
  readonly services = signal<ServiceHealthItem[]>([]);
  readonly workers = signal<Array<WorkerStatusResponse | OrchestratorWorkerTaskStatus>>([]);

  // Controle interno
  private initialized = false;
  private pollSub?: Subscription;
  private spinnerSafetyTimeout?: ReturnType<typeof setTimeout>;

  constructor(private api: BackendApiService, private logger: AppLoggerService) { }

  // Uma única carga (usada internamente pelo startPolling)
  private fetchOverviewOnce(): Promise<boolean> {
    return new Promise((resolve) => {
      this.logger.debug('[Store] Fetching system overview');
      this.api.getSystemOverview().pipe(
        take(1),
        timeout({ each: 5000 }),
        retry({ count: 1 })
      ).subscribe({
        next: (overview: SystemOverviewResponse) => {
          this.logger.debug('[Store] System overview received', overview);
          this.apiHealthy.set(overview.system_status.status === 'ok' ? 'ok' : 'unknown');
          this.systemStatus.set(overview.system_status);
          this.services.set(overview.services_status || []);
          this.workers.set(overview.workers_status || []);
          resolve(true);
        },
        error: (error) => {
          this.logger.error('[Store] Failed to fetch system overview', error);
          resolve(false);
        }
      });
    });
  }

  // Inicia polling controlado (primeiro tick mostra spinner, demais silenciosos)
  startPolling(intervalMs: number): void {
    if (this.pollSub) this.pollSub.unsubscribe();
    const showSpinner = !this.initialized;
    if (showSpinner) this.loading.set(true);
    this.logger.debug('[Store] startPolling', { intervalMs, showSpinner });

    // Fallback de segurança: garante que o spinner não fique infinito
    if (showSpinner) {
      if (this.spinnerSafetyTimeout) clearTimeout(this.spinnerSafetyTimeout);
      this.spinnerSafetyTimeout = setTimeout(() => {
        if (!this.initialized) {
          this.loading.set(false);
          this.initialized = true;
          this.logger.debug('[Store] safety timeout -> spinner off');
        }
      }, Math.min(intervalMs + 5000, 10000));
    }

    this.pollSub = timer(0, intervalMs).pipe(
      switchMap(() => {
        this.logger.debug('[Store] polling tick');
        return this.api.getSystemOverview().pipe(
          take(1),
          timeout({ each: 5000 }),
          retry({ count: 1 })
        )
      })
    ).subscribe({
      next: (overview: SystemOverviewResponse) => {
        this.logger.debug('[Store] overview received', {
          apiStatus: overview.system_status.status,
          services: (overview.services_status || []).length,
          workers: (overview.workers_status || []).length
        });
        this.apiHealthy.set(overview.system_status.status === 'ok' ? 'ok' : 'unknown');
        this.systemStatus.set(overview.system_status);
        this.services.set(overview.services_status || []);
        this.workers.set(overview.workers_status || []);
        if (showSpinner && !this.initialized) {
          this.loading.set(false);
          this.initialized = true;
          if (this.spinnerSafetyTimeout) { clearTimeout(this.spinnerSafetyTimeout); this.spinnerSafetyTimeout = undefined; }
          this.logger.debug('[Store] first load complete; spinner off');
        }
      },
      error: (err) => {
        this.logger.debug('[Store] overview error', err?.message || err);
        if (showSpinner && !this.initialized) {
          this.loading.set(false);
          this.initialized = true;
          if (this.spinnerSafetyTimeout) { clearTimeout(this.spinnerSafetyTimeout); this.spinnerSafetyTimeout = undefined; }
          this.logger.debug('[Store] first load error; spinner off');
        }
      }
    });
  }

  stopPolling(): void {
    this.pollSub?.unsubscribe();
    this.pollSub = undefined;
    if (this.spinnerSafetyTimeout) { clearTimeout(this.spinnerSafetyTimeout); this.spinnerSafetyTimeout = undefined; }
    this.logger.debug('[Store] stopPolling');
  }

  // Ações de workers
  startAllWorkers(): void {
    this.logger.debug('[Store] startAllWorkers');
    this.api.startAllWorkers().pipe(take(1)).subscribe({
      next: () => { this.logger.debug('[Store] startAllWorkers -> ok'); this.refreshWorkers(); },
      error: (e) => { this.logger.debug('[Store] startAllWorkers -> error', e?.message || e); }
    });
  }

  stopAllWorkers(): void {
    this.logger.debug('[Store] stopAllWorkers');
    this.api.stopAllWorkers().pipe(take(1)).subscribe({
      next: () => { this.logger.debug('[Store] stopAllWorkers -> ok'); this.refreshWorkers(); },
      error: (e) => { this.logger.debug('[Store] stopAllWorkers -> error', e?.message || e); }
    });
  }

  refreshWorkers(): void {
    this.logger.debug('[Store] refreshWorkers');
    this.api.getWorkersStatus().pipe(take(1)).subscribe({
      next: (resp) => { this.logger.debug('[Store] refreshWorkers -> received', (resp.workers || []).length); this.workers.set(resp.workers || []); },
      error: (e) => { this.logger.debug('[Store] refreshWorkers -> error', e?.message || e); }
    });
  }

  refreshSystemStatus(): void {
    this.logger.debug('[Store] refreshSystemStatus (manual)');
    this.fetchOverviewOnce().then(ok => {
      this.logger.debug('[Store] refreshSystemStatus completed', ok ? 'successfully' : 'with errors');
    });
  }
}
</file>

<file path="app/core/types/angular.types.ts">
/**
 * Tipos TypeScript estritos para melhores práticas Angular
 * Este arquivo contém interfaces e tipos reutilizáveis em todo o projeto
 */

// Tipos base para componentes
export type ComponentSize = 'small' | 'medium' | 'large';
export type ComponentColor = 'primary' | 'accent' | 'warn' | 'success' | 'info';
export type ThemeMode = 'light' | 'dark' | 'auto';

// Tipos para formulários
export interface FormFieldConfig {
  name: string;
  label: string;
  type: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url' | 'textarea' | 'select' | 'checkbox' | 'radio' | 'date' | 'datetime-local';
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  readonly?: boolean;
  min?: number;
  max?: number;
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  options?: Array<{value: string | number | boolean; label: string; disabled?: boolean}>;
  validationMessages?: Record<string, string>;
  asyncValidators?: string[];
}

export interface FormConfig {
  fields: FormFieldConfig[];
  submitButtonText?: string;
  cancelButtonText?: string;
  showCancelButton?: boolean;
  validateOnSubmit?: boolean;
  validateOnBlur?: boolean;
  validateOnChange?: boolean;
}

// Tipos para notificações
export interface NotificationConfig {
  id?: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title?: string;
  message: string;
  duration?: number;
  persistent?: boolean;
  actions?: NotificationAction[];
  position?: 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';
  showCloseButton?: boolean;
  icon?: string;
}

export interface NotificationAction {
  label: string;
  action: () => void;
  type?: 'primary' | 'secondary' | 'danger';
}

// Tipos para modais e diálogos
export interface ModalConfig {
  title?: string;
  message?: string;
  size?: ComponentSize;
  showCloseButton?: boolean;
  backdrop?: boolean | 'static';
  keyboard?: boolean;
  centered?: boolean;
  scrollable?: boolean;
  fullscreen?: boolean;
}

export interface ConfirmDialogConfig extends ModalConfig {
  confirmButtonText?: string;
  cancelButtonText?: string;
  confirmButtonType?: ComponentColor;
  icon?: string;
  dangerMode?: boolean;
}

// Tipos para loading e estados
export interface LoadingState {
  isLoading: boolean;
  message?: string;
  subMessage?: string;
  progress?: number;
  showProgress?: boolean;
  cancellable?: boolean;
}

export interface ErrorState {
  hasError: boolean;
  message?: string;
  title?: string;
  code?: string | number;
  details?: unknown;
  retryable?: boolean;
  actions?: ErrorAction[];
}

export interface ErrorAction {
  label: string;
  action: () => void;
  type?: 'primary' | 'secondary' | 'danger';
  icon?: string;
}

// Tipos para paginação
export interface PaginationConfig {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
  hasNext: boolean;
  hasPrevious: boolean;
  showSizeOptions?: boolean;
  sizeOptions?: number[];
  showInfo?: boolean;
}

export interface PaginationState extends PaginationConfig {
  loading?: boolean;
  error?: string;
}

// Tipos para ordenação
export interface SortConfig {
  field: string;
  direction: 'asc' | 'desc';
  multi?: boolean;
}

// Tipos para filtros
export interface FilterConfig {
  field: string;
  operator: 'equals' | 'contains' | 'startsWith' | 'endsWith' | 'greaterThan' | 'lessThan' | 'between' | 'in';
  value: any;
  label?: string;
  type?: 'text' | 'number' | 'date' | 'select' | 'multiselect';
  options?: Array<{value: any; label: string}>;
}

// Tipos para APIs e serviços
export interface ApiResponse<T = any> {
  data: T;
  success: boolean;
  message?: string;
  errors?: string[];
  timestamp: string;
  requestId?: string;
}

export interface ApiError {
  message: string;
  code?: string;
  details?: any;
  timestamp: string;
  requestId?: string;
  statusCode?: number;
}

export interface ApiRequestConfig {
  timeout?: number;
  retries?: number;
  retryDelay?: number;
  cache?: boolean | number;
  headers?: Record<string, string>;
  params?: Record<string, any>;
}

// Tipos para autenticação
export interface AuthUser {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  roles: string[];
  permissions: string[];
  metadata?: Record<string, any>;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: AuthUser | null;
  token: string | null;
  refreshToken: string | null;
  expiresAt: number | null;
}

// Tipos para temas e estilos
export interface ThemeConfig {
  mode: ThemeMode;
  primaryColor: string;
  accentColor: string;
  backgroundColor: string;
  textColor: string;
  borderRadius: ComponentSize;
  fontSize: ComponentSize;
}

// Tipos para analytics e métricas
export interface MetricData {
  timestamp: number;
  value: number;
  label?: string;
  metadata?: Record<string, any>;
}

export interface ChartData {
  labels: string[];
  datasets: ChartDataset[];
}

export interface ChartDataset {
  label: string;
  data: number[];
  backgroundColor?: string | string[];
  borderColor?: string | string[];
  borderWidth?: number;
  fill?: boolean;
  tension?: number;
}

// Tipos para componentes de formulário avançados
export interface SelectOption {
  value: any;
  label: string;
  disabled?: boolean;
  description?: string;
  icon?: string;
  group?: string;
}

export interface AutoCompleteConfig {
  minLength?: number;
  debounceTime?: number;
  placeholder?: string;
  multiple?: boolean;
  showClear?: boolean;
  forceSelection?: boolean;
  emptyMessage?: string;
}

// Tipos para drag and drop
export interface DragDropConfig {
  disabled?: boolean;
  dragHandle?: string;
  dropZone?: string;
  dragPreview?: 'clone' | 'native';
  dragData?: any;
}

// Tipos para componentes de layout
export interface LayoutConfig {
  header?: boolean;
  sidebar?: boolean;
  footer?: boolean;
  breadcrumbs?: boolean;
  themeToggle?: boolean;
  responsive?: boolean;
}

// Tipos para componentes de navegação
export interface NavigationItem {
  id: string;
  label: string;
  icon?: string;
  route?: string;
  external?: boolean;
  children?: NavigationItem[];
  permissions?: string[];
  roles?: string[];
  badge?: string | number;
  badgeColor?: ComponentColor;
  active?: boolean;
  disabled?: boolean;
  separator?: boolean;
}

// Tipos para componentes de tabela
export interface TableColumn {
  field: string;
  header: string;
  type?: 'text' | 'number' | 'date' | 'boolean' | 'currency' | 'percent' | 'badge' | 'actions';
  sortable?: boolean;
  filterable?: boolean;
  width?: string;
  align?: 'left' | 'center' | 'right';
  formatter?: (value: any, row: any) => string;
  template?: string;
  sticky?: boolean;
  hidden?: boolean;
}

export interface TableConfig {
  columns: TableColumn[];
  paginated?: boolean;
  sortable?: boolean;
  filterable?: boolean;
  selectable?: boolean;
  expandable?: boolean;
  actions?: TableAction[];
  emptyMessage?: string;
  loading?: boolean;
}

export interface TableAction {
  label: string;
  icon?: string;
  action: (row: any) => void;
  type?: ComponentColor;
  disabled?: (row: any) => boolean;
  visible?: (row: any) => boolean;
}

// Tipos para componentes de upload
export interface UploadConfig {
  multiple?: boolean;
  accept?: string;
  maxFileSize?: number;
  maxFiles?: number;
  showUploadList?: boolean;
  showPreview?: boolean;
  directory?: boolean;
  drag?: boolean;
  disabled?: boolean;
}

export interface UploadFile {
  uid: string;
  name: string;
  size: number;
  type: string;
  originFileObj?: File;
  percent?: number;
  status?: 'uploading' | 'success' | 'error' | 'removed';
  response?: any;
  error?: any;
}

// Tipos para componentes de chat
export interface ChatMessage {
  id?: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: Date;
  metadata?: Record<string, any>;
  attachments?: ChatAttachment[];
  citations?: ChatCitation[];
}

export interface ChatAttachment {
  id: string;
  name: string;
  type: string;
  size: number;
  url?: string;
  metadata?: Record<string, any>;
}

export interface ChatCitation {
  id: string;
  title: string;
  content: string;
  source: string;
  page?: number;
  metadata?: Record<string, any>;
}

// Tipos para componentes de voz
export interface VoiceConfig {
  language?: string;
  continuous?: boolean;
  interimResults?: boolean;
  maxAlternatives?: number;
  grammars?: any; // SpeechGrammarList - tipo não disponível em todos os navegadores
}

// Tipos para componentes de notificação em tempo real
export interface RealTimeNotification {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success';
  title: string;
  message: string;
  timestamp: Date;
  read: boolean;
  persistent?: boolean;
  actions?: NotificationAction[];
  metadata?: Record<string, any>;
}

// Tipos para componentes de dashboard
export interface DashboardWidget {
  id: string;
  type: 'metric' | 'chart' | 'table' | 'list' | 'card';
  title: string;
  size?: 'small' | 'medium' | 'large' | 'full';
  data?: any;
  config?: any;
  refreshInterval?: number;
  permissions?: string[];
}

// Tipos para componentes de configuração
export interface SettingsSection {
  id: string;
  title: string;
  description?: string;
  icon?: string;
  items: SettingsItem[];
}

export interface SettingsItem {
  id: string;
  label: string;
  type: 'text' | 'number' | 'boolean' | 'select' | 'multiselect' | 'color' | 'file';
  value: any;
  description?: string;
  options?: SelectOption[];
  validation?: any;
  disabled?: boolean;
  dependsOn?: string;
}

// Utility types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type Nullable<T> = T | null;

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;

export type RequiredKeys<T> = {
  [K in keyof T]-?: undefined extends T[K] ? never : K;
}[keyof T];

export type OptionalKeys<T> = {
  [K in keyof T]-?: undefined extends T[K] ? K : never;
}[keyof T];

// Tipos para estados de loading
export interface LoadingState {
  isLoading: boolean
  message?: string
  progress?: number
  timestamp: number
  completedAt?: number
  global?: boolean
  http?: boolean
}

export interface LoadingConfig {
  message?: string
  progress?: number
  global?: boolean
  http?: boolean
}

export interface LoadingOptions {
  showSpinner?: boolean
  showMessage?: boolean
  overlay?: boolean
  delay?: number
  minDuration?: number
}
</file>

<file path="app/core/types/index.ts">
export * from './angular.types';
export * from './speech.types';
export * from './janus-gateway.types';
</file>

<file path="app/core/types/janus-gateway.types.ts">
export interface JanusInitOptions {
    debug?: boolean | 'all' | string[];
    callback?: () => void;
    dependencies?: Record<string, unknown>;
}

export interface JanusOptions {
    server: string | string[];
    iceServers?: RTCIceServer[];
    ipv6?: boolean;
    withCredentials?: boolean;
    max_poll_events?: number;
    destroyOnUnload?: boolean;
    token?: string;
    apisecret?: string;
    success?: () => void;
    error?: (error: unknown) => void;
    destroyed?: () => void;
}

export interface JanusPluginMessage {
    message: Record<string, unknown>;
    jsep?: JanusJsep;
    success?: (data?: unknown) => void;
    error?: (error: unknown) => void;
    [key: string]: unknown;
}

export interface JanusJsep {
    type: string;
    sdp: string;
}

export interface JanusOfferParams {
    media?: {
        audioSend?: boolean;
        audioRecv?: boolean;
        videoSend?: boolean;
        videoRecv?: boolean;
        audio?: boolean | { deviceId: string };
        video?: boolean | { deviceId: string } | 'lowres' | 'hires' | 'stdres';
        data?: boolean;
        failIfNoAudio?: boolean;
        failIfNoVideo?: boolean;
        screenshareFrameRate?: number;
    };
    success?: (jsep: JanusJsep) => void;
    error?: (error: unknown) => void;
    customizeSdp?: (jsep: JanusJsep) => void;
}

export interface JanusAnswerParams {
    jsep: JanusJsep;
    media?: {
        audioSend?: boolean;
        audioRecv?: boolean;
        videoSend?: boolean;
        videoRecv?: boolean;
        audio?: boolean | { deviceId: string };
        video?: boolean | { deviceId: string } | 'lowres' | 'hires' | 'stdres';
        data?: boolean;
        failIfNoAudio?: boolean;
        failIfNoVideo?: boolean;
    };
    success?: (jsep: JanusJsep) => void;
    error?: (error: unknown) => void;
}

export interface JanusDataParams {
    text: string;
    success?: () => void;
    error?: (error: unknown) => void;
}

export interface JanusAttachOptions {
    plugin: string;
    opaqueId?: string;
    success?: (pluginHandle: JanusPluginHandle) => void;
    error?: (error: unknown) => void;
    consentDialog?: (on: boolean) => void;
    webrtcState?: (isConnected: boolean) => void;
    iceState?: (state: 'connected' | 'failed' | 'disconnected' | 'closed') => void;
    mediaState?: (medium: 'audio' | 'video', on: boolean) => void;
    slowLink?: (uplink: boolean, lost: number, mid: string) => void;
    onmessage?: (message: Record<string, unknown>, jsep?: JanusJsep) => void;
    onlocalstream?: (stream: MediaStream) => void;
    onremotestream?: (stream: MediaStream) => void;
    ondataopen?: (label: string) => void;
    oncleanup?: () => void;
    detached?: () => void;
}

export interface JanusPluginHandle {
    getId(): string;
    getPlugin(): string;
    send(parameters: JanusPluginMessage): void;
    createOffer(callbacks: JanusOfferParams): void;
    createAnswer(callbacks: JanusAnswerParams): void;
    handleRemoteJsep(callbacks: { jsep: JanusJsep }): void;
    dtmf(parameters: { tones: string; duration?: number; gap?: number }): void;
    data(parameters: JanusDataParams): void;
    isAudioMuted(): boolean;
    muteAudio(): void;
    unmuteAudio(): void;
    isVideoMuted(): boolean;
    muteVideo(): void;
    unmuteVideo(): void;
    getBitrate(): string;
    hangup(sendRequest?: boolean): void;
    detach(parameters?: { success?: () => void; error?: (error: unknown) => void }): void;
}

export interface JanusStatic {
    init(options: JanusInitOptions): void;
    isWebrtcSupported(): boolean;
    debug(...args: unknown[]): void;
    log(...args: unknown[]): void;
    warn(...args: unknown[]): void;
    error(...args: unknown[]): void;
    randomString(length: number): string;
    attachMediaStream(element: HTMLMediaElement, stream: MediaStream): void;
    new (options: JanusOptions): JanusSession;
}

export interface JanusSession {
    getServer(): string;
    isConnected(): boolean;
    getSessionId(): string;
    attach(options: JanusAttachOptions): void;
    destroy(parameters?: { success?: () => void; error?: (error: unknown) => void }): void;
}
</file>

<file path="app/core/types/speech.types.ts">
export interface SpeechRecognition extends EventTarget {
    continuous: boolean;
    interimResults: boolean;
    lang: string;
    start(): void;
    stop(): void;
    abort(): void;
    onresult: (event: SpeechRecognitionEvent) => void;
    onerror: (event: SpeechRecognitionErrorEvent) => void;
    onend: () => void;
    onstart: () => void;
}

export interface SpeechRecognitionEvent {
    results: SpeechRecognitionResultList;
    resultIndex: number;
}

export interface SpeechRecognitionResultList {
    length: number;
    item(index: number): SpeechRecognitionResult;
    [index: number]: SpeechRecognitionResult;
}

export interface SpeechRecognitionResult {
    isFinal: boolean;
    length: number;
    item(index: number): SpeechRecognitionAlternative;
    [index: number]: SpeechRecognitionAlternative;
}

export interface SpeechRecognitionAlternative {
    transcript: string;
    confidence: number;
}

export interface SpeechRecognitionErrorEvent extends Event {
    error: string;
    message: string;
}

// Window augmentation
declare global {
    interface Window {
        SpeechRecognition: {
            new(): SpeechRecognition;
        };
        webkitSpeechRecognition: {
            new(): SpeechRecognition;
        };
    }
}
</file>

<file path="app/core/core-module.ts">
import {NgModule} from '@angular/core';
import {CommonModule} from '@angular/common';

import {CoreRoutingModule} from './core-routing-module';


@NgModule({
  declarations: [],
  imports: [
    CommonModule,
    CoreRoutingModule
  ]
})
export class CoreModule {
}
</file>

<file path="app/core/core-routing-module.ts">
import {NgModule} from '@angular/core';
import {RouterModule, Routes} from '@angular/router';

const routes: Routes = [];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class CoreRoutingModule {
}
</file>

<file path="app/core/README.md">
# Core

Serviços e utilitários centrais da aplicação.

Sugestões de conteúdo:
- Configuração de interceptors HTTP
- Serviços de autenticação/autorização
- Gerenciamento de estado global (se aplicável)
- Inicialização de app (tokens, configuração)
</file>

<file path="app/features/admin/autonomia/admin-autonomia.html">
<section class="admin-autonomia-page">
  <app-header></app-header>

  <div class="shell">
    <header class="hero">
      <div>
        <p class="eyebrow">ADMIN</p>
        <h1>Autonomia Interna</h1>
        <p class="sub">
          Backlog interno, autoestudo incremental e perguntas naturais sobre o codigo com citacoes.
        </p>
      </div>
      <div class="hero-actions">
        <ui-badge variant="info">RBAC: admin</ui-badge>
        <button ui-button variant="ghost" size="lg" (click)="refreshAll()" [disabled]="loading() || syncing() || runningStudy()">
          Atualizar
        </button>
      </div>
    </header>

    @if (error()) {
      <div class="inline-alert" role="alert">{{ error() }}</div>
    }
    @if (notice()) {
      <div class="inline-success" role="status">{{ notice() }}</div>
    }

    <section class="card">
      <div class="card-head">
        <h2>Backlog</h2>
        <div class="row-actions">
          <ui-badge variant="neutral">{{ totalTasks() }} tasks</ui-badge>
          <button ui-button variant="default" size="sm" (click)="syncBacklog()" [disabled]="syncing()">
            {{ syncing() ? 'Sincronizando...' : 'Sincronizar backlog' }}
          </button>
        </div>
      </div>

      @if (!board().length) {
        <p class="muted">Nenhum item de backlog encontrado.</p>
      } @else {
        <div class="board-list">
          @for (type of board(); track type.sprint_type.id) {
            <article class="bucket">
              <div class="bucket-head">
                <h3>{{ type.sprint_type.name }}</h3>
                <ui-badge variant="neutral">{{ type.sprints.length }} sprints</ui-badge>
              </div>
              @for (sprint of type.sprints; track sprint.id) {
                <div class="sprint-block">
                  <div class="sprint-head">
                    <strong>{{ sprint.name }}</strong>
                    <ui-badge variant="neutral">{{ sprint.tasks.length }} tasks</ui-badge>
                  </div>
                  @if (!sprint.tasks.length) {
                    <p class="muted">Sem tasks.</p>
                  } @else {
                    <div class="tasks">
                      @for (task of sprint.tasks; track task.id) {
                        <article class="task-row">
                          <div>
                            <p class="task-title">{{ task.title }}</p>
                            <p class="muted">{{ task.description }}</p>
                          </div>
                          <div class="task-metrics">
                            <span class="chip">status: {{ task.status }}</span>
                            <span class="chip">prio: {{ task.priority }}</span>
                            @if (task.area) {
                              <span class="chip">area: {{ task.area }}</span>
                            }
                            @if (task.severity) {
                              <span class="chip">sev: {{ task.severity }}</span>
                            }
                          </div>
                        </article>
                      }
                    </div>
                  }
                </div>
              }
            </article>
          }
        </div>
      }
    </section>

    <section class="card">
      <div class="card-head">
        <h2>Autoestudo</h2>
        <div class="row-actions">
          <button ui-button variant="ghost" size="sm" (click)="runStudy('incremental')" [disabled]="runningStudy()">
            Reestudar incremental
          </button>
          <button ui-button variant="ghost" size="sm" (click)="runStudy('full')" [disabled]="runningStudy()">
            Reestudar full
          </button>
        </div>
      </div>

      <div class="study-status">
        <p><strong>Ultimo commit estudado:</strong> {{ selfStudyStatus()?.last_studied_commit || 'n/a' }}</p>
        <p><strong>Ultimo sucesso:</strong> {{ selfStudyStatus()?.last_success_at || 'n/a' }}</p>
        <p><strong>Run em andamento:</strong> {{ selfStudyStatus()?.running ? ('#' + selfStudyStatus()?.running?.id + ' - ' + selfStudyStatus()?.running?.status) : 'nao' }}</p>
        @if (selfStudyStatus()?.running) {
          <p class="study-progress">
            <strong>Progresso:</strong>
            arquivo {{ selfStudyStatus()?.running?.current_file_index || ((selfStudyStatus()?.running?.files_processed || 0) + 1) }}/{{ selfStudyStatus()?.running?.files_total || '?' }}
          </p>
          <p class="study-current-file">
            <strong>Arquivo atual:</strong>
            <span class="mono">{{ selfStudyStatus()?.running?.current_file_path || 'aguardando...' }}</span>
          </p>
        }
      </div>

      @if (!selfStudyRuns().length) {
        <p class="muted">Sem historico de runs.</p>
      } @else {
        <div class="runs">
          @for (run of selfStudyRuns(); track run.id) {
            <article class="run-row">
              <div class="run-head">
                <strong>#{{ run.id }} - {{ run.mode }} - {{ run.status }}</strong>
                <span class="muted">{{ run.files_processed }}/{{ run.files_total }} arquivos</span>
              </div>
              <p class="muted">trigger: {{ run.trigger_type }} · commit: {{ run.base_commit || 'n/a' }} -> {{ run.target_commit || 'n/a' }}</p>
              @if (run.error) {
                <p class="error-text">{{ run.error }}</p>
              }
            </article>
          }
        </div>
      }
    </section>

    <section class="card">
      <div class="card-head">
        <h2>Pergunte ao Codigo</h2>
      </div>
      <textarea
        class="question-input"
        rows="4"
        placeholder="Ex: Onde o Janus dispara autoestudo quando uma task e concluida?"
        [value]="question()"
        (input)="onQuestionChange($any($event.target).value)"
      ></textarea>
      <div class="row-actions">
        <button ui-button variant="default" size="sm" (click)="askCode()" [disabled]="asking() || !question().trim()">
          {{ asking() ? 'Consultando...' : 'Perguntar' }}
        </button>
      </div>

      @if (answer()) {
        <div class="qa-answer">
          <h3>Resposta</h3>
          <p>{{ answer() }}</p>
        </div>
      }

      @if (citations().length) {
        <div class="qa-citations">
          <h3>Citacoes</h3>
          <ul>
            @for (citation of citations(); track $index) {
              <li>
                {{ citation.file_path || citation.title || citation.url || 'citacao' }}
                @if (citation.line) { :{{ citation.line }} }
              </li>
            }
          </ul>
        </div>
      }

      @if (selfMemory().length) {
        <div class="qa-memory">
          <h3>SelfMemory recente</h3>
          <ul>
            @for (memory of selfMemory(); track $index) {
              <li>
                <strong>{{ memory.file_path || 'arquivo' }}</strong>
                <p class="muted">{{ memory.summary || '' }}</p>
              </li>
            }
          </ul>
        </div>
      }
    </section>
  </div>
</section>
</file>

<file path="app/features/admin/autonomia/admin-autonomia.scss">
@use 'styles/tokens' as *;
@use 'styles/mixins' as *;

.admin-autonomia-page {
  min-height: calc(100vh - 64px);
  display: flex;
  flex-direction: column;
  gap: 24px;
  padding-bottom: 80px;
}

.shell {
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: clamp(18px, 3vw, 36px);
}

.hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.eyebrow {
  font-family: $font-mono;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.28em;
  color: $color-text-muted;
}

.sub {
  color: $color-text-secondary;
}

.hero-actions,
.row-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
}

.card {
  @include glass-panel;
  border-radius: var(--janus-radius-lg);
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.inline-alert,
.inline-success {
  border-radius: 10px;
  padding: 10px 12px;
  font-size: 0.9rem;
}

.inline-alert {
  border: 1px solid rgba(var(--error-rgb), 0.55);
  color: rgba(var(--error-rgb), 1);
  background: rgba(var(--error-rgb), 0.08);
}

.inline-success {
  border: 1px solid rgba(var(--success-rgb), 0.45);
  color: rgba(var(--success-rgb), 1);
  background: rgba(var(--success-rgb), 0.08);
}

.muted {
  color: $color-text-muted;
  font-size: 0.84rem;
}

.board-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.bucket {
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 12px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bucket-head,
.sprint-head,
.run-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.sprint-block {
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: 10px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tasks {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.task-row {
  padding: 10px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.05);
  background: rgba(255, 255, 255, 0.02);
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.task-title {
  margin: 0;
  font-family: $font-display;
  color: $color-text-primary;
}

.task-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  border: 1px solid rgba(var(--janus-secondary-rgb), 0.28);
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 0.72rem;
  font-family: $font-mono;
  color: $color-text-secondary;
}

.study-status {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
}

.study-progress,
.study-current-file {
  margin: 0;
}

.mono {
  font-family: $font-mono;
  word-break: break-all;
}

.runs {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.run-row {
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 10px;
  padding: 10px;
}

.error-text {
  color: rgba(var(--error-rgb), 1);
  font-size: 0.82rem;
}

.question-input {
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(var(--janus-bg-dark-rgb), 0.34);
  color: $color-text-primary;
  border-radius: 10px;
  padding: 10px;
  resize: vertical;
}

.qa-answer,
.qa-citations,
.qa-memory {
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  padding-top: 10px;
}

@media (max-width: 768px) {
  .study-status {
    grid-template-columns: 1fr;
  }
}
</file>

<file path="app/features/admin/autonomia/admin-autonomia.ts">
import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core'
import { CommonModule } from '@angular/common'
import { catchError, finalize, of } from 'rxjs'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'

import {
  AdminBacklogSprintType,
  AdminCodeQaResponse,
  BackendApiService,
  Citation,
  SelfStudyRun,
  SelfStudyStatusResponse
} from '../../../services/backend-api.service'
import { Header } from '../../../core/layout/header/header'
import { UiBadgeComponent } from '../../../shared/components/ui/ui-badge/ui-badge.component'
import { UiButtonComponent } from '../../../shared/components/ui/button/button.component'

@Component({
  selector: 'app-admin-autonomia',
  standalone: true,
  imports: [CommonModule, Header, UiBadgeComponent, UiButtonComponent],
  templateUrl: './admin-autonomia.html',
  styleUrls: ['./admin-autonomia.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class AdminAutonomiaComponent {
  private readonly api = inject(BackendApiService)
  private readonly destroyRef = inject(DestroyRef)
  private selfStudyPollTimer: ReturnType<typeof setInterval> | null = null
  private readonly selfStudyPollIntervalMs = 1500

  readonly loading = signal(true)
  readonly syncing = signal(false)
  readonly runningStudy = signal(false)
  readonly asking = signal(false)
  readonly error = signal('')
  readonly notice = signal('')

  readonly board = signal<AdminBacklogSprintType[]>([])
  readonly selfStudyStatus = signal<SelfStudyStatusResponse | null>(null)
  readonly selfStudyRuns = signal<SelfStudyRun[]>([])

  readonly question = signal('')
  readonly answer = signal('')
  readonly citations = signal<Citation[]>([])
  readonly selfMemory = signal<Array<{ file_path?: string; summary?: string; updated_at?: string | number }>>([])

  readonly totalTasks = computed(() =>
    this.board().reduce(
      (acc, type) => acc + type.sprints.reduce((inner, sprint) => inner + (sprint.tasks?.length || 0), 0),
      0
    )
  )

  constructor() {
    this.destroyRef.onDestroy(() => this.stopSelfStudyPolling())
    this.refreshAll()
  }

  refreshAll() {
    this.loading.set(true)
    this.error.set('')
    this.notice.set('')
    this.refreshBoard()
    this.refreshSelfStudy()
  }

  refreshBoard() {
    this.api.getAutonomyAdminBoard({ limit: 400 })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((err) => {
          this.error.set(this.extractErrorMessage(err, 'Falha ao carregar board de backlog.'))
          return of({ items: [] as AdminBacklogSprintType[] })
        }),
        finalize(() => this.loading.set(false))
      )
      .subscribe((resp) => this.board.set(resp.items || []))
  }

  refreshSelfStudy() {
    this.refreshSelfStudyStatus()
    this.api.listAutonomyAdminSelfStudyRuns(20)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((err) => {
          this.error.set(this.extractErrorMessage(err, 'Falha ao carregar historico de autoestudo.'))
          return of({ items: [] as SelfStudyRun[] })
        })
      )
      .subscribe((resp) => this.selfStudyRuns.set(resp.items || []))
  }

  private refreshSelfStudyStatus() {
    this.api.getAutonomyAdminSelfStudyStatus()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((err) => {
          this.error.set(this.extractErrorMessage(err, 'Falha ao carregar status de autoestudo.'))
          return of({ recent_runs: [] } as SelfStudyStatusResponse)
        })
      )
      .subscribe((status) => {
        const wasRunning = Boolean(this.selfStudyStatus()?.running)
        const isRunning = Boolean(status.running)
        this.selfStudyStatus.set(status)
        if (isRunning) {
          this.startSelfStudyPolling()
        } else {
          this.stopSelfStudyPolling()
          if (wasRunning) {
            this.refreshSelfStudyRuns()
          }
        }
      })
  }

  private refreshSelfStudyRuns() {
    this.api.listAutonomyAdminSelfStudyRuns(20)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((err) => {
          this.error.set(this.extractErrorMessage(err, 'Falha ao carregar historico de autoestudo.'))
          return of({ items: [] as SelfStudyRun[] })
        })
      )
      .subscribe((resp) => this.selfStudyRuns.set(resp.items || []))
  }

  private startSelfStudyPolling() {
    if (this.selfStudyPollTimer) return
    this.selfStudyPollTimer = setInterval(() => this.refreshSelfStudyStatus(), this.selfStudyPollIntervalMs)
  }

  private stopSelfStudyPolling() {
    if (!this.selfStudyPollTimer) return
    clearInterval(this.selfStudyPollTimer)
    this.selfStudyPollTimer = null
  }

  syncBacklog() {
    if (this.syncing()) return
    this.syncing.set(true)
    this.error.set('')
    this.notice.set('')
    this.api.syncAutonomyAdminBacklog()
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.syncing.set(false)),
        catchError((err) => {
          this.error.set(this.extractErrorMessage(err, 'Falha ao sincronizar backlog.'))
          return of(null)
        })
      )
      .subscribe((resp) => {
        if (!resp) return
        this.notice.set(
          `Backlog sincronizado: ${resp.created} criadas, ${resp.deduped} deduplicadas, ${resp.closed} fechadas.`
        )
        this.refreshBoard()
      })
  }

  runStudy(mode: 'incremental' | 'full') {
    if (this.runningStudy()) return
    this.runningStudy.set(true)
    this.error.set('')
    this.notice.set('')
    this.api.runAutonomyAdminSelfStudy({
      mode,
      reason: `admin_panel_${mode}`
    })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.runningStudy.set(false)),
        catchError((err) => {
          this.error.set(this.extractErrorMessage(err, 'Falha ao iniciar autoestudo.'))
          return of(null)
        })
      )
      .subscribe((resp) => {
        if (!resp) return
        this.notice.set(`Autoestudo iniciado (run #${resp.run_id}).`)
        this.refreshSelfStudy()
      })
  }

  onQuestionChange(value: string) {
    this.question.set(String(value || ''))
  }

  askCode() {
    if (this.asking()) return
    const question = this.question().trim()
    if (!question) return
    this.asking.set(true)
    this.error.set('')
    this.notice.set('')
    this.api.askAutonomyAdminCodeQa({
      question,
      limit: 12,
      citation_limit: 8
    })
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        finalize(() => this.asking.set(false)),
        catchError((err) => {
          this.error.set(this.extractErrorMessage(err, 'Falha ao consultar codigo.'))
          return of({ answer: '', citations: [], self_memory: [] } as AdminCodeQaResponse)
        })
      )
      .subscribe((resp) => {
        this.answer.set(String(resp.answer || ''))
        this.citations.set(resp.citations || [])
        this.selfMemory.set(resp.self_memory || [])
      })
  }

  private extractErrorMessage(err: unknown, fallback: string): string {
    const detail = (err as { error?: { detail?: unknown } })?.error?.detail
    if (typeof detail === 'string' && detail.trim()) return detail.trim()
    if (typeof err === 'string' && err.trim()) return err.trim()
    return fallback
  }
}
</file>

<file path="app/features/auth/login/login.a11y.spec.ts">
import { TestBed } from '@angular/core/testing'
import { RouterTestingModule } from '@angular/router/testing'
import { AuthService } from '../../../core/auth/auth.service'
import { LoginComponent } from './login'

describe('LoginComponent A11y', () => {
  it('deve ter labels associados aos inputs', () => {
    const fixture = TestBed.configureTestingModule({
      imports: [LoginComponent, RouterTestingModule],
      providers: [
        { provide: AuthService, useValue: { loginWithPassword: () => Promise.resolve(true), loginWithProvider: () => Promise.resolve(true) } }
      ]
    }).createComponent(LoginComponent)
    fixture.detectChanges()
    const el: HTMLElement = fixture.nativeElement
    const emailLabel = el.querySelector('label[for="email"]')
    const emailInput = el.querySelector('#email')
    const passwordLabel = el.querySelector('label[for="password"]')
    const passwordInput = el.querySelector('#password')
    expect(emailLabel).toBeTruthy()
    expect(emailInput).toBeTruthy()
    expect(passwordLabel).toBeTruthy()
    expect(passwordInput).toBeTruthy()
  })
})
</file>

<file path="app/features/auth/login/login.html">
<section class="login">
  <div class="glass-panel">
    <div class="panel-glow" aria-hidden="true"></div>

    <div class="brand">
      <div class="signal-orb" aria-hidden="true">
        <span class="signal-core"></span>
        <span class="signal-ring"></span>
        <span class="signal-ring ring-two"></span>
      </div>
      <p class="eyebrow">JANUS // PORTAL SEGURO</p>
      <h1>VERIFICACAO DE ACESSO</h1>
      <p class="sub">Entrada segura para o nucleo operacional do Janus.</p>
      <div class="status-chip">
        <span class="status-dot"></span>
        CANAL CRIPTOGRAFADO ATIVO
      </div>
    </div>

    <form [formGroup]="form" (ngSubmit)="loginEmailPassword()" aria-label="Login">

      <!-- Email -->
      <div class="field">
        <label for="email">Email de acesso</label>
        <input id="email" type="email" formControlName="email" class="glass-input" placeholder="voce@janus.ai"
          [attr.aria-invalid]="form.controls.email.invalid && form.controls.email.touched" />
        @if (form.controls.email.invalid && form.controls.email.touched) {
          <div class="field-error">
            > IDENTIFICADOR INVALIDO
          </div>
        }
      </div>

      <!-- Password -->
      <div class="field">
        <label for="password">Senha de acesso</label>
        <div class="password-wrap">
          <input id="password" [type]="showPassword ? 'text' : 'password'" formControlName="password"
            class="glass-input has-toggle" placeholder="********" />
          <button type="button" class="toggle-password" (click)="togglePassword()"
            [attr.aria-pressed]="showPassword">
            {{ showPassword ? 'OCULTAR' : 'MOSTRAR' }}
          </button>
        </div>
        @if (form.controls.password.invalid && form.controls.password.touched) {
          <div class="field-error">
            > MINIMO 6 CARACTERES
          </div>
        }
      </div>

      <!-- Extras -->
      <div class="extras">
        <label class="remember">
          <input type="checkbox" formControlName="remember" />
          <span>Manter sessao</span>
        </label>
        <button type="button" class="recover" (click)="recoverAccess()">Recuperar acesso</button>
      </div>

      <!-- Submit -->
      <button class="glass-button primary" type="submit" [disabled]="form.invalid || loading">
        <span>{{ loading ? 'ENTRANDO...' : 'ENTRAR NO JANUS' }}</span>
        @if (!loading) {
          <span class="material-icons">login</span>
        }
      </button>

      <!-- SSO Alt -->
      <div class="sso">
        <button type="button" class="glass-button secondary" (click)="loginWithGoogle()" [disabled]="loading">
          Entrar com Google
        </button>
        <button type="button" class="glass-button secondary" (click)="loginWithGithub()" [disabled]="loading">
          Entrar com GitHub
        </button>
      </div>

      <!-- Sign Up -->
      <div class="signup">
        <span>Sem credenciais?</span>
        <a routerLink="/registro">Criar conta</a>
      </div>

      @if (error) {
        <div class="error-box">
          > {{ error }}
          @if (showRecoveryHint) {
            <div class="error-action">
              <button type="button" class="recover-inline" (click)="recoverAccess()">Guiar recuperacao</button>
            </div>
          }
        </div>
      }
      @if (notice) {
        <div class="notice-box">
          > {{ notice }}
        </div>
      }

      @if (showResetGuide) {
        <div class="notice-box">
          <p><strong>Fluxo guiado de redefinicao</strong></p>
          <p>1) Solicite a recuperacao acima. 2) Cole o token. 3) Defina sua nova senha.</p>

          <div class="field">
            <label for="resetToken">Token de recuperacao</label>
            <input
              id="resetToken"
              type="text"
              class="glass-input"
              placeholder="Cole o token recebido"
              [(ngModel)]="resetToken"
              name="resetToken"
            />
          </div>

          <div class="field">
            <label for="newPassword">Nova senha</label>
            <input
              id="newPassword"
              type="password"
              class="glass-input"
              placeholder="Minimo 8 caracteres"
              [(ngModel)]="newPassword"
              name="newPassword"
            />
          </div>

          <div class="field">
            <label for="confirmPassword">Confirmar nova senha</label>
            <input
              id="confirmPassword"
              type="password"
              class="glass-input"
              placeholder="Repita a nova senha"
              [(ngModel)]="confirmPassword"
              name="confirmPassword"
            />
          </div>

          <button type="button" class="glass-button secondary" (click)="submitResetPassword()" [disabled]="loading">
            Confirmar redefinicao
          </button>
        </div>
      }
    </form>
  </div>
</section>
</file>

<file path="app/features/auth/login/login.scss">
@use 'styles/tokens' as *;

:host {
    display: block;
    --login-bg: #0a0f13;
    --login-panel: rgba(13, 18, 22, 0.86);
    --login-accent: #23d5a1;
    --login-accent-strong: #10b981;
    --login-cool: #45c3ff;
    --login-warm: #f6b348;
    --login-text: #eaf2f8;
    --login-muted: #8ea2b0;
    --login-stroke: rgba(255, 255, 255, 0.1);
    --login-shadow: 0 30px 80px rgba(0, 0, 0, 0.55);
}

.login {
    min-height: 100vh;
    padding: clamp(2rem, 4vw, 4rem) 1.5rem;
    display: grid;
    place-items: center;
    background:
        radial-gradient(circle at 15% 20%, rgba(35, 213, 161, 0.18), transparent 45%),
        radial-gradient(circle at 80% 10%, rgba(69, 195, 255, 0.18), transparent 40%),
        radial-gradient(circle at 20% 85%, rgba(246, 179, 72, 0.15), transparent 50%),
        var(--login-bg);
    position: relative;
    overflow: hidden;

    &::before {
        content: '';
        position: absolute;
        inset: -20%;
        background:
            linear-gradient(120deg, transparent 30%, rgba(69, 195, 255, 0.07) 50%, transparent 70%),
            linear-gradient(-40deg, transparent 30%, rgba(35, 213, 161, 0.05) 50%, transparent 70%);
        animation: drift 14s ease-in-out infinite;
        pointer-events: none;
    }

    &::after {
        content: '';
        position: absolute;
        inset: 0;
        background-image:
            linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
        background-size: 32px 32px;
        opacity: 0.35;
        pointer-events: none;
        mask-image: radial-gradient(circle at center, rgba(0, 0, 0, 1) 20%, transparent 65%);
    }
}

.glass-panel {
    position: relative;
    width: min(100%, 440px);
    padding: 2.5rem 2.25rem;
    border-radius: 24px;
    background: linear-gradient(160deg, rgba(16, 22, 28, 0.95) 0%, var(--login-panel) 100%);
    border: 1px solid var(--login-stroke);
    box-shadow: var(--login-shadow);
    overflow: hidden;
}

.panel-glow {
    position: absolute;
    inset: 0;
    background:
        radial-gradient(circle at 20% 20%, rgba(35, 213, 161, 0.22), transparent 45%),
        radial-gradient(circle at 90% 0%, rgba(69, 195, 255, 0.18), transparent 50%),
        radial-gradient(circle at 10% 90%, rgba(246, 179, 72, 0.14), transparent 50%);
    opacity: 0.8;
    pointer-events: none;
}

.brand {
    position: relative;
    z-index: 1;
    text-align: center;
    margin-bottom: 2rem;

    h1 {
        font-family: $font-display;
        font-size: clamp(1.4rem, 1rem + 1vw, 2rem);
        letter-spacing: 0.08em;
        color: var(--login-text);
        margin: 0.2rem 0 0.35rem;
        text-transform: uppercase;
    }

    .eyebrow {
        font-family: $font-mono;
        font-size: 0.7rem;
        letter-spacing: 0.24em;
        color: var(--login-muted);
        text-transform: uppercase;
        margin: 0 0 0.35rem;
    }

    .sub {
        font-family: $font-body;
        color: rgba(234, 242, 248, 0.7);
        font-size: 0.9rem;
        margin: 0.35rem auto 1rem;
        max-width: 28ch;
    }
}

.signal-orb {
    width: 64px;
    height: 64px;
    margin: 0 auto 1rem;
    position: relative;
}

.signal-core {
    position: absolute;
    inset: 22px;
    border-radius: 999px;
    background: radial-gradient(circle, #ffffff 0%, #ffffff 45%, rgba(255, 255, 255, 0) 60%);
    box-shadow: 0 0 12px rgba(255, 255, 255, 0.7);
    animation: pulse 2.8s ease-in-out infinite;
}

.signal-ring {
    position: absolute;
    inset: 0;
    border-radius: 999px;
    border: 1px solid rgba(35, 213, 161, 0.7);
    box-shadow: 0 0 12px rgba(35, 213, 161, 0.35);
    animation: orbit 6s linear infinite;

    &.ring-two {
        inset: 8px;
        border-color: rgba(69, 195, 255, 0.65);
        animation-duration: 8s;
        animation-direction: reverse;
    }
}

.status-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    font-family: $font-mono;
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--login-text);
    padding: 0.4rem 0.75rem;
    border-radius: 999px;
    background: rgba(35, 213, 161, 0.12);
    border: 1px solid rgba(35, 213, 161, 0.3);
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: var(--login-accent);
    box-shadow: 0 0 8px rgba(35, 213, 161, 0.7);
}

form {
    position: relative;
    z-index: 1;
    display: grid;
    gap: 1.25rem;
}

.field {
    display: grid;
    gap: 0.45rem;
}

label {
    font-family: $font-mono;
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--login-muted);
}

.glass-input {
    width: 100%;
    background: rgba(6, 10, 14, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 0.85rem 1rem;
    color: var(--login-text);
    font-family: $font-body;
    font-size: 0.95rem;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;

    &:focus {
        outline: none;
        border-color: rgba(35, 213, 161, 0.65);
        box-shadow: 0 0 0 3px rgba(35, 213, 161, 0.15);
    }

    &::placeholder {
        color: rgba(142, 162, 176, 0.65);
    }
}

.password-wrap {
    position: relative;
}

.glass-input.has-toggle {
    padding-right: 5rem;
}

.toggle-password {
    position: absolute;
    right: 0.85rem;
    top: 50%;
    transform: translateY(-50%);
    background: transparent;
    border: none;
    font-family: $font-mono;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--login-cool);
    cursor: pointer;
    transition: color 0.2s ease;

    &:hover {
        color: var(--login-text);
    }
}

.field-error {
    font-family: $font-mono;
    font-size: 0.7rem;
    color: #f87171;
    letter-spacing: 0.08em;
}

.extras {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.8rem;
    color: var(--login-muted);
}

.remember {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;

    input {
        accent-color: var(--login-accent);
    }
}

.recover {
    background: transparent;
    border: none;
    color: var(--login-cool);
    text-decoration: none;
    font-weight: 600;
    cursor: pointer;
    transition: color 0.2s ease;

    &:hover {
        color: var(--login-text);
    }
}

.glass-button {
    width: 100%;
    border-radius: 14px;
    padding: 0.95rem 1rem;
    font-family: $font-display;
    font-size: 0.92rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border: 1px solid transparent;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    transition: transform 0.2s ease, box-shadow 0.2s ease;

    &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
        transform: none;
    }
}

.glass-button.primary {
    background: linear-gradient(120deg, rgba(35, 213, 161, 0.95), rgba(69, 195, 255, 0.9));
    color: #02110c;
    border-color: rgba(35, 213, 161, 0.45);
    box-shadow: 0 0 20px rgba(35, 213, 161, 0.2);

    &:hover:not(:disabled) {
        transform: translateY(-1px);
        box-shadow: 0 0 24px rgba(35, 213, 161, 0.35);
    }
}

.glass-button.secondary {
    background: rgba(255, 255, 255, 0.04);
    color: var(--login-text);
    border-color: rgba(255, 255, 255, 0.12);
    font-size: 0.8rem;
    letter-spacing: 0.06em;

    &:hover:not(:disabled) {
        border-color: rgba(255, 255, 255, 0.25);
        box-shadow: 0 0 18px rgba(69, 195, 255, 0.15);
    }
}

.sso {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.75rem;
}

.signup {
    display: flex;
    justify-content: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    color: var(--login-muted);

    a {
        color: var(--login-warm);
        font-weight: 600;
        text-decoration: none;

        &:hover {
            color: var(--login-text);
        }
    }
}

.error-box {
    margin-top: 0.5rem;
    padding: 0.75rem 0.9rem;
    border-radius: 12px;
    border: 1px solid rgba(248, 113, 113, 0.35);
    background: rgba(248, 113, 113, 0.1);
    color: #fca5a5;
    font-family: $font-mono;
    font-size: 0.75rem;
    letter-spacing: 0.08em;
}

.error-action {
    margin-top: 0.6rem;
}

.recover-inline {
    background: rgba(248, 113, 113, 0.12);
    border: 1px solid rgba(248, 113, 113, 0.35);
    color: #fecaca;
    border-radius: 8px;
    padding: 0.35rem 0.65rem;
    font-family: $font-display;
    font-size: 0.7rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    cursor: pointer;
}

.notice-box {
    margin-top: 0.5rem;
    padding: 0.75rem 0.9rem;
    border-radius: 12px;
    border: 1px solid rgba(69, 195, 255, 0.35);
    background: rgba(69, 195, 255, 0.1);
    color: #93c5fd;
    font-family: $font-mono;
    font-size: 0.75rem;
    letter-spacing: 0.08em;
}

@keyframes orbit {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

@keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 0.9; }
    50% { transform: scale(1.15); opacity: 1; }
}

@keyframes drift {
    0%, 100% { transform: translate3d(0, 0, 0); }
    50% { transform: translate3d(-4%, 2%, 0); }
}

@media (max-width: 480px) {
    .glass-panel {
        padding: 2rem 1.5rem;
    }

    .status-chip {
        letter-spacing: 0.12em;
    }
}
</file>

<file path="app/features/auth/login/login.spec.ts">
import { TestBed } from '@angular/core/testing'
import { LoginComponent } from './login'
import { AuthService } from '../../../core/auth/auth.service'
import { Router } from '@angular/router'
import { RouterTestingModule } from '@angular/router/testing'
import { vi } from 'vitest'

describe('LoginComponent', () => {
  let comp: LoginComponent
  let authSpy: {
    loginWithPassword: ReturnType<typeof vi.fn>
    loginWithProvider: ReturnType<typeof vi.fn>
    requestPasswordReset: ReturnType<typeof vi.fn>
    resetPassword: ReturnType<typeof vi.fn>
  }
  let router: Router

  beforeEach(() => {
    authSpy = {
      loginWithPassword: vi.fn(),
      loginWithProvider: vi.fn(),
      requestPasswordReset: vi.fn(),
      resetPassword: vi.fn()
    }

    TestBed.configureTestingModule({
      imports: [LoginComponent, RouterTestingModule],
      providers: [{ provide: AuthService, useValue: authSpy }]
    })

    const fixture = TestBed.createComponent(LoginComponent)
    comp = fixture.componentInstance
    router = TestBed.inject(Router)
  })

  it('deve invalidar email incorreto', () => {
    comp.form.setValue({ email: 'x', password: '123456', remember: true })
    expect(comp.form.invalid).toBe(true)
  })

  it('deve alternar exibicao de senha', () => {
    expect(comp.showPassword).toBe(false)
    comp.togglePassword()
    expect(comp.showPassword).toBe(true)
  })

  it('deve logar com email/senha validos', async () => {
    comp.form.setValue({ email: 'a@b.com', password: '123456', remember: true })
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true)
    authSpy.loginWithPassword.mockResolvedValue({ ok: true })

    await comp.loginEmailPassword()

    expect(authSpy.loginWithPassword).toHaveBeenCalledWith('a@b.com', '123456', true)
    expect(navigateSpy).toHaveBeenCalledWith(['/'])
  })

  it('deve exibir hint de recuperacao em erro 401', async () => {
    comp.form.setValue({ email: 'a@b.com', password: 'bad-pass', remember: true })
    authSpy.loginWithPassword.mockResolvedValue({
      ok: false,
      statusCode: 401,
      reason: 'invalid_credentials',
      error: 'Email/usuario ou senha invalidos.'
    })

    await comp.loginEmailPassword()

    expect(comp.error).toContain('invalidos')
    expect(comp.showRecoveryHint).toBe(true)
    expect(comp.notice).toContain('Recuperar acesso')
  })
})
</file>

<file path="app/features/auth/login/login.ts">
import { ChangeDetectorRef, Component, inject } from '@angular/core'
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms'
import { FormsModule } from '@angular/forms'
import { Router } from '@angular/router'
import { RouterLink } from '@angular/router'
import { AuthService } from '../../../core/auth/auth.service'
import { AppLoggerService } from '../../../core/services/app-logger.service'

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule, FormsModule, RouterLink],
  templateUrl: './login.html',
  styleUrls: ['./login.scss']
})
export class LoginComponent {
  private fb = inject(FormBuilder)
  private auth = inject(AuthService)
  private router = inject(Router)
  private logger = inject(AppLoggerService)
  private cdr = inject(ChangeDetectorRef)
  form = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
    remember: [true]
  })
  showPassword = false
  loading = false
  error = ''
  notice = ''
  showRecoveryHint = false
  showResetGuide = false
  resetToken = ''
  newPassword = ''
  confirmPassword = ''
  attempts = 0
  lockedUntil = 0

  togglePassword() {
    this.showPassword = !this.showPassword
  }

  async loginEmailPassword() {
    if (this.loading) return
    const now = Date.now()
    if (this.lockedUntil && now < this.lockedUntil) return
    this.error = ''
    this.notice = ''
    if (this.form.invalid) { this.form.markAllAsTouched(); return }
    this.loading = true
    const v = this.form.value
    try {
      this.logger.debug('[LoginComponent] Attempting login', { email: v.email })
      const result = await this.auth.loginWithPassword(String(v.email), String(v.password), !!v.remember)
      if (result.ok) {
        this.logger.info('[LoginComponent] Login successful, navigating to home')
        // Add a small delay to ensure token is properly stored
        await new Promise(resolve => setTimeout(resolve, 100))
        await this.router.navigate(['/'])
      } else {
        this.logger.warn('[LoginComponent] Login failed', { reason: result.reason, statusCode: result.statusCode })
        this.handleFailure(result.error, result.statusCode === 401)
      }
    } catch (error) {
      this.logger.error('[LoginComponent] Login error', error)
      this.handleFailure()
    } finally {
      this.loading = false
      this.cdr.markForCheck()
    }
  }

  async loginWithGoogle() {
    if (this.loading) return
    this.loading = true
    this.error = ''
    this.notice = ''
    try {
      const ok = await this.auth.loginWithProvider('google')
      if (ok) {
        await this.router.navigateByUrl('/')
      } else {
        this.handleFailure()
      }
    } catch {
      this.handleFailure()
    } finally {
      this.loading = false
      this.cdr.markForCheck()
    }
  }

  async loginWithGithub() {
    if (this.loading) return
    this.loading = true
    this.error = ''
    this.notice = ''
    try {
      const ok = await this.auth.loginWithProvider('github')
      if (ok) {
        await this.router.navigateByUrl('/')
      } else {
        this.handleFailure()
      }
    } catch {
      this.handleFailure()
    } finally {
      this.loading = false
      this.cdr.markForCheck()
    }
  }

  handleFailure(errorMessage?: string, withRecoveryHint = false) {
    this.attempts += 1
    this.showRecoveryHint = withRecoveryHint
    if (this.attempts >= 5) {
      this.lockedUntil = Date.now() + 60_000
    }
    this.error = errorMessage || 'Falha no login. Verifique seus dados.'
    if (withRecoveryHint) {
      this.notice = 'Se voce esqueceu a senha, use Recuperar acesso para receber instrucoes.'
    }
    this.cdr.markForCheck()
  }

  async recoverAccess() {
    if (this.loading) return
    this.error = ''
    this.notice = ''
    this.showResetGuide = false
    this.resetToken = ''
    this.newPassword = ''
    this.confirmPassword = ''
    const email = String(this.form.value.email || '').trim()
    if (!email) {
      this.error = 'Informe seu email para recuperar o acesso.'
      return
    }
    this.loading = true
    try {
      const token = await this.auth.requestPasswordReset(email)
      if (token) {
        this.notice = `Token de reset: ${token}. Cole abaixo para definir uma nova senha.`
        this.resetToken = token
      } else {
        this.notice = 'Se o email existir, enviaremos instrucoes de recuperacao. Se tiver um token, use o fluxo guiado abaixo.'
      }
      this.showResetGuide = true
      this.showRecoveryHint = false
    } catch {
      this.error = 'Falha ao solicitar recuperacao.'
    } finally {
      this.loading = false
      this.cdr.markForCheck()
    }
  }

  async submitResetPassword() {
    if (this.loading) return
    this.error = ''
    this.notice = ''

    const token = this.resetToken.trim()
    const password = this.newPassword.trim()
    const confirm = this.confirmPassword.trim()

    if (!token) {
      this.error = 'Informe o token de recuperacao.'
      return
    }
    if (password.length < 8) {
      this.error = 'A nova senha deve ter no minimo 8 caracteres.'
      return
    }
    if (password !== confirm) {
      this.error = 'A confirmacao da senha nao confere.'
      return
    }

    this.loading = true
    try {
      const result = await this.auth.resetPassword(token, password)
      if (!result.ok) {
        this.error = result.error || 'Falha ao redefinir senha.'
        return
      }
      this.notice = 'Senha redefinida com sucesso. Faca login com a nova senha.'
      this.showResetGuide = false
      this.resetToken = ''
      this.newPassword = ''
      this.confirmPassword = ''
    } finally {
      this.loading = false
      this.cdr.markForCheck()
    }
  }
}
</file>

<file path="app/features/auth/register/register.html">
<section class="register">
  <div class="register-shell">
    <aside class="register-hero">
      <div class="hero-glow" aria-hidden="true"></div>
      <div class="signal-orb" aria-hidden="true">
        <span class="signal-core"></span>
        <span class="signal-ring"></span>
        <span class="signal-ring ring-two"></span>
      </div>
      <p class="eyebrow">JANUS // REGISTRO SEGURO</p>
      <h1>Criar conta</h1>
      <p class="sub">Complete o formulario para solicitar acesso e ativar seu perfil.</p>
      <div class="hero-badges">
        <span class="badge">Dados protegidos</span>
        <span class="badge outline">Validacao manual</span>
      </div>
      <ul class="hero-list">
        <li><span class="dot"></span>Analise em ate 24h apos o envio</li>
        <li><span class="dot"></span>Seguranca reforcada com dupla verificacao</li>
        <li><span class="dot"></span>Equipe dedicada para onboarding</li>
      </ul>
      <div class="hero-stats">
        <div class="stat">
          <span class="stat-label">Tempo medio</span>
          <span class="stat-value">2 min</span>
        </div>
        <div class="stat">
          <span class="stat-label">Resposta</span>
          <span class="stat-value">ate 24h</span>
        </div>
      </div>
    </aside>

    <div class="register-card">
      <div class="card-header">
        <p class="eyebrow">Formulario</p>
        <h2>Informacoes do usuario</h2>
        <p class="sub">Preencha com dados reais. Todos os campos sao obrigatorios.</p>
      </div>

      <form [formGroup]="form" (ngSubmit)="register()" aria-label="Registro">
        <div class="form-section">
          <p class="section-title">Identidade</p>
          <div class="form-grid">
            <div class="field span-2" style="--delay: 0.05s">
              <label for="username">Usuario</label>
              <input id="username" type="text" formControlName="username" class="glass-input" placeholder="seu_usuario"
                autocomplete="username" required
                [attr.aria-invalid]="form.controls.username.invalid && form.controls.username.touched" />
              @if (form.controls.username.invalid && form.controls.username.touched) {
                <div class="field-error">
                  > USUARIO INVALIDO
                </div>
              }
            </div>

            <div class="field span-2" style="--delay: 0.1s">
              <label for="fullName">Nome completo</label>
              <input id="fullName" type="text" formControlName="fullName" class="glass-input"
                placeholder="Nome completo" autocomplete="name" required
                [attr.aria-invalid]="form.controls.fullName.invalid && form.controls.fullName.touched" />
              @if (form.controls.fullName.invalid && form.controls.fullName.touched) {
                <div class="field-error">
                  > NOME OBRIGATORIO
                </div>
              }
            </div>

            <div class="field span-2" style="--delay: 0.15s">
              <label for="cpf">CPF</label>
              <input id="cpf" type="text" formControlName="cpf" class="glass-input" placeholder="000.000.000-00"
                inputmode="numeric" maxlength="14" autocomplete="off" required (input)="onCpfInput()"
                [attr.aria-invalid]="form.controls.cpf.invalid && form.controls.cpf.touched" />
              <div class="field-hint">Use apenas numeros, com ou sem pontos.</div>
              @if (form.controls.cpf.invalid && form.controls.cpf.touched) {
                <div class="field-error">
                  > CPF INVALIDO
                </div>
              }
            </div>
          </div>
        </div>

        <div class="form-section">
          <p class="section-title">Contato</p>
          <div class="form-grid">
            <div class="field span-2" style="--delay: 0.2s">
              <label for="phone">Telefone</label>
              <input id="phone" type="tel" formControlName="phone" class="glass-input" placeholder="(11) 90000-0000"
                inputmode="tel" maxlength="15" autocomplete="tel" required (input)="onPhoneInput()"
                [attr.aria-invalid]="form.controls.phone.invalid && form.controls.phone.touched" />
              <div class="field-hint">Inclua o DDD.</div>
              @if (form.controls.phone.invalid && form.controls.phone.touched) {
                <div class="field-error">
                  > TELEFONE INVALIDO
                </div>
              }
            </div>

            <div class="field span-2" style="--delay: 0.25s">
              <label for="email">Email</label>
              <input id="email" type="email" formControlName="email" class="glass-input" placeholder="voce@janus.ai"
                autocomplete="email" required
                [attr.aria-invalid]="form.controls.email.invalid && form.controls.email.touched" />
              @if (form.controls.email.invalid && form.controls.email.touched) {
                <div class="field-error">
                  > EMAIL INVALIDO
                </div>
              }
            </div>
          </div>
        </div>

        <div class="form-section">
          <p class="section-title">Seguranca</p>
          <div class="form-grid">
            <div class="field span-2" style="--delay: 0.3s">
              <label for="password">Senha</label>
              <div class="password-wrap">
                <input id="password" [type]="showPassword ? 'text' : 'password'" formControlName="password"
                  class="glass-input has-toggle" placeholder="********" autocomplete="new-password" required />
                <button type="button" class="toggle-password" (click)="togglePassword()"
                  [attr.aria-pressed]="showPassword">
                  {{ showPassword ? 'OCULTAR' : 'MOSTRAR' }}
                </button>
              </div>
              <div class="field-hint">Use letras maiusculas, minusculas, numeros e caracteres especiais.</div>
              <ul class="password-rules">
                <li [class.ok]="hasMinLength">Minimo de 8 caracteres</li>
                <li [class.ok]="hasUppercase">Pelo menos 1 letra maiuscula</li>
                <li [class.ok]="hasLowercase">Pelo menos 1 letra minuscula</li>
                <li [class.ok]="hasNumber">Pelo menos 1 numero</li>
                <li [class.ok]="hasSpecial">Pelo menos 1 caractere especial</li>
                <li [class.ok]="hasNoPersonalInfo">Nao conter dados pessoais</li>
              </ul>
              @if ((form.controls.password.invalid || form.hasError('passwordContainsPersonalInfo')) && form.controls.password.touched) {
                <div class="field-error">
                  > SENHA NAO ATENDE OS REQUISITOS
                </div>
              }
            </div>
          </div>

          <label class="remember terms">
            <input type="checkbox" formControlName="terms" required />
            <span>
              Aceito os <a href="#" class="terms-link">termos de uso</a> e a politica de privacidade
            </span>
          </label>
          @if (form.controls.terms.invalid && form.controls.terms.touched) {
            <div class="field-error">
              > ACEITE O TERMO PARA CONTINUAR
            </div>
          }
        </div>

        <button class="glass-button primary" type="submit" [disabled]="form.invalid || loading">
          <span>{{ loading ? 'ENVIANDO...' : 'CRIAR CONTA' }}</span>
          @if (!loading) {
            <span class="material-icons">person_add</span>
          }
        </button>

        <div class="signup">
          <span>Ja tem conta?</span>
          <a routerLink="/login">Entrar</a>
        </div>

        @if (success) {
          <div class="success-box">
            > {{ success }}
          </div>
        }
        @if (error) {
          <div class="error-box">
            > {{ error }}
          </div>
        }
      </form>
    </div>
  </div>
</section>
</file>

<file path="app/features/auth/register/register.scss">
@use 'styles/tokens' as *;

:host {
    display: block;
    --register-bg: #0a0f13;
    --register-panel: rgba(12, 18, 25, 0.92);
    --register-panel-strong: rgba(13, 20, 28, 0.96);
    --register-accent: #23d5a1;
    --register-accent-strong: #0fb28a;
    --register-cool: #45c3ff;
    --register-warm: #f6b348;
    --register-text: #eaf2f8;
    --register-muted: #93a2b2;
    --register-stroke: rgba(255, 255, 255, 0.08);
    --register-shadow: 0 30px 80px rgba(0, 0, 0, 0.55);
}

.register {
    min-height: 100vh;
    padding: clamp(2rem, 4vw, 4.5rem) 1.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    background:
        radial-gradient(circle at 12% 18%, rgba(35, 213, 161, 0.2), transparent 40%),
        radial-gradient(circle at 88% 10%, rgba(69, 195, 255, 0.18), transparent 45%),
        radial-gradient(circle at 20% 85%, rgba(246, 179, 72, 0.16), transparent 52%),
        var(--register-bg);
    position: relative;
    overflow: hidden;
    color: var(--register-text);

    &::before {
        content: '';
        position: absolute;
        inset: -15%;
        background:
            linear-gradient(120deg, transparent 30%, rgba(69, 195, 255, 0.1) 50%, transparent 70%),
            linear-gradient(-30deg, transparent 25%, rgba(35, 213, 161, 0.08) 50%, transparent 75%);
        animation: float 18s ease-in-out infinite;
        pointer-events: none;
        opacity: 0.8;
    }

    &::after {
        content: '';
        position: absolute;
        inset: 0;
        background-image:
            radial-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
            radial-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px);
        background-size: 40px 40px, 18px 18px;
        background-position: 0 0, 12px 8px;
        opacity: 0.35;
        pointer-events: none;
        mask-image: radial-gradient(circle at center, rgba(0, 0, 0, 1) 15%, transparent 65%);
    }
}

.register-shell {
    width: min(1120px, 100%);
    display: grid;
    grid-template-columns: minmax(0, 1.05fr) minmax(0, 1fr);
    gap: 2rem;
    position: relative;
    z-index: 1;
}

.register-hero {
    position: relative;
    padding: 2.75rem 2.5rem;
    border-radius: 28px;
    background: linear-gradient(150deg, rgba(14, 21, 29, 0.98) 0%, rgba(12, 17, 24, 0.88) 100%);
    border: 1px solid var(--register-stroke);
    box-shadow: var(--register-shadow);
    overflow: hidden;
    animation: panel-in 0.8s ease both;
}

.hero-glow {
    position: absolute;
    inset: 0;
    background:
        radial-gradient(circle at 20% 20%, rgba(35, 213, 161, 0.22), transparent 45%),
        radial-gradient(circle at 85% 0%, rgba(69, 195, 255, 0.2), transparent 50%),
        radial-gradient(circle at 10% 90%, rgba(246, 179, 72, 0.18), transparent 55%);
    opacity: 0.9;
    pointer-events: none;
}

.register-card {
    position: relative;
    padding: 2.4rem 2.25rem;
    border-radius: 24px;
    background: linear-gradient(160deg, rgba(12, 18, 26, 0.96) 0%, var(--register-panel) 100%);
    border: 1px solid var(--register-stroke);
    box-shadow: var(--register-shadow);
    backdrop-filter: blur(16px);
    animation: panel-in 0.8s ease 0.1s both;
}

.signal-orb {
    width: 66px;
    height: 66px;
    margin: 0 0 1.25rem;
    position: relative;
}

.signal-core {
    position: absolute;
    inset: 22px;
    border-radius: 999px;
    background: radial-gradient(circle, #ffffff 0%, #ffffff 45%, rgba(255, 255, 255, 0) 60%);
    box-shadow: 0 0 12px rgba(255, 255, 255, 0.7);
    animation: pulse 2.8s ease-in-out infinite;
}

.signal-ring {
    position: absolute;
    inset: 0;
    border-radius: 999px;
    border: 1px solid rgba(35, 213, 161, 0.75);
    box-shadow: 0 0 14px rgba(35, 213, 161, 0.35);
    animation: orbit 6s linear infinite;

    &.ring-two {
        inset: 8px;
        border-color: rgba(69, 195, 255, 0.7);
        animation-duration: 8s;
        animation-direction: reverse;
    }
}

.eyebrow {
    font-family: $font-mono;
    font-size: 0.7rem;
    letter-spacing: 0.24em;
    color: var(--register-muted);
    text-transform: uppercase;
    margin: 0 0 0.4rem;
}

h1 {
    font-family: $font-display;
    font-size: clamp(1.8rem, 1.1rem + 1.6vw, 2.6rem);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin: 0.2rem 0 0.4rem;
}

h2 {
    font-family: $font-display;
    font-size: clamp(1.1rem, 1rem + 0.8vw, 1.6rem);
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin: 0.2rem 0 0.4rem;
}

.sub {
    font-family: $font-body;
    font-size: 0.95rem;
    color: rgba(234, 242, 248, 0.75);
    margin: 0.4rem 0 0.8rem;
    max-width: 34ch;
}

.hero-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 0.6rem;
    margin: 1rem 0 1.5rem;
}

.badge {
    font-family: $font-mono;
    font-size: 0.68rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    padding: 0.45rem 0.85rem;
    border-radius: 999px;
    background: rgba(35, 213, 161, 0.14);
    border: 1px solid rgba(35, 213, 161, 0.35);
    color: var(--register-text);
}

.badge.outline {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(246, 179, 72, 0.4);
    color: var(--register-warm);
}

.hero-list {
    list-style: none;
    padding: 0;
    margin: 0 0 2rem;
    display: grid;
    gap: 0.75rem;
    font-size: 0.9rem;
    color: rgba(234, 242, 248, 0.75);
}

.hero-list li {
    display: flex;
    align-items: center;
    gap: 0.65rem;
}

.hero-list .dot {
    width: 10px;
    height: 10px;
    border-radius: 999px;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.9), rgba(35, 213, 161, 0.9));
    box-shadow: 0 0 12px rgba(35, 213, 161, 0.6);
    flex: 0 0 auto;
}

.hero-stats {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 1rem;
}

.stat {
    padding: 0.85rem;
    border-radius: 16px;
    background: rgba(9, 14, 20, 0.5);
    border: 1px solid rgba(255, 255, 255, 0.06);
}

.stat-label {
    font-family: $font-mono;
    font-size: 0.65rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--register-muted);
}

.stat-value {
    display: block;
    font-family: $font-display;
    font-size: 1.2rem;
    margin-top: 0.35rem;
    color: var(--register-text);
}

.card-header {
    margin-bottom: 1.5rem;
}

form {
    display: grid;
    gap: 1.5rem;
}

.form-section {
    display: grid;
    gap: 1rem;
}

.form-section + .form-section {
    margin-top: 0.5rem;
    padding-top: 1.3rem;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.section-title {
    font-family: $font-mono;
    font-size: 0.68rem;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    color: var(--register-muted);
}

.form-grid {
    display: grid;
    gap: 1rem;
    grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field {
    display: grid;
    gap: 0.4rem;
    animation: fade-up 0.6s ease both;
    animation-delay: var(--delay, 0s);
}

.field.span-2 {
    grid-column: 1 / -1;
}

label {
    font-family: $font-mono;
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--register-muted);
}

.glass-input {
    width: 100%;
    background: rgba(7, 11, 15, 0.75);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 0.85rem 1rem;
    color: var(--register-text);
    font-family: $font-body;
    font-size: 0.95rem;
    transition: border-color 0.2s ease, box-shadow 0.2s ease, transform 0.2s ease;

    &:focus {
        outline: none;
        border-color: rgba(35, 213, 161, 0.7);
        box-shadow: 0 0 0 3px rgba(35, 213, 161, 0.16);
        transform: translateY(-1px);
    }

    &::placeholder {
        color: rgba(147, 162, 178, 0.7);
    }
}

.password-wrap {
    position: relative;
}

.glass-input.has-toggle {
    padding-right: 5rem;
}

.toggle-password {
    position: absolute;
    right: 0.85rem;
    top: 50%;
    transform: translateY(-50%);
    background: transparent;
    border: none;
    font-family: $font-mono;
    font-size: 0.7rem;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--register-cool);
    cursor: pointer;
    transition: color 0.2s ease;

    &:hover {
        color: var(--register-text);
    }
}

.field-hint {
    font-family: $font-body;
    font-size: 0.75rem;
    color: var(--register-muted);
}

.password-rules {
    list-style: none;
    padding: 0;
    margin: 0.6rem 0 0;
    display: grid;
    gap: 0.35rem;
    font-size: 0.75rem;
    color: var(--register-muted);
}

.password-rules li {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.password-rules li::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.2);
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.08);
    flex: 0 0 auto;
}

.password-rules li.ok {
    color: rgba(134, 239, 172, 0.9);
}

.password-rules li.ok::before {
    background: rgba(35, 213, 161, 0.9);
    box-shadow: 0 0 8px rgba(35, 213, 161, 0.6);
}

.field-error {
    font-family: $font-mono;
    font-size: 0.7rem;
    color: #f87171;
    letter-spacing: 0.08em;
}

.remember {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    font-size: 0.82rem;
    color: var(--register-muted);

    input {
        accent-color: var(--register-accent);
    }
}

.remember.terms {
    align-items: flex-start;
    line-height: 1.4;
}

.terms-link {
    color: var(--register-warm);
    font-weight: 600;
    text-decoration: none;

    &:hover {
        color: var(--register-text);
    }
}

.glass-button {
    width: 100%;
    border-radius: 14px;
    padding: 1rem 1.1rem;
    font-family: $font-display;
    font-size: 0.95rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    border: 1px solid transparent;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    transition: transform 0.2s ease, box-shadow 0.2s ease;

    &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
        transform: none;
    }
}

.glass-button.primary {
    background: linear-gradient(115deg, rgba(35, 213, 161, 0.98) 0%, rgba(69, 195, 255, 0.92) 45%, rgba(246, 179, 72, 0.92) 100%);
    color: #02110c;
    border-color: rgba(35, 213, 161, 0.5);
    box-shadow: 0 0 24px rgba(35, 213, 161, 0.25);

    &:hover:not(:disabled) {
        transform: translateY(-1px);
        box-shadow: 0 0 28px rgba(35, 213, 161, 0.35);
    }
}

.signup {
    display: flex;
    justify-content: center;
    gap: 0.4rem;
    font-size: 0.8rem;
    color: var(--register-muted);

    a {
        color: var(--register-warm);
        font-weight: 600;
        text-decoration: none;

        &:hover {
            color: var(--register-text);
        }
    }
}

.success-box {
    margin-top: 0.5rem;
    padding: 0.75rem 0.9rem;
    border-radius: 12px;
    border: 1px solid rgba(34, 197, 94, 0.35);
    background: rgba(34, 197, 94, 0.1);
    color: #86efac;
    font-family: $font-mono;
    font-size: 0.75rem;
    letter-spacing: 0.08em;
}

.error-box {
    margin-top: 0.5rem;
    padding: 0.75rem 0.9rem;
    border-radius: 12px;
    border: 1px solid rgba(248, 113, 113, 0.35);
    background: rgba(248, 113, 113, 0.1);
    color: #fca5a5;
    font-family: $font-mono;
    font-size: 0.75rem;
    letter-spacing: 0.08em;
}

@keyframes orbit {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

@keyframes pulse {
    0%, 100% { transform: scale(1); opacity: 0.9; }
    50% { transform: scale(1.15); opacity: 1; }
}

@keyframes float {
    0%, 100% { transform: translate3d(0, 0, 0); }
    50% { transform: translate3d(-5%, 3%, 0); }
}

@keyframes panel-in {
    from { opacity: 0; transform: translateY(18px) scale(0.98); }
    to { opacity: 1; transform: translateY(0) scale(1); }
}

@keyframes fade-up {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 960px) {
    .register-shell {
        grid-template-columns: 1fr;
    }
}

@media (max-width: 720px) {
    .form-grid {
        grid-template-columns: 1fr;
    }

    .field.span-2 {
        grid-column: auto;
    }
}

@media (max-width: 520px) {
    .register-card,
    .register-hero {
        padding: 2rem 1.6rem;
    }
}

@media (prefers-reduced-motion: reduce) {
    .register::before,
    .register-card,
    .register-hero,
    .field {
        animation: none;
    }
}
</file>

<file path="app/features/auth/register/register.ts">
import { ChangeDetectorRef, Component, inject } from '@angular/core'
import { ReactiveFormsModule, FormBuilder, Validators, AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms'
import { RouterLink } from '@angular/router'
import { AuthService } from '../../../core/auth/auth.service'

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './register.html',
  styleUrls: ['./register.scss']
})
export class RegisterComponent {
  private fb = inject(FormBuilder)
  private auth = inject(AuthService)
  private cdr = inject(ChangeDetectorRef)
  private readonly cpfValidator: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
    const cpf = String(control.value ?? '').replace(/\D/g, '')
    if (!cpf) return null
    if (cpf.length !== 11) return { cpfInvalid: true }
    if (/^(\d)\1{10}$/.test(cpf)) return { cpfInvalid: true }

    const calcDigit = (base: number): number => {
      let sum = 0
      for (let i = 0; i < base; i += 1) {
        sum += Number(cpf[i]) * ((base + 1) - i)
      }
      const digit = (sum * 10) % 11
      return digit === 10 ? 0 : digit
    }

    const d10 = calcDigit(9)
    const d11 = calcDigit(10)
    const valid = d10 === Number(cpf[9]) && d11 === Number(cpf[10])
    return valid ? null : { cpfInvalid: true }
  }
  private readonly passwordStrengthValidator: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
    const value = String(control.value ?? '')
    const hasMinLength = value.length >= 8
    const hasUpper = /[A-Z]/.test(value)
    const hasLower = /[a-z]/.test(value)
    const hasNumber = /\d/.test(value)
    const hasSpecial = /[^A-Za-z0-9]/.test(value)
    return hasMinLength && hasUpper && hasLower && hasNumber && hasSpecial ? null : { passwordStrength: true }
  }
  private readonly passwordPersonalInfoValidator: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
    const password = String(control.get('password')?.value ?? '')
    if (!password) return null
    const normalizedPassword = this.normalizeForMatch(password)
    if (!normalizedPassword) return null
    const tokens = this.collectPersonalTokens(control)
    const hit = tokens.some(token => token && normalizedPassword.includes(token))
    return hit ? { passwordContainsPersonalInfo: true } : null
  }
  form = this.fb.group({
    username: ['', [Validators.required, Validators.minLength(3), Validators.pattern(/^[a-zA-Z0-9._-]+$/)]],
    fullName: ['', [Validators.required, Validators.minLength(3)]],
    cpf: ['', [Validators.required, Validators.pattern(/^(\d{11}|\d{3}\.\d{3}\.\d{3}-\d{2})$/), this.cpfValidator]],
    phone: ['', [Validators.required, Validators.pattern(/^\(?\d{2}\)?\s?\d{4,5}-?\d{4}$/)]],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, this.passwordStrengthValidator]],
    terms: [false, Validators.requiredTrue]
  }, { validators: [this.passwordPersonalInfoValidator] })
  showPassword = false
  loading = false
  error = ''
  success = ''

  get passwordValue(): string {
    return String(this.form.controls.password.value ?? '')
  }

  get hasMinLength(): boolean {
    return this.passwordValue.length >= 8
  }

  get hasUppercase(): boolean {
    return /[A-Z]/.test(this.passwordValue)
  }

  get hasLowercase(): boolean {
    return /[a-z]/.test(this.passwordValue)
  }

  get hasNumber(): boolean {
    return /\d/.test(this.passwordValue)
  }

  get hasSpecial(): boolean {
    return /[^A-Za-z0-9]/.test(this.passwordValue)
  }

  get hasNoPersonalInfo(): boolean {
    return this.passwordValue.length > 0 && !this.form.hasError('passwordContainsPersonalInfo')
  }

  onCpfInput() {
    const control = this.form.controls.cpf
    const raw = String(control.value ?? '')
    const formatted = this.formatCpf(raw)
    if (formatted !== raw) {
      control.setValue(formatted, { emitEvent: false })
    }
  }

  onPhoneInput() {
    const control = this.form.controls.phone
    const raw = String(control.value ?? '')
    const formatted = this.formatPhone(raw)
    if (formatted !== raw) {
      control.setValue(formatted, { emitEvent: false })
    }
  }

  togglePassword() {
    this.showPassword = !this.showPassword
  }

  async register() {
    if (this.loading) return
    this.error = ''
    this.success = ''
    if (this.form.invalid) {
      this.form.markAllAsTouched()
      return
    }
    this.loading = true
    try {
      const result = await this.auth.registerLocal({
        username: String(this.form.value.username || ''),
        fullName: String(this.form.value.fullName || ''),
        cpf: String(this.form.value.cpf || ''),
        phone: String(this.form.value.phone || ''),
        email: String(this.form.value.email || ''),
        password: String(this.form.value.password || ''),
        terms: Boolean(this.form.value.terms)
      })
      if (result.ok) {
        this.success = 'Cadastro realizado. Voce ja pode acessar.'
        this.form.reset({ terms: false })
      } else {
        this.error = result.error || 'Falha ao registrar. Verifique seus dados.'
      }
    } catch {
      this.error = 'Falha ao registrar. Tente novamente.'
    } finally {
      this.loading = false
      this.cdr.markForCheck()
    }
  }

  private formatCpf(value: string): string {
    const digits = value.replace(/\D/g, '').slice(0, 11)
    if (digits.length <= 3) return digits
    if (digits.length <= 6) return `${digits.slice(0, 3)}.${digits.slice(3)}`
    if (digits.length <= 9) {
      return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6)}`
    }
    return `${digits.slice(0, 3)}.${digits.slice(3, 6)}.${digits.slice(6, 9)}-${digits.slice(9)}`
  }

  private formatPhone(value: string): string {
    const digits = value.replace(/\D/g, '').slice(0, 11)
    if (digits.length <= 2) return digits
    const ddd = digits.slice(0, 2)
    const rest = digits.slice(2)
    if (rest.length <= 4) return `(${ddd}) ${rest}`
    if (rest.length <= 8) return `(${ddd}) ${rest.slice(0, 4)}-${rest.slice(4)}`
    return `(${ddd}) ${rest.slice(0, 5)}-${rest.slice(5)}`
  }

  private normalizeForMatch(value: string): string {
    return value.toLowerCase().replace(/[^a-z0-9]/g, '')
  }

  private collectPersonalTokens(control: AbstractControl): string[] {
    const tokens = new Set<string>()
    const username = this.normalizeForMatch(String(control.get('username')?.value ?? ''))
    if (username.length >= 3) tokens.add(username)

    const email = String(control.get('email')?.value ?? '').toLowerCase()
    const emailLocal = email.split('@')[0] || ''
    const normalizedEmailLocal = this.normalizeForMatch(emailLocal)
    if (normalizedEmailLocal.length >= 3) tokens.add(normalizedEmailLocal)

    const fullName = String(control.get('fullName')?.value ?? '').toLowerCase()
    fullName.split(/\s+/).forEach(part => {
      const normalizedPart = this.normalizeForMatch(part)
      if (normalizedPart.length >= 3) tokens.add(normalizedPart)
    })

    const cpfDigits = String(control.get('cpf')?.value ?? '').replace(/\D/g, '')
    if (cpfDigits.length >= 11) tokens.add(cpfDigits)
    if (cpfDigits.length >= 4) tokens.add(cpfDigits.slice(-4))

    const phoneDigits = String(control.get('phone')?.value ?? '').replace(/\D/g, '')
    if (phoneDigits.length >= 10) tokens.add(phoneDigits)
    if (phoneDigits.length >= 4) tokens.add(phoneDigits.slice(-4))

    return Array.from(tokens)
  }
}
</file>

<file path="app/features/conversations/admin-code-qa.util.spec.ts">
import { describe, expect, it } from 'vitest'

import { parseAdminCodeQaCommand } from './admin-code-qa.util'

describe('parseAdminCodeQaCommand', () => {
  it('nao ativa code qa para usuario nao admin', () => {
    const result = parseAdminCodeQaCommand('/code me fale de chat', false)
    expect(result).toEqual({ enabled: false, question: null })
  })

  it('nao ativa code qa para pergunta natural no admin', () => {
    const result = parseAdminCodeQaCommand('me fale um arquivo seu', true)
    expect(result).toEqual({ enabled: false, question: null })
  })

  it('ativa code qa quando comando /code e informado', () => {
    const result = parseAdminCodeQaCommand('/code me fale um arquivo seu', true)
    expect(result).toEqual({ enabled: true, question: 'me fale um arquivo seu' })
  })

  it('ativa com question nula quando /code vem sem pergunta', () => {
    const result = parseAdminCodeQaCommand('/code   ', true)
    expect(result).toEqual({ enabled: true, question: null })
  })

  it('suporta comando /code case insensitive', () => {
    const result = parseAdminCodeQaCommand('/CODE arquitetura do chat', true)
    expect(result).toEqual({ enabled: true, question: 'arquitetura do chat' })
  })
})
</file>

<file path="app/features/conversations/admin-code-qa.util.ts">
export interface AdminCodeQaCommandResult {
  enabled: boolean
  question: string | null
}

export function parseAdminCodeQaCommand(
  message: string,
  isAdmin: boolean
): AdminCodeQaCommandResult {
  if (!isAdmin) {
    return { enabled: false, question: null }
  }

  const text = String(message || '').trim()
  const match = text.match(/^\/code\b([\s\S]*)$/i)
  if (!match) {
    return { enabled: false, question: null }
  }

  const question = String(match[1] || '').trim()
  return {
    enabled: true,
    question: question || null
  }
}
</file>

<file path="app/features/conversations/conversations.html">
<section class="conversations">
  <app-header></app-header>

  <div class="convo-shell">
    <header class="convo-hero">
      <div class="hero-copy">
        <p class="eyebrow">JANUS // CONVERSAS</p>
        <h1>Converse com o Janus sem friccao</h1>
        <p class="sub">
          Escolha uma conversa ou envie sua primeira pergunta. O modo avancado fica opcional.
        </p>
      </div>
      <div class="hero-actions">
        <button ui-button variant="default" size="lg" (click)="createConversation()" [disabled]="sending()">
          <span class="material-icons">add</span>
          Nova conversa
        </button>
        <button ui-button variant="ghost" size="lg" (click)="refresh()" [disabled]="listLoading()">
          Atualizar
        </button>
      </div>
    </header>

    <div class="convo-grid" [class.simple]="!showAdvanced()">
      <aside class="convo-panel convo-list" aria-label="Lista de conversas">
        <div class="panel-head">
          <div>
            <p class="eyebrow">HISTORICO</p>
            <h2>Conversas</h2>
          </div>
          <ui-badge variant="neutral">{{ conversations().length }}</ui-badge>
        </div>

        <div class="search-row">
          <span class="material-icons">search</span>
          <input
            type="text"
            aria-label="Buscar conversas"
            placeholder="Buscar por titulo ou id"
            [value]="search()"
            (input)="onSearchChange($event)" />
          @if (search()) {
            <button ui-button variant="ghost" size="icon" (click)="clearSearch()" aria-label="Limpar busca">
              <span class="material-icons">close</span>
            </button>
          }
          <button ui-button variant="ghost" size="icon" (click)="refresh()" [disabled]="listLoading()">
            <span class="material-icons">refresh</span>
          </button>
        </div>

        @if (listLoading()) {
          <app-skeleton variant="paragraph" [count]="6"></app-skeleton>
        } @else if (filteredConversations().length) {
          <ul class="conversation-list">
            @for (conv of filteredConversations(); track conv.conversation_id) {
              <li
                class="conversation-item"
                [class.active]="conv.conversation_id === selectedId()">
                <button class="conversation-trigger" type="button" (click)="openConversation(conv)">
                  <div class="item-content">
                    <span class="item-title">{{ conv.title || ('Conversa ' + conv.conversation_id.slice(0, 8)) }}</span>
                    <span class="muted line-clamp-2">{{ conversationPreviewText(conv) }}</span>
                  </div>
                  <div class="item-tags">
                    <span class="chip">ID {{ conv.conversation_id.slice(0, 6) }}</span>
                    <span class="chip soft">{{ conversationLastActivity(conv) }}</span>
                  </div>
                </button>
              </li>
            }
          </ul>
        } @else {
          <p class="muted">Nenhuma conversa encontrada.</p>
        }
      </aside>

      <section class="convo-panel convo-main" aria-label="Chat">
        <div class="chat-head">
          <div class="title-group">
            <app-jarvis-avatar [state]="avatarState()" [size]="48"></app-jarvis-avatar>
            <div>
              <p class="eyebrow">CONVERSA ATIVA</p>
              <h2>{{ selectedTitle() }}</h2>
              <p class="muted">ID {{ selectedId() || 'sem selecao' }}</p>
            </div>
          </div>
          <div class="status-group">
            <ui-badge [variant]="streamBadge().variant">{{ streamBadge().label }}</ui-badge>
            <ui-badge variant="neutral">{{ messages().length }} msgs</ui-badge>
            <ui-badge [variant]="isSimpleMode() ? 'neutral' : 'info'">{{ isSimpleMode() ? 'Modo simples' : 'Modo avancado' }}</ui-badge>
            @if (latestCognitiveState()) {
              <ui-badge variant="info">{{ latestCognitiveState() }}</ui-badge>
            }
            @if (latestToolStatus()) {
              <ui-badge variant="warning">{{ latestToolStatus() }}</ui-badge>
            }
            <button ui-button variant="ghost" size="sm" type="button" (click)="toggleAdvanced()">
              {{ showAdvanced() ? 'Voltar ao simples' : 'Abrir painel avancado' }}
            </button>
            @if (isAdmin()) {
              <ui-badge variant="info">Modo Admin</ui-badge>
            }
          </div>
        </div>

        @if (error()) {
          <div class="inline-alert" role="alert">
            <span class="material-icons">error_outline</span>
            {{ error() }}
          </div>
        }
        @if (!showAdvanced() && autonomyNotice(); as notice) {
          <div class="section-notice" [class.is-success]="notice.kind === 'success'" [class.is-info]="notice.kind === 'info'" [class.is-warning]="notice.kind === 'warning'" [class.is-error]="notice.kind === 'error'" role="status" aria-live="polite">
            <span class="material-icons">{{ notice.kind === 'success' ? 'check_circle' : notice.kind === 'error' ? 'error_outline' : 'info' }}</span>
            <span>{{ notice.message }}</span>
          </div>
        }

        <div class="chat-body" #messageList>
          @if (historyLoading()) {
            <app-skeleton variant="paragraph" [count]="8"></app-skeleton>
          } @else if (messages().length) {
            <div class="message-feed">
              @for (msg of messages(); track msg.id) {
                <article class="message"
                  [class.user]="msg.role === 'user'"
                  [class.assistant]="msg.role === 'assistant'"
                  [class.system]="msg.role === 'system'"
                  [class.error]="msg.error">
                  <div class="avatar-slot">
                    @if (msg.role === 'assistant') {
                      <app-jarvis-avatar [state]="msg.streaming ? 'thinking' : 'idle'" [size]="36"></app-jarvis-avatar>
                    } @else {
                      <div class="user-avatar">{{ displayName().slice(0, 1) }}</div>
                    }
                  </div>
                  <div class="bubble">
                    <div class="message-meta">
                      <span class="author">{{ authorLabel(msg) }}</span>
                      <span class="time">{{ formatTime(msg.timestamp) }}</span>
                      @if (msg.streaming) {
                        <span class="stream-indicator">streaming</span>
                      }
                    </div>
                    @if (msg.role === 'assistant' && (msg.provider || msg.model || msg.latency_ms)) {
                      <div class="message-runtime">
                        <span class="runtime-chip">{{ assistantRuntimeLabel(msg) }}</span>
                        @if (msg.latency_ms) {
                          <span class="runtime-chip">{{ formatLatency(msg.latency_ms) }}</span>
                        }
                        @if (messageAgentState(msg)) {
                          <span class="runtime-chip">{{ messageAgentState(msg) }}</span>
                        }
                      </div>
                    }
                    <div class="message-text markdown-content" [innerHTML]="msg.text | markdown"></div>
                    @if (msg.role === 'assistant' && msg.understanding?.summary) {
                      <div class="understanding-card">
                        <div class="understanding-head">
                          <span class="understanding-label">Entendi assim</span>
                          <span class="understanding-intent">{{ understandingIntentLabel(msg.understanding) }}</span>
                          <span
                            class="confidence-chip"
                            [class.high]="understandingConfidenceBand(msg.understanding) === 'high'"
                            [class.medium]="understandingConfidenceBand(msg.understanding) === 'medium'"
                            [class.low]="understandingConfidenceBand(msg.understanding) === 'low'">
                            {{ understandingConfidenceLabel(msg.understanding) }}
                          </span>
                          <span class="muted">{{ understandingConfidence(msg.understanding) }}</span>
                        </div>
                        <p>{{ msg.understanding?.summary }}</p>
                        @if (msg.understanding?.low_confidence) {
                          <span class="understanding-flag">Acao com confirmacao sugerida</span>
                          <button ui-button variant="ghost" size="sm" type="button" (click)="confirmLowConfidence()">
                            Confirmar antes de executar
                          </button>
                        }
                      </div>
                    }
                    @if (msg.role === 'assistant') {
                      @if (messageConfirmation(msg); as confirmation) {
                        <div class="understanding-card confirmation-card">
                          <div class="understanding-head">
                            <span class="understanding-label">Confirmação de ação</span>
                            <span class="understanding-intent">{{ confirmation.reason || 'requires_confirmation' }}</span>
                            @if (confirmation.pending_action_id) {
                              <span class="muted">#{{ confirmation.pending_action_id }}</span>
                            }
                          </div>
                          <p>{{ messageRiskSummary(msg) }}</p>
                          @if (confirmation.pending_action_id && confirmation.required !== false) {
                            <div class="confirmation-actions">
                              <button
                                ui-button
                                variant="default"
                                size="sm"
                                type="button"
                                [disabled]="isPendingActionBusy(confirmation.pending_action_id)"
                                (click)="approvePendingActionForMessage(msg)">
                                Aprovar
                              </button>
                              <button
                                ui-button
                                variant="ghost"
                                size="sm"
                                type="button"
                                [disabled]="isPendingActionBusy(confirmation.pending_action_id)"
                                (click)="rejectPendingActionForMessage(msg)">
                                Rejeitar
                              </button>
                            </div>
                          } @else if (confirmation.required !== false) {
                            <span class="understanding-flag">Pendência sem ID estruturado (fallback legado)</span>
                          } @else {
                            <span class="understanding-flag">Confirmação processada</span>
                          }
                        </div>
                      }
                    }
                    @if (msg.citations?.length) {
                      <div class="citation-list">
                        @for (cite of msg.citations; track $index) {
                          <details class="citation-item">
                            <summary class="citation-chip" title="Abrir detalhes da fonte">
                              {{ citationTitle(cite) }}
                            </summary>
                            <div class="citation-detail">
                              <div class="citation-actions">
                                @if (cite.url) {
                                  <a [href]="cite.url" target="_blank" rel="noopener noreferrer">Abrir fonte</a>
                                } @else {
                                  <span class="muted">Fonte local sem URL publica</span>
                                }
                                <button ui-button variant="ghost" size="sm" type="button" (click)="copyCitation(cite)">
                                  {{ copiedCitation() === citationReference(cite) ? 'Copiado' : 'Copiar referencia' }}
                                </button>
                              </div>
                              <span class="muted">Score: {{ citationScore(cite) }}</span>
                              @if (cite.snippet) {
                                <pre>{{ cite.snippet }}</pre>
                              }
                            </div>
                          </details>
                        }
                      </div>
                    }
                    @if (msg.role === 'assistant' && msg.citation_status && (!msg.citations?.length || msg.citation_status.status !== 'present')) {
                      <div class="citation-status-inline">
                        <ui-badge [variant]="citationStatusVariant(msg.citation_status)">{{ citationStatusLabel(msg.citation_status) }}</ui-badge>
                        @if (msg.citation_status.reason) {
                          <span class="muted">{{ msg.citation_status.reason }}</span>
                        }
                      </div>
                    }
                    @if (msg.role === 'assistant' && !msg.streaming) {
                      <div class="message-feedback">
                        <div class="feedback-row">
                          @if (feedbackState(msg).submitted && !feedbackState(msg).error) {
                            <div class="feedback-pill success" aria-live="polite">
                              <span class="material-icons">check_circle</span>
                              <span>{{ feedbackState(msg).serverMessage || 'Feedback enviado' }}</span>
                            </div>
                          } @else {
                            <div class="feedback-actions-inline" role="group" aria-label="Ações de feedback da resposta">
                              <button
                                ui-button
                                variant="ghost"
                                size="sm"
                                type="button"
                                (click)="sendThumbsUp(msg)"
                                [disabled]="feedbackState(msg).submitting || feedbackState(msg).submitted"
                                aria-label="Gostei desta resposta">
                                👍
                              </button>
                              <button
                                ui-button
                                variant="ghost"
                                size="sm"
                                type="button"
                                (click)="sendThumbsDown(msg)"
                                [disabled]="feedbackState(msg).submitting || feedbackState(msg).submitted"
                                aria-label="Não gostei desta resposta">
                                👎
                              </button>
                            </div>
                          }
                          <button
                            class="feedback-comment-toggle"
                            type="button"
                            (click)="toggleFeedbackComment(msg.id)"
                            [disabled]="feedbackState(msg).submitting"
                            [attr.aria-expanded]="feedbackState(msg).commentOpen"
                            [attr.aria-controls]="'feedback-comment-' + msg.id">
                            {{ feedbackState(msg).commentOpen ? 'Ocultar comentário' : 'Adicionar comentário' }}
                          </button>
                        </div>
                        @if (feedbackState(msg).commentOpen) {
                          <div class="feedback-comment-box" [id]="'feedback-comment-' + msg.id">
                            <textarea
                              rows="2"
                              placeholder="O que faltou? O que melhoraria? (opcional)"
                              [value]="feedbackCommentDraft(msg.id)"
                              (input)="onFeedbackCommentInput(msg.id, $event)">
                            </textarea>
                            <div class="feedback-comment-actions">
                              <button ui-button variant="ghost" size="sm" type="button" (click)="sendThumbsUp(msg)" [disabled]="feedbackState(msg).submitting">Enviar 👍</button>
                              <button ui-button variant="ghost" size="sm" type="button" (click)="sendThumbsDown(msg)" [disabled]="feedbackState(msg).submitting">Enviar 👎</button>
                            </div>
                          </div>
                        }
                        @if (feedbackState(msg).error) {
                          <div class="feedback-error-row">
                            <p class="muted feedback-status error">{{ feedbackState(msg).error }}</p>
                            <button
                              ui-button
                              variant="ghost"
                              size="sm"
                              type="button"
                              (click)="feedbackState(msg).rating === 'negative' ? sendThumbsDown(msg) : sendThumbsUp(msg)"
                              [disabled]="feedbackState(msg).submitting">
                              Tentar novamente
                            </button>
                          </div>
                        }
                      </div>
                    }
                  </div>
                </article>
              }
            </div>
          } @else {
            <div class="empty-state">
              @if (!hasConversationSelected()) {
                <h3>Selecione uma conversa</h3>
                <p class="muted">Escolha uma conversa na coluna lateral ou crie uma nova para comecar.</p>
                <div class="empty-actions">
                  <button ui-button variant="default" size="sm" type="button" (click)="createConversation()">
                    Nova conversa
                  </button>
                </div>
              } @else {
                <h3>Nenhuma mensagem ainda</h3>
                <p class="muted">Envie a primeira pergunta para iniciar esta conversa.</p>
                <div class="quick-prompts">
                  @for (item of quickPrompts; track item) {
                    <button ui-button variant="ghost" size="sm" type="button" (click)="useQuickPrompt(item)">
                      {{ item }}
                    </button>
                  }
                </div>
              }
            </div>
          }
        </div>

        <div class="composer">
          @if (showAdvanced()) {
            <div class="composer-toolbar">
              <label>
                <span>Role</span>
                <select [value]="selectedRole()" (change)="selectedRole.set($any($event.target).value)">
                  @for (role of roleOptions; track role.value) {
                    <option [value]="role.value">{{ role.label }}</option>
                  }
                </select>
              </label>
              <label>
                <span>Prioridade</span>
                <select [value]="selectedPriority()" (change)="selectedPriority.set($any($event.target).value)">
                  @for (priority of priorityOptions; track priority.value) {
                    <option [value]="priority.value">{{ priority.label }}</option>
                  }
                </select>
              </label>
              <label class="toggle">
                <input type="checkbox" [checked]="streamingEnabled()" (change)="streamingEnabled.set(!streamingEnabled())" />
                <span>Streaming</span>
              </label>
            </div>
            <p class="composer-helper muted">
              Role e prioridade ajustam a estrategia de resposta. Se tiver duvida, mantenha o padrao.
            </p>
          } @else {
            <p class="composer-helper muted">
              Modo simples ativo: foco na conversa. O Janus escolhe automaticamente a melhor estrategia.
            </p>
          }

          <textarea
            [formControl]="prompt"
            rows="3"
            placeholder="Descreva a tarefa ou envie uma pergunta..."
            (keydown)="onComposerKeydown($event)">
          </textarea>

          <div class="composer-actions">
            <button ui-button variant="ghost" size="sm" type="button" (click)="clearComposer()">Limpar</button>
            <button ui-button variant="default" size="lg" type="button" (click)="sendMessage()" [disabled]="sending()">
              <span class="material-icons">send</span>
              Enviar
            </button>
          </div>
        </div>
      </section>

      @if (showAdvanced()) {
      <aside class="convo-panel convo-rail" aria-label="Contexto">
        <header class="rail-header">
          <div>
            <p class="eyebrow">PAINEL AVANCADO</p>
            <h3>Contexto, cliente e autonomia</h3>
            <p class="muted rail-subtitle">Use as abas para reduzir ruído e focar na etapa atual da conversa.</p>
          </div>
          <div class="segmented-tabs" role="tablist" aria-label="Abas do painel avançado">
            <button
              id="advanced-tab-insights"
              type="button"
              role="tab"
              class="segmented-tab"
              [class.active]="advancedRailTab() === 'insights'"
              [attr.aria-selected]="advancedRailTab() === 'insights'"
              [attr.tabindex]="advancedRailTab() === 'insights' ? 0 : -1"
              aria-controls="advanced-tabpanel-insights"
              (keydown)="onAdvancedRailTabKeydown($event)"
              (click)="setAdvancedRailTab('insights')">
              Insights
            </button>
            <button
              id="advanced-tab-cliente"
              type="button"
              role="tab"
              class="segmented-tab"
              [class.active]="advancedRailTab() === 'cliente'"
              [attr.aria-selected]="advancedRailTab() === 'cliente'"
              [attr.tabindex]="advancedRailTab() === 'cliente' ? 0 : -1"
              aria-controls="advanced-tabpanel-cliente"
              (keydown)="onAdvancedRailTabKeydown($event)"
              (click)="setAdvancedRailTab('cliente')">
              Cliente
            </button>
            <button
              id="advanced-tab-autonomia"
              type="button"
              role="tab"
              class="segmented-tab"
              [class.active]="advancedRailTab() === 'autonomia'"
              [attr.aria-selected]="advancedRailTab() === 'autonomia'"
              [attr.tabindex]="advancedRailTab() === 'autonomia' ? 0 : -1"
              aria-controls="advanced-tabpanel-autonomia"
              (keydown)="onAdvancedRailTabKeydown($event)"
              (click)="setAdvancedRailTab('autonomia')">
              Autonomia
            </button>
          </div>
        </header>

        @if (advancedRailTab() === 'insights') {
          <div id="advanced-tabpanel-insights" class="rail-tab-panel" role="tabpanel" aria-labelledby="advanced-tab-insights">
            <section class="rail-section">
              <div class="panel-head">
                <h3>Explicacao da resposta</h3>
              </div>
              @if (latestAssistantMessage(); as latest) {
                <div class="explain-card">
                  <div class="explain-grid">
                    <span class="metric-pill">Fontes: {{ latest.citations?.length || 0 }}</span>
                    <span class="metric-pill">Confianca: {{ understandingConfidence(latest.understanding) }}</span>
                    <span class="metric-pill">Latencia: {{ formatLatency(latest.latency_ms) }}</span>
                  </div>
                  @if (latest.provider || latest.model) {
                    <p class="muted">Modelo: {{ latest.provider || '--' }} / {{ latest.model || '--' }}</p>
                  }
                  @if (latest.understanding?.summary) {
                    <p class="muted">{{ latest.understanding?.summary }}</p>
                  }
                </div>
              } @else {
                <p class="muted">Envie uma mensagem para visualizar fontes, confianca e latencia.</p>
              }
            </section>

            <section class="rail-section">
              <div class="panel-head">
                <h3>Thought stream</h3>
                <ui-badge variant="info">{{ thoughtStream().length }}</ui-badge>
              </div>
              @if (thoughtStream().length) {
                <ul class="thought-list">
                  @for (item of thoughtStream(); track item.id) {
                    <li class="thought-item" [class.agent]="item.kind === 'agent'" [class.stream]="item.kind === 'stream'" [class.system]="item.kind === 'system'">
                      <div class="thought-head">
                        <span class="thought-icon material-icons">{{ thoughtIcon(item) }}</span>
                        <strong>{{ item.title }}</strong>
                        <span class="muted">{{ formatTime(item.timestamp) }}</span>
                      </div>
                      <p>{{ item.text }}</p>
                    </li>
                  }
                </ul>
              } @else {
                <p class="muted">Ainda sem atividade em tempo real.</p>
              }
            </section>

            <section class="rail-section">
              <div class="panel-head">
                <h3>Trace tecnico</h3>
                <button ui-button variant="ghost" size="sm" (click)="toggleTrace()">
                  {{ showTrace() ? 'Ocultar' : 'Carregar' }}
                </button>
              </div>
              @if (showTrace()) {
                @if (traceSteps().length) {
                  <ul class="trace-list">
                    @for (step of traceSteps(); track step.stepId) {
                      <li class="trace-item">
                        <div class="trace-header">
                          <span class="agent-badge">{{ step.agent }}</span>
                          <span class="trace-time">{{ formatTime(step.timestamp * 1000) }}</span>
                        </div>
                        <div class="trace-content">
                          <strong>{{ step.type }}</strong>
                          <p>{{ step.content }}</p>
                        </div>
                      </li>
                    }
                  </ul>
                } @else {
                  <p class="muted">Nenhum rastro tecnico disponivel.</p>
                }
              } @else {
                <p class="muted">Ative para carregar a trilha detalhada por etapa.</p>
              }
            </section>
          </div>
        }

        @if (advancedRailTab() === 'cliente') {
          <div id="advanced-tabpanel-cliente" class="rail-tab-panel" role="tabpanel" aria-labelledby="advanced-tab-cliente">
            <section class="rail-section customer-tools">
              <div class="panel-head">
                <div>
                  <p class="eyebrow">RECURSOS DO CLIENTE</p>
                  <h3>Documentos, memoria e RAG</h3>
                  <p class="muted">Anexe contexto, recupere memória e rode consultas RAG sem sair da conversa.</p>
                </div>
              </div>

              <div class="segmented-tabs customer-tabs" role="tablist" aria-label="Abas de recursos do cliente">
                <button
                  id="customer-tab-docs"
                  type="button"
                  role="tab"
                  class="segmented-tab customer docs"
                  [class.active]="customerTab() === 'docs'"
                  [attr.aria-selected]="customerTab() === 'docs'"
                  [attr.tabindex]="customerTab() === 'docs' ? 0 : -1"
                  aria-controls="customer-tabpanel-docs"
                  (keydown)="onCustomerTabKeydown($event)"
                  (click)="setCustomerTab('docs')">
                  Docs
                </button>
                <button
                  id="customer-tab-memoria"
                  type="button"
                  role="tab"
                  class="segmented-tab customer memoria"
                  [class.active]="customerTab() === 'memoria'"
                  [attr.aria-selected]="customerTab() === 'memoria'"
                  [attr.tabindex]="customerTab() === 'memoria' ? 0 : -1"
                  aria-controls="customer-tabpanel-memoria"
                  (keydown)="onCustomerTabKeydown($event)"
                  (click)="setCustomerTab('memoria')">
                  Memoria
                </button>
                <button
                  id="customer-tab-rag"
                  type="button"
                  role="tab"
                  class="segmented-tab customer rag"
                  [class.active]="customerTab() === 'rag'"
                  [attr.aria-selected]="customerTab() === 'rag'"
                  [attr.tabindex]="customerTab() === 'rag' ? 0 : -1"
                  aria-controls="customer-tabpanel-rag"
                  (keydown)="onCustomerTabKeydown($event)"
                  (click)="setCustomerTab('rag')">
                  RAG
                </button>
              </div>

              @if (customerTab() === 'docs') {
                <div id="customer-tabpanel-docs" class="rail-tab-panel nested" role="tabpanel" aria-labelledby="customer-tab-docs">
                  <div class="customer-card accent-docs">
                    <div class="panel-head">
                      <div>
                        <h4>Ingestao de documentos</h4>
                        <p class="muted section-help">Vincule uma URL ou envie um arquivo para enriquecer o contexto desta conversa.</p>
                      </div>
                      <ui-badge variant="neutral">{{ docs().length }}</ui-badge>
                    </div>
                    @if (docsNotice(); as notice) {
                      <div class="section-notice" [class.is-success]="notice.kind === 'success'" [class.is-info]="notice.kind === 'info'" [class.is-warning]="notice.kind === 'warning'" [class.is-error]="notice.kind === 'error'" role="status" aria-live="polite">
                        <span class="material-icons">{{ notice.kind === 'success' ? 'check_circle' : notice.kind === 'error' ? 'error_outline' : 'info' }}</span>
                        <span>{{ notice.message }}</span>
                      </div>
                    }

                    <div class="customer-subcard">
                      <div class="stack-gap-sm">
                        <label class="field-label">Vincular URL</label>
                        <p class="muted section-help compact">Use para importar conteúdo público e indexar na conversa atual.</p>
                        <div class="inline-form">
                          <input
                            type="url"
                            placeholder="https://..."
                            [value]="docLinkUrl()"
                            (input)="onDocLinkInput($event)" />
                          <button ui-button variant="ghost" size="sm" type="button" (click)="linkDocumentUrl()" [disabled]="docLinkLoading()">
                            {{ docLinkLoading() ? 'Vinculando...' : 'Vincular' }}
                          </button>
                        </div>
                        @if (docLinkError()) {
                          <p class="muted field-error" [class.is-business]="isBusinessDocError(docLinkError())">{{ docLinkError() }}</p>
                        }
                      </div>
                    </div>

                    <div class="customer-subcard">
                      <div class="stack-gap-sm">
                        <label class="field-label">Upload de arquivo</label>
                        <p class="muted section-help compact">Arquivos ficam vinculados à conversa e entram no contexto das próximas respostas.</p>
                        <div class="inline-form file-form">
                          <input type="file" (change)="onDocFileSelected($event)" />
                          <button ui-button variant="ghost" size="sm" type="button" (click)="uploadSelectedDoc()" [disabled]="docUploadInFlight() || !selectedUploadFile()">
                            {{ docUploadInFlight() ? 'Enviando...' : 'Upload' }}
                          </button>
                        </div>
                        @if (selectedUploadFile()) {
                          <p class="muted">Arquivo: {{ selectedUploadFile()?.name }}</p>
                        }
                        @if (docUploadProgress() !== null) {
                          <div class="progress-row" aria-label="Progresso do upload">
                            <div class="progress-track">
                              <div class="progress-fill" [style.width.%]="docUploadProgress() || 0"></div>
                            </div>
                            <span class="muted">{{ docUploadProgress() }}%</span>
                          </div>
                          <p class="muted section-help compact">Progresso do envio e processamento inicial do arquivo.</p>
                        }
                        @if (docUploadError()) {
                          <p class="muted field-error" [class.is-business]="isBusinessDocError(docUploadError())">{{ docUploadError() }}</p>
                        }
                      </div>
                    </div>

                    <div class="customer-subcard">
                      <div class="stack-gap-sm">
                        <label class="field-label">Buscar em documentos</label>
                        <p class="muted section-help compact">Recupere trechos indexados por similaridade para validar contexto rapidamente.</p>
                        <div class="inline-form">
                          <input
                            type="text"
                            placeholder="Buscar por conteúdo/index..."
                            [value]="docSearchQuery()"
                            (input)="onDocSearchInput($event)"
                            (keydown.enter)="searchDocs()" />
                          <button ui-button variant="ghost" size="sm" type="button" (click)="searchDocs()" [disabled]="docSearchLoading()">
                            {{ docSearchLoading() ? 'Buscando...' : 'Buscar' }}
                          </button>
                        </div>
                        @if (docSearchError()) {
                          <p class="muted field-error">{{ docSearchError() }}</p>
                        }
                        @if (docSearchResults().length) {
                          <ul class="rail-list compact">
                            @for (item of docSearchResults(); track item.id) {
                              <li class="rail-item compact-item doc-search-item">
                                <div class="rail-title">
                                  <span class="item-title">{{ item.file_name || item.doc_id }}</span>
                                  <span class="muted">{{ item.score ? (item.score * 100).toFixed(0) + '%' : '--' }}</span>
                                </div>
                                <span class="muted doc-meta-line">doc {{ item.doc_id }} · chunk {{ item.index ?? '--' }}</span>
                                @if (item['content']) {
                                  <p class="doc-snippet">{{ item['content'] }}</p>
                                }
                              </li>
                            }
                          </ul>
                        } @else if (docSearchQuery().trim() && !docSearchLoading() && !docSearchError()) {
                          <p class="muted">Nenhum trecho encontrado para esta busca.</p>
                        }
                      </div>
                    </div>

                    <div class="customer-subcard">
                      <div class="panel-head compact-head">
                        <h4>Biblioteca da conversa</h4>
                        <ui-badge variant="neutral">{{ docs().length }}</ui-badge>
                      </div>
                      @if (contextLoading()) {
                        <app-skeleton variant="text" [count]="3"></app-skeleton>
                      } @else if (docs().length) {
                        <ul class="rail-list compact doc-library-list">
                          @for (doc of docs(); track doc.doc_id) {
                            <li class="rail-item compact-item doc-library-item">
                              <div class="rail-title doc-action-row">
                                <span class="item-title">{{ doc.file_name || doc.doc_id }}</span>
                                <button ui-button variant="ghost" size="sm" type="button" (click)="deleteDoc(doc.doc_id)" [disabled]="deletingDocIds()[doc.doc_id]">
                                  {{ deletingDocIds()[doc.doc_id] ? 'Excluindo...' : 'Excluir' }}
                                </button>
                              </div>
                              <span class="muted doc-meta-line">{{ doc.chunks }} blocos · conv {{ doc.conversation_id || 'global' }}</span>
                            </li>
                          }
                        </ul>
                      } @else {
                        <p class="muted">Sem documentos vinculados a esta conversa.</p>
                      }
                    </div>
                  </div>
                </div>
              }

              @if (customerTab() === 'memoria') {
                <div id="customer-tabpanel-memoria" class="rail-tab-panel nested" role="tabpanel" aria-labelledby="customer-tab-memoria">
                  <div class="customer-card accent-memory">
                    <div class="panel-head">
                      <div>
                        <h4>Memoria generativa</h4>
                        <p class="muted section-help">Guarde fatos importantes do cliente e recupere contexto recorrente.</p>
                      </div>
                      <ui-badge variant="neutral">{{ generativeMemoryResults().length }}</ui-badge>
                    </div>
                    @if (memoryNotice(); as notice) {
                      <div class="section-notice" [class.is-success]="notice.kind === 'success'" [class.is-info]="notice.kind === 'info'" [class.is-warning]="notice.kind === 'warning'" [class.is-error]="notice.kind === 'error'" role="status" aria-live="polite">
                        <span class="material-icons">{{ notice.kind === 'success' ? 'check_circle' : notice.kind === 'error' ? 'error_outline' : 'info' }}</span>
                        <span>{{ notice.message }}</span>
                      </div>
                    }

                    <div class="customer-subcard">
                      <div class="stack-gap-sm">
                        <label class="field-label">Adicionar memória</label>
                        <textarea
                          rows="2"
                          placeholder="Fato, preferência ou contexto importante do cliente..."
                          [value]="memoryDraft()"
                          (input)="onMemoryDraftInput($event)">
                        </textarea>
                        <div class="memory-config-group">
                          <p class="field-label">Configurações</p>
                          <div class="inline-form memory-config-form">
                            <input
                              type="number"
                              min="0"
                              max="10"
                              step="1"
                              placeholder="Importância 0-10 (opcional)"
                              [value]="memoryImportance() ?? ''"
                              (input)="onMemoryImportanceInput($event)" />
                            <select [value]="memoryType()" (change)="onMemoryTypeChange($event)">
                              <option value="episodic">Episódica</option>
                              <option value="semantic">Semântica</option>
                              <option value="procedural">Procedural</option>
                            </select>
                            <button ui-button variant="ghost" size="sm" type="button" (click)="addMemory()" [disabled]="memoryAddLoading()">
                              {{ memoryAddLoading() ? 'Salvando...' : 'Adicionar' }}
                            </button>
                          </div>
                        </div>
                        @if (memoryAddError()) {
                          <p class="muted field-error">{{ memoryAddError() }}</p>
                        }
                      </div>
                    </div>

                    <div class="customer-subcard">
                      <div class="stack-gap-sm">
                        <label class="field-label">Buscar memória generativa</label>
                        <div class="inline-form">
                          <input
                            type="text"
                            placeholder="Ex.: preferências do cliente"
                            [value]="memorySearchQuery()"
                            (input)="onMemorySearchQueryInput($event)"
                            (keydown.enter)="searchGenerativeMemory()" />
                          <button ui-button variant="ghost" size="sm" type="button" (click)="searchGenerativeMemory()" [disabled]="memorySearchLoading()">
                            {{ memorySearchLoading() ? 'Buscando...' : 'Buscar' }}
                          </button>
                        </div>
                        @if (memorySearchError()) {
                          <p class="muted field-error">{{ memorySearchError() }}</p>
                        }
                        @if (generativeMemoryResults().length) {
                          <ul class="rail-list compact">
                            @for (item of generativeMemoryResults(); track $index) {
                              <li class="rail-item compact-item memory-list-item">
                                <p class="memory-content">{{ item.content }}</p>
                                <span class="muted memory-meta-line">{{ generativeMemoryMetaLine(item) }}</span>
                              </li>
                            }
                          </ul>
                        } @else if (memorySearchQuery().trim() && !memorySearchLoading() && !memorySearchError()) {
                          <p class="muted">Nenhuma memória encontrada para a busca atual.</p>
                        }
                      </div>
                    </div>

                    <div class="customer-subcard">
                      <div class="panel-head compact-head">
                        <h4>Memória da conversa</h4>
                        <ui-badge variant="neutral">{{ conversationMemory().length }}</ui-badge>
                      </div>
                      @if (contextLoading()) {
                        <app-skeleton variant="text" [count]="3"></app-skeleton>
                      } @else if (conversationMemory().length) {
                        <ul class="rail-list compact">
                          @for (item of conversationMemory(); track memoryTrackKey(item, $index)) {
                            <li class="rail-item compact-item memory-list-item">
                              <p class="memory-content">{{ item.content }}</p>
                              <span class="muted memory-meta-line">{{ formatDate(item.ts_ms) }}</span>
                            </li>
                          }
                        </ul>
                      } @else {
                        <p class="muted">Sem memória vinculada a esta conversa.</p>
                      }
                    </div>

                    <div class="customer-subcard">
                      <div class="panel-head compact-head">
                        <h4>Memória do usuário</h4>
                        <ui-badge variant="neutral">{{ userMemory().length }}</ui-badge>
                      </div>
                      @if (contextLoading()) {
                        <app-skeleton variant="text" [count]="3"></app-skeleton>
                      } @else if (userMemory().length) {
                        <ul class="rail-list compact">
                          @for (item of userMemory(); track memoryTrackKey(item, $index)) {
                            <li class="rail-item compact-item memory-list-item">
                              <p class="memory-content">{{ item.content }}</p>
                              <span class="muted memory-meta-line">{{ formatDate(item.ts_ms) }}</span>
                            </li>
                          }
                        </ul>
                      } @else {
                        <p class="muted">Sem memória de usuário recente.</p>
                      }
                    </div>
                  </div>
                </div>
              }

              @if (customerTab() === 'rag') {
                <div id="customer-tabpanel-rag" class="rail-tab-panel nested" role="tabpanel" aria-labelledby="customer-tab-rag">
                  <div class="customer-card accent-rag">
                    <div class="panel-head">
                      <div>
                        <h4>Consulta RAG</h4>
                        <p class="muted section-help">Use o modo certo para buscar em documentos, memória ou contexto pessoal.</p>
                      </div>
                      <ui-badge [variant]="ragLoading() ? 'warning' : 'info'">{{ ragLoading() ? 'Executando' : 'Pronto' }}</ui-badge>
                    </div>
                    @if (ragNotice(); as notice) {
                      <div class="section-notice" [class.is-success]="notice.kind === 'success'" [class.is-info]="notice.kind === 'info'" [class.is-warning]="notice.kind === 'warning'" [class.is-error]="notice.kind === 'error'" role="status" aria-live="polite">
                        <span class="material-icons">{{ notice.kind === 'success' ? 'check_circle' : notice.kind === 'error' ? 'error_outline' : 'info' }}</span>
                        <span>{{ notice.message }}</span>
                      </div>
                    }

                    <div class="customer-subcard">
                      <div class="stack-gap-sm">
                        <label class="field-label">Modo de consulta</label>
                        <select [value]="ragMode()" (change)="onRagModeChange($event)">
                          <option value="hybrid_search">Híbrido (Vetor + Grafo)</option>
                          <option value="search">Busca vetorial</option>
                          <option value="user-chat">Chat pessoal (v1)</option>
                          <option value="user_chat">Chat pessoal (v2)</option>
                          <option value="productivity">Produtividade</option>
                        </select>
                        <p class="muted rag-mode-hint">{{ ragModeHint(ragMode()) }}</p>
                      </div>
                    </div>

                    <div class="customer-subcard">
                      <div class="stack-gap-sm">
                        <label class="field-label">Consulta</label>
                        <div class="inline-form">
                          <input
                            type="text"
                            placeholder="Pergunte sobre contexto, docs ou conversa..."
                            [value]="ragQuery()"
                            (input)="onRagQueryInput($event)"
                            (keydown.enter)="runRagQuery()" />
                          <button ui-button variant="ghost" size="sm" type="button" (click)="runRagQuery()" [disabled]="ragLoading()">
                            {{ ragLoading() ? 'Consultando...' : 'Executar' }}
                          </button>
                        </div>
                        @if (ragError()) {
                          <p class="muted field-error">{{ ragError() }}</p>
                        }
                      </div>
                    </div>

                    <div class="customer-subcard">
                      <div class="panel-head compact-head">
                        <h4>Resultado</h4>
                        @if (ragResult(); as rr) {
                          <ui-badge variant="neutral">{{ ragModeLabel(rr.mode) }}</ui-badge>
                        }
                      </div>

                      @if (ragResult(); as rr) {
                        <div class="rag-result-card">
                          <div class="rag-result-head">
                            <span class="metric-pill">Modo: {{ ragModeLabel(rr.mode) }}</span>
                            <span class="metric-pill">Fontes: {{ rr.citations?.length || 0 }}</span>
                            <span class="metric-pill">Resultados: {{ rr.results?.length || 0 }}</span>
                          </div>
                          <div class="rag-view-tabs" role="tablist" aria-label="Visualização do resultado RAG">
                            <button
                              id="rag-view-tab-resposta"
                              type="button"
                              role="tab"
                              class="rag-view-tab"
                              [class.active]="ragResultViewTab() === 'resposta'"
                              [attr.aria-selected]="ragResultViewTab() === 'resposta'"
                              [attr.tabindex]="ragResultViewTab() === 'resposta' ? 0 : -1"
                              aria-controls="rag-view-panel-resposta"
                              (keydown)="onRagResultTabKeydown($event)"
                              (click)="setRagResultViewTab('resposta')">
                              Resposta
                            </button>
                            <button
                              id="rag-view-tab-fontes"
                              type="button"
                              role="tab"
                              class="rag-view-tab"
                              [class.active]="ragResultViewTab() === 'fontes'"
                              [attr.aria-selected]="ragResultViewTab() === 'fontes'"
                              [attr.tabindex]="ragResultViewTab() === 'fontes' ? 0 : -1"
                              aria-controls="rag-view-panel-fontes"
                              (keydown)="onRagResultTabKeydown($event)"
                              (click)="setRagResultViewTab('fontes')">
                              Fontes
                            </button>
                            <button
                              id="rag-view-tab-raw"
                              type="button"
                              role="tab"
                              class="rag-view-tab"
                              [class.active]="ragResultViewTab() === 'raw'"
                              [attr.aria-selected]="ragResultViewTab() === 'raw'"
                              [attr.tabindex]="ragResultViewTab() === 'raw' ? 0 : -1"
                              aria-controls="rag-view-panel-raw"
                              (keydown)="onRagResultTabKeydown($event)"
                              (click)="setRagResultViewTab('raw')">
                              Raw
                            </button>
                          </div>

                          @if (ragResultViewTab() === 'resposta') {
                            <div id="rag-view-panel-resposta" class="rag-view-panel" role="tabpanel" aria-labelledby="rag-view-tab-resposta">
                              @if (rr.answer) {
                                <div class="markdown-content" [innerHTML]="rr.answer | markdown"></div>
                              } @else if (rr.results?.length) {
                                <p class="muted rag-result-empty">Esta consulta retornou dados estruturados. Abra a aba <strong>Raw</strong> para inspecionar o resultado.</p>
                              } @else {
                                <p class="muted rag-result-empty">Nenhuma resposta textual retornada para esta consulta.</p>
                              }
                            </div>
                          }

                          @if (ragResultViewTab() === 'fontes') {
                            <div id="rag-view-panel-fontes" class="rag-view-panel" role="tabpanel" aria-labelledby="rag-view-tab-fontes">
                              @if (rr.citations?.length) {
                                <ul class="rail-list compact rag-section-list">
                                  @for (cite of rr.citations || []; track $index) {
                                    <li class="rail-item compact-item">
                                      <span class="item-title">{{ cite.file_path || cite.title || cite.doc_id || 'fonte' }}</span>
                                      <span class="muted">score {{ citationScore(cite) }}</span>
                                    </li>
                                  }
                                </ul>
                              } @else {
                                <p class="muted rag-result-empty">Sem fontes/citações para esta consulta.</p>
                              }
                            </div>
                          }

                          @if (ragResultViewTab() === 'raw') {
                            <div id="rag-view-panel-raw" class="rag-view-panel" role="tabpanel" aria-labelledby="rag-view-tab-raw">
                              @if (rr.results?.length) {
                                <details class="rag-raw-details">
                                  <summary>Raw (JSON)</summary>
                                  <ul class="rail-list compact rag-section-list">
                                    @for (row of rr.results || []; track $index) {
                                      <li class="rail-item compact-item">
                                        <pre>{{ row | json }}</pre>
                                      </li>
                                    }
                                  </ul>
                                </details>
                              } @else {
                                <p class="muted rag-result-empty">Sem payload bruto para exibir.</p>
                              }
                            </div>
                          }
                        </div>
                      } @else {
                        <p class="muted">Execute uma consulta para visualizar resposta, fontes e resultado bruto.</p>
                      }
                    </div>
                  </div>
                </div>
              }
            </section>
          </div>
        }

        @if (advancedRailTab() === 'autonomia') {
          <div id="advanced-tabpanel-autonomia" class="rail-tab-panel" role="tabpanel" aria-labelledby="advanced-tab-autonomia">
            <section class="rail-section">
              <div class="panel-head">
                <div>
                  <h3>Autonomia</h3>
                  <p class="muted">Controle do loop, metas em andamento e ferramentas disponíveis.</p>
                </div>
                <button ui-button variant="ghost" size="sm" type="button" (click)="refreshAutonomy()" [disabled]="autonomyLoading() || autonomySaving()">
                  Atualizar
                </button>
              </div>
              @if (autonomyError()) {
                <div class="inline-alert" role="alert">
                  <span class="material-icons">error_outline</span>
                  {{ autonomyError() }}
                </div>
              }
              @if (autonomyNotice(); as notice) {
                <div class="section-notice" [class.is-success]="notice.kind === 'success'" [class.is-info]="notice.kind === 'info'" [class.is-warning]="notice.kind === 'warning'" [class.is-error]="notice.kind === 'error'" role="status" aria-live="polite">
                  <span class="material-icons">{{ notice.kind === 'success' ? 'check_circle' : notice.kind === 'error' ? 'error_outline' : 'info' }}</span>
                  <span>{{ notice.message }}</span>
                </div>
              }
              @if (autonomyLoading()) {
                <app-skeleton variant="text" [count]="4"></app-skeleton>
              } @else {
                <div class="autonomy-card">
                  <div class="autonomy-status">
                    <span class="metric-pill">Loop: {{ autonomyStatus()?.active ? 'Ativo' : 'Inativo' }}</span>
                    <span class="metric-pill">Ciclos: {{ autonomyStatus()?.cycle_count ?? 0 }}</span>
                    <span class="metric-pill">Risco: {{ autonomyStatus()?.config?.risk_profile || 'balanced' }}</span>
                  </div>
                  <div class="autonomy-actions">
                    <button ui-button variant="default" size="sm" type="button" (click)="toggleAutonomyLoop()" [disabled]="autonomySaving()">
                      {{ autonomyStatus()?.active ? 'Parar loop' : 'Iniciar loop' }}
                    </button>
                  </div>
                </div>

                <div class="goal-create-card">
                  <div class="panel-head">
                    <div>
                      <h4>Criar nova meta</h4>
                      <p class="muted section-help">Defina um objetivo curto para o loop autônomo acompanhar.</p>
                    </div>
                  </div>
                  <input
                    type="text"
                    placeholder="Título da meta"
                    [value]="goalCreateTitle()"
                    (input)="onGoalCreateTitleInput($event)" />
                  <textarea
                    rows="2"
                    placeholder="Descrição (opcional)"
                    [value]="goalCreateDescription()"
                    (input)="onGoalCreateDescriptionInput($event)">
                  </textarea>
                  <div class="goal-create-actions">
                    <button ui-button variant="ghost" size="sm" type="button" (click)="createGoal()" [disabled]="goalCreateLoading() || autonomySaving()">
                      {{ goalCreateLoading() ? 'Criando...' : 'Criar meta' }}
                    </button>
                  </div>
                  @if (goalCreateError()) {
                    <p class="muted field-error">{{ goalCreateError() }}</p>
                  }
                </div>

                <div class="autonomy-split">
                  <div class="autonomy-panel-subcard">
                    <div class="panel-head">
                      <h4>Metas ativas</h4>
                      <ui-badge variant="neutral">{{ autonomyActiveGoals().length }}</ui-badge>
                    </div>
                    @if (autonomyActiveGoals().length) {
                      <ul class="rail-list compact">
                        @for (goal of autonomyActiveGoals(); track goal.id) {
                          <li class="rail-item">
                            <p class="item-title">{{ goal.title }}</p>
                            <span class="muted">{{ goalStatusLabel(goal) }}</span>
                            <div class="goal-actions">
                              <button ui-button variant="ghost" size="sm" type="button" (click)="markGoalStatus(goal, 'in_progress')" [disabled]="autonomySaving()">Andamento</button>
                              <button ui-button variant="ghost" size="sm" type="button" (click)="markGoalStatus(goal, 'completed')" [disabled]="autonomySaving()">Concluir</button>
                            </div>
                          </li>
                        }
                      </ul>
                    } @else {
                      <p class="muted">Sem metas ativas.</p>
                    }
                  </div>
                  <div class="autonomy-panel-subcard">
                    <div class="panel-head">
                      <h4>Ferramentas ativas</h4>
                      <ui-badge variant="neutral">{{ autonomyEnabledTools().length }}</ui-badge>
                    </div>
                    @if (autonomyEnabledTools().length) {
                      <div class="tool-chips">
                        @for (tool of autonomyEnabledTools(); track tool.name) {
                          <span class="chip">{{ tool.name }}</span>
                        }
                      </div>
                    } @else {
                      <p class="muted">Nenhuma ferramenta ativa encontrada.</p>
                    }
                  </div>
                </div>
              }
            </section>
          </div>
        }
      </aside>
      }
    </div>
  </div>
</section>
</file>

<file path="app/features/conversations/conversations.scss">
@use 'styles/tokens' as *;
@use 'styles/mixins' as *;

.conversations {
  position: relative;
  min-height: calc(100vh - 64px);
  padding-bottom: 96px;
  display: flex;
  flex-direction: column;
  gap: clamp(20px, 2vw, 32px);
}

.convo-shell {
  max-width: none;
  margin: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: clamp(22px, 2.4vw, 38px);
  padding: clamp(20px, 2.3vw, 48px) clamp(18px, 3.8vw, 84px) 0;
}

.convo-hero {
  display: flex;
  gap: clamp(18px, 2vw, 32px);
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
}

.hero-copy {
  max-width: 78ch;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.eyebrow {
  font-family: $font-mono;
  font-size: 0.7rem;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: $color-text-muted;
}

.sub {
  color: $color-text-secondary;
  font-size: 1rem;
}

.hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.convo-grid {
  display: grid;
  grid-template-columns: minmax(280px, 18%) minmax(0, 1fr) minmax(320px, 24%);
  gap: clamp(16px, 1.8vw, 30px);
  align-items: start;
}

.convo-grid.simple {
  grid-template-columns: minmax(280px, 22%) minmax(0, 1fr);
}

.convo-panel {
  @include glass-panel;
  border-radius: var(--janus-radius-lg);
  padding: clamp(16px, 1.4vw, 26px) clamp(16px, 1.5vw, 28px);
  display: flex;
  flex-direction: column;
  gap: clamp(14px, 1.2vw, 20px);
  position: relative;
  overflow: hidden;
}

.convo-panel::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top right, rgba(var(--janus-secondary-rgb), 0.14), transparent 55%);
  pointer-events: none;
  z-index: 0;
}

.convo-panel > * {
  position: relative;
  z-index: 1;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  position: relative;
  z-index: 1;
}

.convo-list {
  min-height: clamp(520px, 68vh, 920px);
}

.search-row {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: $radius-md;
  background: rgba(var(--janus-bg-surface-rgb), 0.9);
  border: 1px solid rgba(255, 255, 255, 0.08);
  position: relative;
  z-index: 1;
}

.search-row input {
  background: transparent;
  border: none;
  outline: none;
  color: $color-text-primary;
  font-family: $font-body;
  font-size: 0.9rem;
}

.conversation-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0;
  margin: 0;
  position: relative;
  z-index: 1;
  overflow-y: auto;
  max-height: calc(100vh - 320px);
  padding-right: 4px;
}

.conversation-item {
  border-radius: $radius-md;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  transition: $transition-fast;
}

.conversation-trigger {
  width: 100%;
  border: none;
  background: transparent;
  color: inherit;
  padding: 12px;
  border-radius: inherit;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  text-align: left;
  cursor: pointer;
}

.conversation-trigger:focus-visible {
  outline: 2px solid rgba(var(--janus-secondary-rgb), 0.45);
  outline-offset: 2px;
}

.item-content {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.item-tags {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-end;
}

.chip.soft {
  opacity: 0.8;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.conversation-item:hover {
  border-color: rgba(var(--janus-secondary-rgb), 0.5);
  transform: translateY(-1px);
}

.conversation-item.active {
  border-color: rgba(var(--janus-primary-rgb), 0.7);
  box-shadow: 0 0 18px rgba(var(--janus-primary-rgb), 0.2);
}

.chip {
  border: 1px solid rgba(255, 255, 255, 0.08);
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-family: $font-mono;
  color: $color-text-muted;
}

.item-title {
  font-family: $font-display;
  font-size: 0.95rem;
  color: $color-text-primary;
  display: block;
}

.muted {
  color: $color-text-muted;
  font-size: 0.8rem;
}

.convo-main {
  min-height: clamp(640px, 76vh, 980px);
}

.chat-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  position: relative;
  z-index: 1;
}

.title-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.inline-alert {
  display: flex;
  align-items: center;
  gap: 10px;
  border-radius: $radius-md;
  padding: 12px 16px;
  font-size: 0.9rem;
  background: rgba(var(--error-rgb), 0.16);
  border: 1px solid rgba(var(--error-rgb), 0.4);
  position: relative;
  z-index: 1;
}

.chat-body {
  position: relative;
  z-index: 1;
  background: rgba(var(--janus-bg-dark-rgb), 0.2);
  border-radius: $radius-md;
  padding: clamp(14px, 1.2vw, 24px);
  border: 1px solid rgba(255, 255, 255, 0.05);
  min-height: clamp(420px, 56vh, 760px);
  max-height: clamp(520px, 66vh, 980px);
  overflow-y: auto;
}

.message-feed {
  display: flex;
  flex-direction: column;
  gap: clamp(14px, 1.2vw, 22px);
}

.message {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 12px;
  align-items: flex-start;
}

.message.user {
  grid-template-columns: minmax(0, 1fr) auto;
  justify-items: end;
}

.message.user .bubble {
  background: rgba(var(--janus-secondary-rgb), 0.1);
  border-color: rgba(var(--janus-secondary-rgb), 0.35);
}

.message.assistant .bubble {
  background: rgba(var(--janus-bg-surface-rgb), 0.9);
  border-color: rgba(255, 255, 255, 0.08);
}

.message.system .bubble {
  background: rgba(var(--warning-rgb), 0.12);
  border-color: rgba(var(--warning-rgb), 0.3);
}

.message.error .bubble {
  border-color: rgba(var(--error-rgb), 0.5);
}

.avatar-slot {
  display: flex;
  align-items: flex-start;
  justify-content: center;
}

.message.user .avatar-slot {
  order: 2;
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-family: $font-mono;
  font-size: 0.8rem;
  color: $color-text-primary;
  background: linear-gradient(135deg, rgba(var(--janus-primary-rgb), 0.35), rgba(var(--janus-accent-rgb), 0.3));
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.bubble {
  border-radius: 18px;
  padding: 16px 18px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  display: flex;
  flex-direction: column;
  gap: 11px;
}

.message.assistant .bubble,
.message.system .bubble {
  max-width: min(92%, clamp(760px, 56vw, 1120px));
}

.message.user .bubble {
  max-width: min(86%, clamp(620px, 48vw, 900px));
}

.message.user .bubble {
  text-align: right;
  justify-self: end;
}

.message-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-family: $font-mono;
  color: $color-text-muted;
}

.message.user .message-meta {
  justify-content: flex-end;
}

.stream-indicator {
  color: $color-text-secondary;
}

.message-text {
  color: $color-text-primary;
  font-size: 0.95rem;
  line-height: 1.5;
}

.message-runtime {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.runtime-chip {
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.67rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-family: $font-mono;
  color: $color-text-muted;
}

.understanding-card {
  border-radius: 12px;
  border: 1px solid rgba(var(--janus-primary-rgb), 0.25);
  background: rgba(var(--janus-primary-rgb), 0.08);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.understanding-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.understanding-label {
  font-size: 0.72rem;
  font-family: $font-mono;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: $color-text-muted;
}

.understanding-intent {
  border: 1px solid rgba(var(--janus-secondary-rgb), 0.3);
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.7rem;
  color: $color-text-secondary;
}

.understanding-card p {
  margin: 0;
  font-size: 0.85rem;
  color: $color-text-secondary;
}

.understanding-flag {
  font-size: 0.72rem;
  color: $color-text-muted;
}

.confidence-chip {
  border-radius: 999px;
  padding: 2px 8px;
  font-size: 0.68rem;
  font-family: $font-mono;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.confidence-chip.high {
  border-color: rgba(var(--success-rgb), 0.45);
  color: rgba(var(--success-rgb), 1);
}

.confidence-chip.medium {
  border-color: rgba(var(--warning-rgb), 0.45);
  color: rgba(var(--warning-rgb), 1);
}

.confidence-chip.low {
  border-color: rgba(var(--error-rgb), 0.45);
  color: rgba(var(--error-rgb), 1);
}

.citation-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.citation-item {
  border: 1px solid rgba(var(--janus-secondary-rgb), 0.25);
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  overflow: hidden;
}

.citation-item summary::-webkit-details-marker {
  display: none;
}

.citation-chip {
  list-style: none;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(var(--janus-secondary-rgb), 0.25);
  font-size: 0.7rem;
  color: $color-text-secondary;
}

.citation-detail {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.citation-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.citation-detail a {
  color: $color-text-primary;
  text-decoration: underline;
}

.citation-detail pre {
  margin: 0;
  padding: 8px;
  border-radius: 8px;
  background: rgba(var(--janus-bg-dark-rgb), 0.45);
  color: $color-text-secondary;
  font-size: 0.74rem;
  white-space: pre-wrap;
  word-break: break-word;
}

.message-feedback {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
  padding-top: 6px;
  border-top: 1px dashed rgba(255, 255, 255, 0.08);
}

.feedback-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.feedback-actions-inline {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.feedback-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 0.68rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.03);
  color: $color-text-secondary;
}

.feedback-pill .material-icons {
  font-size: 14px;
  width: 14px;
  height: 14px;
}

.feedback-pill.success {
  color: rgba(var(--success-rgb), 1);
  border-color: rgba(var(--success-rgb), 0.25);
  background: rgba(var(--success-rgb), 0.08);
}

.feedback-comment-toggle {
  border: 0;
  background: transparent;
  color: $color-text-muted;
  font-size: 0.74rem;
  padding: 2px 0;
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: rgba(255, 255, 255, 0.12);
  text-underline-offset: 3px;
}

.feedback-comment-toggle:hover:not(:disabled),
.feedback-comment-toggle:focus-visible {
  color: $color-text-secondary;
  text-decoration-color: rgba(var(--janus-secondary-rgb), 0.45);
  outline: none;
}

.feedback-comment-toggle:disabled {
  opacity: 0.5;
  cursor: default;
}

.feedback-comment-box {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.02);
}

.feedback-comment-box textarea {
  width: 100%;
  background: rgba(var(--janus-bg-dark-rgb), 0.28);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: $color-text-primary;
  border-radius: 10px;
  padding: 10px;
  resize: vertical;
  font-size: 0.82rem;
}

.feedback-comment-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.feedback-status.success {
  color: rgba(var(--success-rgb), 1);
}

.feedback-status.error {
  color: rgba(var(--error-rgb), 1);
}

.feedback-error-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.empty-state {
  text-align: center;
  padding: 24px 0;
}

.empty-actions {
  display: flex;
  justify-content: center;
  margin-top: 12px;
}

.quick-prompts {
  margin-top: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.composer {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
  z-index: 1;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
}

.composer-helper {
  margin: 0;
}

.composer-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.composer-toolbar label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.75rem;
  font-family: $font-mono;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: $color-text-muted;
}

.composer-toolbar select {
  background: rgba(var(--janus-bg-surface-rgb), 0.9);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: $radius-md;
  color: $color-text-primary;
  padding: 6px 10px;
  font-family: $font-body;
  text-transform: none;
  letter-spacing: normal;
}

.toggle {
  gap: 6px;
}

.toggle input {
  accent-color: var(--janus-primary);
}

.composer textarea {
  background: rgba(var(--janus-bg-surface-rgb), 0.95);
  border: 1px solid var(--janus-border);
  border-radius: $radius-md;
  padding: 12px 14px;
  color: $color-text-primary;
  font-family: $font-body;
  resize: vertical;
  min-height: 90px;
  transition: $transition-fast;
}

.composer textarea:focus {
  border-color: var(--janus-border-active);
  box-shadow: 0 0 0 2px rgba(var(--janus-secondary-rgb), 0.2);
  outline: none;
}

.composer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.convo-rail {
  gap: 14px;
  max-height: calc(100vh - 220px);
  overflow-y: auto;
  padding-right: 6px;
}

.rail-header {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px;
  border-radius: $radius-md;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background:
    radial-gradient(circle at top right, rgba(var(--janus-secondary-rgb), 0.12), transparent 58%),
    radial-gradient(circle at bottom left, rgba(var(--janus-primary-rgb), 0.1), transparent 62%),
    rgba(255, 255, 255, 0.02);
}

.rail-header h3 {
  font-size: 1rem;
  margin: 0;
}

.rail-subtitle {
  margin: 4px 0 0;
  font-size: 0.76rem;
}

.segmented-tabs {
  display: flex;
  gap: 4px;
  padding: 3px;
  border-radius: 12px;
  background: rgba(var(--janus-bg-dark-rgb), 0.32);
  border: 1px solid rgba(255, 255, 255, 0.06);
  min-width: 0;
  scroll-padding-inline: 4px;
}

.segmented-tab {
  appearance: none;
  border: 0;
  background: transparent;
  color: $color-text-muted;
  font-family: $font-mono;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border-radius: 9px;
  padding: 6px 8px;
  cursor: pointer;
  transition: $transition-fast;
  white-space: nowrap;
}

.segmented-tab:hover {
  color: $color-text-secondary;
  background: rgba(255, 255, 255, 0.03);
}

.segmented-tab:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(var(--janus-secondary-rgb), 0.25);
}

.segmented-tab.active {
  color: $color-text-primary;
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.segmented-tab.customer.docs.active {
  background: rgba(70, 170, 255, 0.12);
  border-color: rgba(70, 170, 255, 0.26);
}

.segmented-tab.customer.memoria.active {
  background: rgba(255, 176, 52, 0.12);
  border-color: rgba(255, 176, 52, 0.24);
}

.segmented-tab.customer.rag.active {
  background: rgba(72, 214, 178, 0.12);
  border-color: rgba(72, 214, 178, 0.24);
}

.rail-tab-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  animation: railTabFadeIn 180ms ease;
}

.rail-tab-panel.nested {
  gap: 8px;
}

@keyframes railTabFadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.explain-card {
  border: 1px solid rgba(var(--janus-primary-rgb), 0.25);
  border-radius: $radius-md;
  background: rgba(var(--janus-primary-rgb), 0.08);
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.explain-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.metric-pill {
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  padding: 3px 8px;
  font-size: 0.66rem;
  font-family: $font-mono;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: $color-text-secondary;
}

.autonomy-status {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.autonomy-actions {
  display: flex;
  gap: 6px;
  align-items: center;
}

.autonomy-split {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.autonomy-split h4 {
  margin: 0;
  font-size: 0.82rem;
  color: $color-text-secondary;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  font-family: $font-mono;
}

.goal-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}

.tool-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.rail-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: relative;
  z-index: 1;
}

.convo-rail .rail-section + .rail-section {
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.rail-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.rail-list.compact {
  gap: 0.45rem;
}

.trace-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  max-height: min(32vh, 420px);
  overflow-y: auto;
  border-left: 2px solid var(--border-subtle);
  padding-left: 0.75rem;

  .trace-item {
    font-size: 0.8rem;
    
    .trace-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 0.25rem;
      
      .agent-badge {
        background: var(--surface-2);
        padding: 0.125rem 0.375rem;
        border-radius: 4px;
        font-weight: 500;
        color: var(--text-secondary);
      }
      
      .trace-time {
        color: var(--text-tertiary);
        font-size: 0.7rem;
      }
    }
    
    .trace-content {
      strong {
        display: block;
        color: var(--primary);
        margin-bottom: 0.125rem;
      }
      p {
        margin: 0;
        color: var(--text-secondary);
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
    }
  }
}

.thought-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: min(34vh, 440px);
  overflow-y: auto;
}

.thought-item {
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.02);
  border-radius: $radius-md;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.thought-item.agent {
  border-color: rgba(var(--janus-secondary-rgb), 0.35);
}

.thought-item.stream {
  border-color: rgba(var(--janus-primary-rgb), 0.35);
}

.thought-item.system {
  border-color: rgba(var(--warning-rgb), 0.35);
}

.thought-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.thought-head strong {
  color: $color-text-primary;
  font-size: 0.78rem;
}

.thought-head .muted {
  margin-left: auto;
}

.thought-icon {
  font-size: 16px;
  width: 16px;
  height: 16px;
  color: $color-text-secondary;
}

.thought-item p {
  margin: 0;
  color: $color-text-secondary;
  font-size: 0.79rem;
}

.rail-item {
  padding: 10px;
  border-radius: $radius-md;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: $color-text-secondary;
  font-size: 0.8rem;
}

.rail-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.section-help {
  margin: 4px 0 0;
  font-size: 0.75rem;
}

.section-help.compact {
  font-size: 0.72rem;
}

.customer-tools .panel-head h3 {
  margin: 0;
}

.customer-tabs {
  overflow-x: auto;
  scrollbar-width: thin;
}

.customer-card {
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
  border-radius: $radius-md;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.customer-card.accent-docs {
  background:
    radial-gradient(circle at 12% 12%, rgba(56, 189, 248, 0.1), transparent 44%),
    rgba(255, 255, 255, 0.02);
  border-color: rgba(56, 189, 248, 0.16);
}

.customer-card.accent-memory {
  background:
    radial-gradient(circle at 18% 8%, rgba(251, 191, 36, 0.1), transparent 48%),
    rgba(255, 255, 255, 0.02);
  border-color: rgba(251, 191, 36, 0.14);
}

.customer-card.accent-rag {
  background:
    radial-gradient(circle at 15% 10%, rgba(34, 197, 94, 0.09), transparent 44%),
    radial-gradient(circle at 85% 20%, rgba(45, 212, 191, 0.09), transparent 46%),
    rgba(255, 255, 255, 0.02);
  border-color: rgba(45, 212, 191, 0.15);
}

.customer-card h4 {
  margin: 0;
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-family: $font-mono;
  color: $color-text-secondary;
}

.customer-subcard {
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 12px;
  padding: 8px;
  background: rgba(var(--janus-bg-dark-rgb), 0.18);
}

.panel-head.compact-head {
  margin-bottom: 2px;
}

.stack-gap-sm {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-family: $font-mono;
  color: $color-text-muted;
}

.inline-form {
  display: flex;
  gap: 6px;
  align-items: center;
}

.inline-form > :is(input, select) {
  min-width: 0;
}

.inline-form.file-form {
  align-items: flex-start;
}

.memory-config-form {
  align-items: stretch;
}

.inline-form input,
.inline-form select,
.customer-card textarea,
.customer-card > input,
.goal-create-card input,
.goal-create-card textarea {
  width: 100%;
  background: rgba(var(--janus-bg-surface-rgb), 0.9);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: $radius-md;
  color: $color-text-primary;
  padding: 7px 9px;
  font-family: $font-body;
  font-size: 0.82rem;
}

.inline-form input:focus,
.inline-form select:focus,
.customer-card textarea:focus,
.goal-create-card input:focus,
.goal-create-card textarea:focus {
  outline: none;
  border-color: rgba(var(--janus-secondary-rgb), 0.45);
  box-shadow: 0 0 0 2px rgba(var(--janus-secondary-rgb), 0.14);
}

.field-error {
  color: rgba(var(--error-rgb), 1);
}

.field-error.is-business {
  color: rgba(var(--warning-rgb), 1);
  border-left: 2px solid rgba(var(--warning-rgb), 0.5);
  padding-left: 6px;
}

.section-notice {
  display: flex;
  align-items: center;
  gap: 6px;
  border-radius: 10px;
  padding: 6px 8px;
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
  color: $color-text-secondary;
  animation: noticeFadeIn 160ms ease;
  font-size: 0.76rem;
}

.section-notice .material-icons {
  width: 16px;
  height: 16px;
  font-size: 16px;
}

.section-notice.is-success {
  border-color: rgba(var(--success-rgb), 0.2);
  background: rgba(var(--success-rgb), 0.07);
  color: rgba(var(--success-rgb), 1);
}

.section-notice.is-info {
  border-color: rgba(var(--janus-secondary-rgb), 0.18);
  background: rgba(var(--janus-secondary-rgb), 0.06);
}

.section-notice.is-warning {
  border-color: rgba(var(--warning-rgb), 0.2);
  background: rgba(var(--warning-rgb), 0.07);
  color: rgba(var(--warning-rgb), 1);
}

.section-notice.is-error {
  border-color: rgba(var(--error-rgb), 0.2);
  background: rgba(var(--error-rgb), 0.07);
  color: rgba(var(--error-rgb), 1);
}

@keyframes noticeFadeIn {
  from {
    opacity: 0;
    transform: translateY(-2px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.progress-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 6px;
  align-items: center;
}

.progress-track {
  width: 100%;
  height: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.05);
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, rgba(var(--janus-secondary-rgb), 0.9), rgba(var(--janus-primary-rgb), 0.9));
  transition: width 180ms ease;
}

.compact-item {
  gap: 4px;
  padding: 8px;
}

.compact-item pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 180px;
  max-width: 100%;
  overflow: auto;
  background: rgba(var(--janus-bg-dark-rgb), 0.25);
  border-radius: 8px;
  padding: 8px;
}

.doc-search-item,
.doc-library-item {
  gap: 4px;
}

.doc-action-row {
  align-items: center;
  gap: 8px;
}

.doc-meta-line {
  font-size: 0.71rem;
}

.doc-snippet {
  margin: 2px 0 0;
  color: $color-text-secondary;
  font-size: 0.76rem;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.rag-result-card {
  border: 1px solid rgba(var(--janus-primary-rgb), 0.2);
  background: rgba(var(--janus-primary-rgb), 0.05);
  border-radius: 10px;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rag-result-head {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.rag-view-tabs {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  padding: 3px;
  border-radius: 10px;
  background: rgba(var(--janus-bg-dark-rgb), 0.24);
  border: 1px solid rgba(255, 255, 255, 0.05);
  min-width: 0;
  scroll-padding-inline: 4px;
}

.confirmation-card {
  border-color: rgba(217, 119, 6, 0.35);
  background: rgba(245, 158, 11, 0.08);
}

.confirmation-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.citation-status-inline {
  margin-top: 8px;
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.rag-view-tab {
  appearance: none;
  border: 1px solid transparent;
  background: transparent;
  color: $color-text-muted;
  font-size: 0.72rem;
  padding: 5px 7px;
  border-radius: 8px;
  cursor: pointer;
  transition: $transition-fast;
}

.rag-view-tab:hover {
  color: $color-text-secondary;
  background: rgba(255, 255, 255, 0.03);
}

.rag-view-tab:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(var(--janus-secondary-rgb), 0.18);
}

.rag-view-tab.active {
  color: $color-text-primary;
  border-color: rgba(255, 255, 255, 0.08);
  background: rgba(var(--janus-primary-rgb), 0.08);
}

.rag-view-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  overflow: hidden;
}

.rag-result-empty {
  margin: 0;
}

.rag-section-list {
  gap: 0.4rem;
}

.rag-result-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.rag-raw-details {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding-top: 8px;
}

.rag-raw-details > summary {
  cursor: pointer;
  color: $color-text-secondary;
  font-size: 0.78rem;
}

.rag-mode-hint {
  margin: 0;
  font-size: 0.75rem;
}

.autonomy-card {
  border: 1px solid rgba(var(--janus-primary-rgb), 0.12);
  background:
    radial-gradient(circle at top right, rgba(var(--janus-primary-rgb), 0.08), transparent 56%),
    rgba(255, 255, 255, 0.02);
  border-radius: $radius-md;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.goal-create-card {
  border: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.02);
  border-radius: $radius-md;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.autonomy-panel-subcard {
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: $radius-md;
  background: rgba(255, 255, 255, 0.02);
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.memory-config-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.memory-config-group .field-label {
  margin: 0;
}

.memory-list-item {
  gap: 4px;
}

.memory-content {
  margin: 0;
  color: $color-text-secondary;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.memory-meta-line {
  font-size: 0.71rem;
}

.goal-create-actions {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
}

@media (max-width: 1200px) {
  .convo-shell {
    padding-inline: clamp(16px, 3vw, 32px);
  }

  .convo-grid {
    grid-template-columns: minmax(220px, 1fr) minmax(0, 2fr);
  }

  .convo-grid.simple {
    grid-template-columns: minmax(220px, 1fr) minmax(0, 2fr);
  }

  .convo-rail {
    grid-column: span 2;
    max-height: none;
    overflow: visible;
    padding-right: 0;
  }

  .convo-list {
    min-height: 420px;
  }

  .convo-main {
    min-height: 0;
  }

  .inline-form {
    flex-wrap: wrap;
  }

  .doc-action-row {
    align-items: flex-start;
    flex-wrap: wrap;
  }
}

@media (max-width: 900px) {
  .convo-shell {
    padding-inline: clamp(14px, 4vw, 24px);
  }

  .convo-grid {
    grid-template-columns: 1fr;
  }

  .convo-rail {
    grid-column: span 1;
  }

  .conversation-list {
    max-height: 360px;
  }

  .chat-body {
    min-height: 320px;
    max-height: 52vh;
  }

  .convo-rail {
    max-height: none;
    overflow: visible;
    padding-right: 0;
  }

  .conversation-trigger {
    align-items: flex-start;
  }

  .item-tags {
    align-items: flex-start;
    flex-direction: row;
  }

  .segmented-tabs {
    overflow-x: auto;
    scrollbar-width: thin;
    -webkit-overflow-scrolling: touch;
    scroll-snap-type: x proximity;
  }

  .segmented-tab {
    flex: 0 0 auto;
    scroll-snap-align: start;
  }

  .feedback-row {
    align-items: flex-start;
  }

  .feedback-error-row {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .inline-form {
    flex-direction: column;
    align-items: stretch;
  }

  .inline-form.file-form {
    align-items: stretch;
  }

  .progress-row {
    grid-template-columns: 1fr;
  }

  .rag-view-tabs {
    overflow-x: auto;
    flex-wrap: nowrap;
    -webkit-overflow-scrolling: touch;
    scroll-snap-type: x proximity;
  }

  .rag-view-tab {
    flex: 0 0 auto;
    scroll-snap-align: start;
  }

  .doc-action-row {
    flex-direction: column;
    align-items: stretch;
  }

  .doc-action-row > * {
    width: 100%;
  }

  .goal-actions {
    align-items: stretch;
  }

  .goal-actions > * {
    flex: 1 1 140px;
  }

  .compact-item pre {
    max-height: 160px;
  }
}

@media (max-width: 720px) {
  .chat-head {
    flex-direction: column;
    align-items: flex-start;
  }

  .composer-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .message.assistant .bubble,
  .message.system .bubble,
  .message.user .bubble {
    max-width: 100%;
  }
}

@media (min-width: 1800px) {
  .convo-shell {
    padding-inline: clamp(36px, 3.8vw, 120px);
  }

  .convo-grid {
    grid-template-columns: minmax(320px, 17%) minmax(0, 1fr) minmax(360px, 22%);
    gap: clamp(22px, 1.8vw, 40px);
  }

  .convo-grid.simple {
    grid-template-columns: minmax(320px, 19%) minmax(0, 1fr);
  }
}

@media (min-width: 2400px) {
  .convo-shell {
    padding-inline: clamp(52px, 4.6vw, 180px);
  }

  .convo-grid {
    grid-template-columns: minmax(340px, 16%) minmax(0, 1fr) minmax(380px, 20%);
  }
}
</file>

<file path="app/features/conversations/conversations.spec.ts">
import { CUSTOM_ELEMENTS_SCHEMA, provideZonelessChangeDetection, signal } from '@angular/core'
import { TestBed } from '@angular/core/testing'
import { provideHttpClient } from '@angular/common/http'
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router'
import { BehaviorSubject, of } from 'rxjs'
import { vi } from 'vitest'

import { AuthService } from '../../core/auth/auth.service'
import { AgentEventsService } from '../../core/services/agent-events.service'
import { Header } from '../../core/layout/header/header'
import { ChatStreamService } from '../../services/chat-stream.service'
import { BackendApiService } from '../../services/backend-api.service'
import { ConversationsComponent } from './conversations'

describe('ConversationsComponent', () => {
  let routeParams$: BehaviorSubject<ReturnType<typeof convertToParamMap>>
  let routerNavigateSpy: ReturnType<typeof vi.fn>
  let apiStub: Record<string, ReturnType<typeof vi.fn>>

  beforeEach(async () => {
    routeParams$ = new BehaviorSubject(convertToParamMap({ conversationId: 'legacy' }))
    routerNavigateSpy = vi.fn()
    apiStub = {
      listConversations: vi.fn(() => of({ conversations: [] })),
      startChat: vi.fn(() => of({ conversation_id: 'fresh' })),
      getChatHistoryPaginated: vi.fn(() => of({ conversation_id: 'legacy', messages: [] })),
      listDocuments: vi.fn(() => of({ items: [] })),
      getMemoryTimeline: vi.fn(() => of([])),
      getAutonomyStatus: vi.fn(() => of(null)),
      listGoals: vi.fn(() => of([])),
      getTools: vi.fn(() => of({ tools: [] })),
      getConversationTrace: vi.fn(() => of([]))
    }

    await TestBed.configureTestingModule({
      imports: [ConversationsComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideHttpClient(),
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            user: signal({ id: 2, name: 'arthur' }),
            isAdmin: signal(true)
          }
        },
        {
          provide: ActivatedRoute,
          useValue: {
            paramMap: routeParams$.asObservable()
          }
        },
        {
          provide: Router,
          useValue: {
            navigate: routerNavigateSpy
          }
        },
        {
          provide: AgentEventsService,
          useValue: {
            events$: of([]),
            connect: vi.fn(),
            disconnect: vi.fn()
          }
        },
        {
          provide: ChatStreamService,
          useValue: {
            status: vi.fn(() => of('idle')),
            typing: vi.fn(() => of(false)),
            partials: vi.fn(() => of()),
            done: vi.fn(() => of()),
            errors: vi.fn(() => of()),
            cognitive: vi.fn(() => of('')),
            toolStatus: vi.fn(() => of('')),
            start: vi.fn(),
            stop: vi.fn()
          }
        },
        {
          provide: BackendApiService,
          useValue: apiStub
        }
      ]
    })
      .overrideComponent(ConversationsComponent, {
        remove: { imports: [Header] },
        add: { schemas: [CUSTOM_ELEMENTS_SCHEMA] }
      })
      .compileComponents()
  })

  it('clears stale state and loads the new conversation when creating from an active thread', async () => {
    const fixture = TestBed.createComponent(ConversationsComponent)
    const component = fixture.componentInstance as any
    fixture.detectChanges()

    component.messages.set([
      { id: 'old-message', role: 'assistant', text: 'legacy state', timestamp: Date.now() }
    ])
    component.docs.set([{ doc_id: 'doc-legacy', chunks: 1, conversation_id: 'legacy' }])
    component.memoryUser.set([{ id: 'mem-legacy' }])

    await component.createConversation()

    expect(component.selectedId()).toBe('fresh')
    expect(component.messages()).toEqual([])
    expect(component.docs()).toEqual([])
    expect(component.memoryUser()).toEqual([])
    expect(apiStub.getChatHistoryPaginated).toHaveBeenCalledWith('fresh', { limit: 80, offset: 0 })
    expect(apiStub.listDocuments).toHaveBeenCalledWith('fresh', '2')
    expect(routerNavigateSpy).toHaveBeenCalledWith(['/conversations', 'fresh'], { replaceUrl: true })
  })

  it('reconciles resolved pending actions when history already contains the system approval message', () => {
    apiStub.getChatHistoryPaginated.mockReturnValue(
      of({
        conversation_id: 'legacy',
        messages: [
          {
            id: 'assistant-1',
            role: 'assistant',
            text: 'Resposta aguardando aprovação',
            timestamp: Date.now(),
            confirmation: {
              required: true,
              reason: 'high_risk',
              pending_action_id: 42,
              approve_endpoint: '/api/v1/pending_actions/action/42/approve',
              reject_endpoint: '/api/v1/pending_actions/action/42/reject'
            },
            agent_state: {
              state: 'waiting_confirmation',
              requires_confirmation: true,
              reason: 'high_risk'
            }
          },
          {
            id: 'system-1',
            role: 'system',
            text: 'Ação pendente #42 aprovada. Action approved.',
            timestamp: Date.now() + 1
          }
        ]
      })
    )

    const fixture = TestBed.createComponent(ConversationsComponent)
    const component = fixture.componentInstance
    fixture.detectChanges()

    const assistant = component.messages().find((msg) => msg.role === 'assistant')
    expect(assistant?.confirmation?.required).toBe(false)
    expect(assistant?.confirmation?.status).toBe('approved')
    expect(assistant?.confirmation?.approve_endpoint).toBeUndefined()
    expect(assistant?.agent_state?.state).toBe('completed')
    expect(assistant?.agent_state?.reason).toBe('approved')
  })
})
</file>

<file path="app/features/conversations/conversations.ts">
import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, ViewChild, computed, inject, signal } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormControl, ReactiveFormsModule } from '@angular/forms'
import { ActivatedRoute, Router } from '@angular/router'
import { firstValueFrom, forkJoin, of } from 'rxjs'
import { catchError, map } from 'rxjs/operators'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import { Observable } from 'rxjs'

import { AuthService } from '../../core/auth/auth.service'
import { AgentEvent, AgentEventsService } from '../../core/services/agent-events.service'
import { ChatStreamService, StreamDone } from '../../services/chat-stream.service'
import {
  BackendApiService,
  ChatAgentState,
  ChatConfirmationState,
  ChatMessage,
  ChatStudyJobRef,
  ChatStudyJobResponse,
  ChatUnderstanding,
  ConversationMeta,
  CitationStatus,
  DocListItem,
  DocSearchResultItem,
  FeedbackQuickResponse,
  GenerativeMemoryItem,
  MemoryItem,
  PendingAction,
  Citation,
  AutonomyStatusResponse,
  Goal,
  RagHybridResponse,
  RagSearchResponse,
  RagUserChatResponse,
  RagUserChatV2Response,
  Tool
} from '../../services/backend-api.service'
import { Header } from '../../core/layout/header/header'
import { UiButtonComponent } from '../../shared/components/ui/button/button.component'
import { UiBadgeComponent } from '../../shared/components/ui/ui-badge/ui-badge.component'
import { JarvisAvatarComponent } from '../../shared/components/jarvis-avatar/jarvis-avatar.component'
import { SkeletonComponent } from '../../shared/components/skeleton/skeleton.component'
import { MarkdownPipe } from '../../shared/pipes/markdown.pipe'
import { parseAdminCodeQaCommand } from './admin-code-qa.util'

type ChatRole = 'user' | 'assistant' | 'system' | 'event'

interface ChatMessageView {
  id: string
  backendMessageId?: string
  role: ChatRole
  text: string
  timestamp: number
  estimated_wait_seconds?: number
  estimated_wait_range_seconds?: number[]
  processing_profile?: string
  processing_notice?: string
  citations?: Citation[]
  understanding?: ChatUnderstanding
  citation_status?: CitationStatus
  confirmation?: ChatConfirmationState
  agent_state?: ChatAgentState
  latency_ms?: number
  provider?: string
  model?: string
  delivery_status?: string
  failure_classification?: string
  streaming?: boolean
  error?: boolean
}

type ThoughtKind = 'agent' | 'stream' | 'system'

interface ThoughtStreamItem {
  id: string
  kind: ThoughtKind
  title: string
  text: string
  timestamp: number
}

type RagMode = 'search' | 'user-chat' | 'user_chat' | 'hybrid_search' | 'productivity'
type AdvancedRailTab = 'insights' | 'cliente' | 'autonomia'
type CustomerTab = 'docs' | 'memoria' | 'rag'
type TabGroup = 'advancedRail' | 'customer' | 'ragResult'
type RailNoticeKind = 'success' | 'info' | 'warning' | 'error'
type RailNoticeSection = 'docs' | 'memory' | 'rag' | 'autonomy'
type RagResultViewTab = 'resposta' | 'fontes' | 'raw'

interface FeedbackUiState {
  rating?: 'positive' | 'negative'
  commentOpen?: boolean
  submitting?: boolean
  submitted?: boolean
  error?: string
  serverMessage?: string
}

interface RagUiResult {
  mode: RagMode
  answer?: string
  citations?: Citation[]
  results?: Record<string, unknown>[]
}

interface RailNotice {
  kind: RailNoticeKind
  message: string
  visible: boolean
}

interface RoleOption {
  value: string
  label: string
}

interface PriorityOption {
  value: string
  label: string
}

type GoalStatus = 'pending' | 'in_progress' | 'completed' | 'failed'
type PendingActionResolution = 'approved' | 'rejected'

@Component({
  selector: 'app-conversations',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    Header,
    UiButtonComponent,
    UiBadgeComponent,
    JarvisAvatarComponent,
    SkeletonComponent,
    MarkdownPipe
  ],
  templateUrl: './conversations.html',
  styleUrls: ['./conversations.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ConversationsComponent {
  private static readonly PENDING_ACTION_RESOLUTION_RE =
    /a[cç][aã]o pendente\s+#(\d+)\s+(aprovada|rejeitada)\b/i

  private api = inject(BackendApiService)
  private auth = inject(AuthService)
  private route = inject(ActivatedRoute)
  private router = inject(Router)
  private destroyRef = inject(DestroyRef)
  private eventsService = inject(AgentEventsService)
  private stream = inject(ChatStreamService)

  @ViewChild('messageList') messageList?: ElementRef<HTMLDivElement>

  readonly prompt = new FormControl('', { nonNullable: true })
  readonly listLoading = signal(true)
  readonly historyLoading = signal(false)
  readonly contextLoading = signal(false)
  readonly sending = signal(false)
  readonly error = signal('')
  readonly search = signal('')

  readonly conversations = signal<ConversationMeta[]>([])
  readonly messages = signal<ChatMessageView[]>([])
  readonly events = signal<AgentEvent[]>([])
  readonly docs = signal<DocListItem[]>([])
  readonly memoryUser = signal<MemoryItem[]>([])
  readonly docSearchResults = signal<DocSearchResultItem[]>([])
  readonly generativeMemoryResults = signal<GenerativeMemoryItem[]>([])
  readonly ragResult = signal<RagUiResult | null>(null)
  readonly docsNotice = signal<RailNotice | null>(null)
  readonly memoryNotice = signal<RailNotice | null>(null)
  readonly ragNotice = signal<RailNotice | null>(null)
  readonly autonomyNotice = signal<RailNotice | null>(null)

  readonly selectedId = signal<string | null>(null)
  readonly streamStatus = signal('idle')
  readonly streamTyping = signal(false)
  readonly selectedRole = signal('orchestrator')
  readonly selectedPriority = signal('fast_and_cheap')
  readonly streamingEnabled = signal(true)
  readonly latestCognitiveState = signal<string>('')
  readonly latestToolStatus = signal<string>('')
  readonly pendingActionLoading = signal<Record<number, boolean>>({})
  readonly showAdvanced = signal(false)
  readonly advancedRailTab = signal<AdvancedRailTab>('cliente')
  readonly customerTab = signal<CustomerTab>('docs')
  readonly copiedCitation = signal('')
  readonly autonomyLoading = signal(false)
  readonly autonomySaving = signal(false)
  readonly autonomyStatus = signal<AutonomyStatusResponse | null>(null)
  readonly autonomyGoals = signal<Goal[]>([])
  readonly autonomyTools = signal<Tool[]>([])
  readonly autonomyError = signal('')
  readonly goalCreateTitle = signal('')
  readonly goalCreateDescription = signal('')
  readonly goalCreateLoading = signal(false)
  readonly goalCreateError = signal('')

  readonly docUploadInFlight = signal(false)
  readonly docUploadProgress = signal<number | null>(null)
  readonly docUploadError = signal('')
  readonly docLinkUrl = signal('')
  readonly docLinkLoading = signal(false)
  readonly docLinkError = signal('')
  readonly docSearchQuery = signal('')
  readonly docSearchLoading = signal(false)
  readonly docSearchError = signal('')
  readonly deletingDocIds = signal<Record<string, boolean>>({})

  readonly memoryDraft = signal('')
  readonly memoryImportance = signal<number | null>(null)
  readonly memoryType = signal('episodic')
  readonly memoryAddLoading = signal(false)
  readonly memoryAddError = signal('')
  readonly memorySearchQuery = signal('')
  readonly memorySearchLimit = signal(5)
  readonly memorySearchLoading = signal(false)
  readonly memorySearchError = signal('')

  readonly ragMode = signal<RagMode>('hybrid_search')
  readonly ragQuery = signal('')
  readonly ragLoading = signal(false)
  readonly ragError = signal('')
  readonly ragResultViewTab = signal<RagResultViewTab>('resposta')

  readonly feedbackStateByMessageId = signal<Record<string, FeedbackUiState>>({})
  readonly feedbackCommentDraftByMessageId = signal<Record<string, string>>({})

  readonly selectedUploadFile = signal<File | null>(null)
  private readonly advancedRailTabOrder: AdvancedRailTab[] = ['insights', 'cliente', 'autonomia']
  private readonly customerTabOrder: CustomerTab[] = ['docs', 'memoria', 'rag']
  private readonly ragResultTabOrder: RagResultViewTab[] = ['resposta', 'fontes', 'raw']

  readonly roleOptions: RoleOption[] = [
    { value: 'orchestrator', label: 'Orchestrator' },
    { value: 'reasoner', label: 'Reasoner' },
    { value: 'code_generator', label: 'Code Generator' },
    { value: 'knowledge_curator', label: 'Knowledge Curator' },
    { value: 'security_auditor', label: 'Security Auditor' }
  ]

  readonly priorityOptions: PriorityOption[] = [
    { value: 'fast_and_cheap', label: 'Fast + Cheap' },
    { value: 'high_quality', label: 'High Quality' },
    { value: 'local_only', label: 'Local Only' }
  ]

  readonly user = this.auth.user
  readonly isAdmin = this.auth.isAdmin

  readonly displayName = computed(() => {
    const user = this.user()
    return user?.display_name || user?.username || user?.email || 'Operador'
  })

  readonly filteredConversations = computed(() => {
    const term = this.search().trim().toLowerCase()
    const items = this.conversations()
      .slice()
      .sort((a, b) => this.conversationUpdatedAt(b) - this.conversationUpdatedAt(a))
    if (!term) return items
    return items.filter((conv) => {
      const title = String(conv.title || '')
      const id = String(conv.conversation_id || '')
      return title.toLowerCase().includes(term) || id.toLowerCase().includes(term)
    })
  })

  readonly selectedConversation = computed(() => {
    const id = this.selectedId()
    if (!id) return null
    return this.conversations().find((conv) => conv.conversation_id === id) || null
  })

  readonly isSimpleMode = computed(() => !this.showAdvanced())
  readonly latestAssistantMessage = computed(() => {
    const items = this.messages()
    for (let idx = items.length - 1; idx >= 0; idx -= 1) {
      if (items[idx].role === 'assistant') return items[idx]
    }
    return null
  })
  readonly conversationMemory = computed(() => {
    const conversationId = this.selectedId()
    const items = this.memoryUser()
    if (!conversationId) return []
    return items
      .filter((item) => this.isConversationMemory(item, conversationId))
      .slice(0, 6)
  })
  readonly userMemory = computed(() => {
    const conversationId = this.selectedId()
    const items = this.memoryUser()
    const filtered = conversationId
      ? items.filter((item) => !this.isConversationMemory(item, conversationId))
      : items
    return filtered.slice(0, 6)
  })
  readonly autonomyActiveGoals = computed(() => this.autonomyGoals()
    .filter((goal) => goal.status === 'pending' || goal.status === 'in_progress')
    .slice(0, 6))
  readonly autonomyEnabledTools = computed(() => this.autonomyTools()
    .filter((tool) => tool.enabled !== false)
    .slice(0, 8))
  readonly hasConversationSelected = computed(() => Boolean(this.selectedId()))

  readonly selectedTitle = computed(() => {
    const selected = this.selectedConversation()
    if (selected?.title) return selected.title
    const id = this.selectedId()
    if (!id) return 'Nova conversa'
    return `Conversa ${id.slice(0, 8)}`
  })

  readonly avatarState = computed(() => {
    if (this.streamTyping()) return 'speaking'
    const status = this.streamStatus()
    if (status === 'connecting' || status === 'retrying' || status === 'open') return 'thinking'
    return 'idle'
  })

  readonly streamBadge = computed(() => {
    const status = this.streamStatus()
    if (status === 'streaming') return { label: 'Streaming', variant: 'success' as const }
    if (status === 'connecting' || status === 'retrying') return { label: 'Conectando', variant: 'warning' as const }
    if (status === 'error') return { label: 'Erro', variant: 'error' as const }
    if (status === 'open') return { label: 'Pronto', variant: 'info' as const }
    return { label: 'Aguardando', variant: 'neutral' as const }
  })

  private streamingBuffer = ''
  private streamingMessageId: string | null = null
  private streamingConversationId: string | null = null
  private pendingConversationRouteId: string | null = null
  private scrollQueued = false
  private responseStartedAt: number | null = null
  private readonly noticeTimers = new Map<RailNoticeSection, ReturnType<typeof setTimeout>>()
  private readonly studyPollTimers = new Map<string, ReturnType<typeof setTimeout>>()
  readonly quickPrompts = [
    'Resuma esta conversa em 5 pontos.',
    'Quais sao os proximos passos recomendados para este tema?',
    'Me explique de forma simples, sem jargao tecnico.'
  ]

  constructor() {
    this.restoreAdvancedModePreference()
    this.restoreRailTabPreferences()
    this.loadConversations()

    this.route.paramMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((params) => {
        const id = params.get('conversationId')
        this.selectConversation(id)
      })

    this.stream.status()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((status) => this.handleStreamStatus(status))

    this.stream.typing()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((typing) => this.streamTyping.set(typing))

    this.stream.partials()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((partial) => this.handleStreamPartial(partial.text))

    this.stream.done()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((done) => this.handleStreamDone(done))

    this.stream.errors()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((err) => this.handleStreamError(err.error))

    this.stream.cognitive()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((evt) => {
        const state = String(evt?.state || '')
        this.latestCognitiveState.set(state)
        if (state) {
          this.appendThought('agent', 'Estado cognitivo', this.cognitiveStatusText(state, evt.reason))
        }
      })

    this.stream.toolStatus()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((evt) => {
        const label = [evt.status, evt.tool_name].filter(Boolean).join(' · ')
        this.latestToolStatus.set(label)
        if (label) {
          this.appendThought('agent', 'Ferramenta', label)
        }
      })

    this.eventsService.events$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((event) => {
        this.events.update((items) => [event, ...items].slice(0, 24))
        this.appendThought('agent', event.agent_role || 'agent', event.content || 'evento sem descricao', event.timestamp)
      })

    this.destroyRef.onDestroy(() => {
      this.noticeTimers.forEach((timer) => clearTimeout(timer))
      this.noticeTimers.clear()
      this.studyPollTimers.forEach((timer) => clearTimeout(timer))
      this.studyPollTimers.clear()
      this.eventsService.disconnect()
      this.stream.stop()
    })
  }

  async sendMessage(): Promise<void> {
    if (this.sending()) return
    const message = this.prompt.value.trim()
    if (!message) return
    this.error.set('')
    this.sending.set(true)

    const conversationId = await this.ensureConversationId(false, false)
    if (!conversationId) {
      this.error.set('Falha ao criar conversa.')
      this.sending.set(false)
      return
    }

    const now = Date.now()
    this.appendMessage({
      id: this.createId(),
      role: 'user',
      text: message,
      timestamp: now
    })
    this.updateConversationPreview(conversationId, 'user', message, now)
    this.prompt.setValue('')
    this.queueScroll()
    this.responseStartedAt = Date.now()

    const adminCodeQa = parseAdminCodeQaCommand(message, this.isAdmin())
    if (adminCodeQa.enabled) {
      if (!adminCodeQa.question) {
        const nowHelp = Date.now()
        const helpText = 'Para consultar codigo no modo admin, use: /code sua pergunta.'
        this.appendMessage({
          id: this.createId(),
          role: 'assistant',
          text: helpText,
          timestamp: nowHelp
        })
        this.updateConversationPreview(conversationId, 'assistant', helpText, nowHelp)
        this.sending.set(false)
        this.flushPendingConversationNavigation(conversationId)
        this.queueScroll()
        return
      }

      this.sendAdminCodeQa(conversationId, adminCodeQa.question)
      return
    }

    if (this.streamingEnabled()) {
      this.startStreaming(conversationId, message)
    } else {
      this.sendClassic(conversationId, message)
    }
  }

  onComposerKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      this.sendMessage()
    }
  }

  clearComposer(): void {
    this.prompt.setValue('')
  }

  onSearchChange(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.search.set(target?.value || '')
  }

  clearSearch(): void {
    this.search.set('')
  }

  refresh(): void {
    this.loadConversations()
    const id = this.selectedId()
    if (id) {
      this.loadHistory(id)
      this.loadContext(id)
    }
  }

  openConversation(conv: ConversationMeta): void {
    if (!conv?.conversation_id) return
    this.router.navigate(['/conversations', conv.conversation_id])
  }

  async createConversation(): Promise<void> {
    if (this.sending()) return
    this.sending.set(true)
    const id = await this.ensureConversationId(true)
    if (!id) this.error.set('Falha ao criar conversa.')
    this.sending.set(false)
  }

  formatTime(timestamp?: number): string {
    if (!timestamp) return '--:--'
    return new Date(timestamp).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  }

  formatDate(timestamp?: number): string {
    if (!timestamp) return '--'
    return new Date(timestamp).toLocaleDateString('pt-BR', { day: '2-digit', month: 'short' })
  }

  formatLatency(latencyMs?: number): string {
    if (!latencyMs || latencyMs <= 0) return '--'
    if (latencyMs < 1000) return `${Math.round(latencyMs)} ms`
    return `${(latencyMs / 1000).toFixed(1)} s`
  }

  conversationPreviewText(conv: ConversationMeta): string {
    const text = this.sanitizeChatText(conv.last_message?.text || '')
    if (!text) return 'Sem mensagens ainda'
    return text.length > 110 ? `${text.slice(0, 110)}...` : text
  }

  conversationLastActivity(conv: ConversationMeta): string {
    const ts = this.conversationUpdatedAt(conv)
    if (!ts) return '--'
    const now = Date.now()
    if (Math.abs(now - ts) < 24 * 60 * 60 * 1000) return this.formatTime(ts)
    return this.formatDate(ts)
  }

  assistantRuntimeLabel(message: ChatMessageView): string {
    const provider = String(message.provider || '').trim()
    const model = String(message.model || '').trim()
    if (provider && model) return `${provider} / ${model}`
    if (provider) return provider
    if (model) return model
    return 'motor padrao'
  }

  authorLabel(message: ChatMessageView): string {
    if (message.role === 'assistant') return 'Janus'
    if (message.role === 'system') return 'Sistema'
    return this.displayName()
  }

  understandingIntentLabel(understanding?: ChatUnderstanding): string {
    const intent = String(understanding?.intent || '')
    if (intent === 'reminder') return 'Lembrete'
    if (intent === 'documentation_query') return 'Consulta de documentação'
    if (intent === 'action_request') return 'Solicitação de ação'
    if (intent === 'question') return 'Pergunta'
    return 'Geral'
  }

  understandingConfidence(understanding?: ChatUnderstanding): string {
    const confidence = Number(understanding?.confidence ?? 0)
    if (!Number.isFinite(confidence) || confidence <= 0) return '--'
    return `${Math.round(confidence * 100)}%`
  }

  understandingConfidenceBand(understanding?: ChatUnderstanding): 'high' | 'medium' | 'low' {
    const band = String(understanding?.confidence_band || '').toLowerCase()
    if (band === 'high' || band === 'medium' || band === 'low') return band
    const confidence = Number(understanding?.confidence ?? 0)
    if (confidence >= 0.8) return 'high'
    if (confidence >= 0.6) return 'medium'
    return 'low'
  }

  understandingConfidenceLabel(understanding?: ChatUnderstanding): string {
    const band = this.understandingConfidenceBand(understanding)
    if (band === 'high') return 'Confianca alta'
    if (band === 'medium') return 'Confianca media'
    return 'Confianca baixa'
  }

  citationTitle(cite: Citation): string {
    const base = cite.file_path || cite.title || cite.doc_id || 'fonte'
    const line = this.citationLine(cite)
    return line ? `${base}:${line}` : base
  }

  citationLine(cite: Citation): string {
    const start = cite.line_start ?? cite.line
    const end = cite.line_end
    if (start == null && end == null) return ''
    if (start != null && end != null && String(start) !== String(end)) {
      return `${start}-${end}`
    }
    return String(start ?? end ?? '')
  }

  citationScore(cite: Citation): string {
    const score = Number(cite.score)
    if (!Number.isFinite(score) || score <= 0) return '--'
    return `${Math.round(score * 100)}%`
  }

  citationReference(cite: Citation): string {
    const line = this.citationLine(cite)
    const base = cite.file_path || cite.title || cite.doc_id || 'fonte'
    if (!line) return base
    return `${base}:${line}`
  }

  copyCitation(cite: Citation): void {
    const reference = this.citationReference(cite)
    const clipboard = typeof navigator !== 'undefined' ? navigator.clipboard : null
    if (!clipboard?.writeText) return
    clipboard.writeText(reference).then(() => {
      this.copiedCitation.set(reference)
      setTimeout(() => {
        if (this.copiedCitation() === reference) {
          this.copiedCitation.set('')
        }
      }, 1400)
    }).catch(() => {
      this.copiedCitation.set('')
    })
  }

  confirmLowConfidence(): void {
    this.prompt.setValue('Confirmo. Pode prosseguir com a acao solicitada.')
  }

  toggleAdvanced(): void {
    this.showAdvanced.update((value) => {
      const next = !value
      this.persistAdvancedModePreference(next)
      return next
    })
  }

  useQuickPrompt(text: string): void {
    this.prompt.setValue(text)
  }

  setAdvancedRailTab(tab: AdvancedRailTab): void {
    this.advancedRailTab.set(tab)
    this.persistRailTabPreference(this.advancedRailTabStorageKey, tab)
  }

  onAdvancedRailTabKeydown(event: KeyboardEvent): void {
    this.moveTabSelection<AdvancedRailTab>(
      event,
      this.advancedRailTab(),
      this.advancedRailTabOrder,
      (tab) => this.setAdvancedRailTab(tab),
      'advancedRail'
    )
  }

  setCustomerTab(tab: CustomerTab): void {
    this.customerTab.set(tab)
    this.persistRailTabPreference(this.customerTabStorageKey, tab)
  }

  onCustomerTabKeydown(event: KeyboardEvent): void {
    this.moveTabSelection<CustomerTab>(
      event,
      this.customerTab(),
      this.customerTabOrder,
      (tab) => this.setCustomerTab(tab),
      'customer'
    )
  }

  onDocLinkInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.docLinkUrl.set(target?.value || '')
  }

  onDocSearchInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.docSearchQuery.set(target?.value || '')
  }

  onMemoryDraftInput(event: Event): void {
    const target = event.target as HTMLTextAreaElement | null
    this.memoryDraft.set(target?.value || '')
  }

  onMemoryImportanceInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    const raw = target?.value?.trim() || ''
    if (!raw) {
      this.memoryImportance.set(null)
      return
    }
    const n = Number(raw)
    this.memoryImportance.set(Number.isFinite(n) ? n : null)
  }

  onMemoryTypeChange(event: Event): void {
    const target = event.target as HTMLSelectElement | null
    this.memoryType.set(target?.value || 'episodic')
  }

  onMemorySearchQueryInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.memorySearchQuery.set(target?.value || '')
  }

  onRagQueryInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.ragQuery.set(target?.value || '')
  }

  onRagModeChange(event: Event): void {
    const target = event.target as HTMLSelectElement | null
    const value = (target?.value || 'hybrid_search') as RagMode
    this.ragMode.set(value)
  }

  ragModeLabel(mode: RagMode): string {
    if (mode === 'hybrid_search') return 'Híbrido (Vetor + Grafo)'
    if (mode === 'search') return 'Busca vetorial'
    if (mode === 'user-chat') return 'Chat pessoal (v1)'
    if (mode === 'user_chat') return 'Chat pessoal (v2)'
    return 'Produtividade'
  }

  ragModeHint(mode: RagMode): string {
    if (mode === 'hybrid_search') return 'Combina busca vetorial e grafo para contexto mais completo.'
    if (mode === 'search') return 'Busca vetorial direta em documentos e memória indexada.'
    if (mode === 'user-chat') return 'Consulta contexto pessoal legado (v1).'
    if (mode === 'user_chat') return 'Consulta contexto pessoal atual (v2).'
    return 'Consulta dados de produtividade do usuário.'
  }

  memoryTypeLabel(value: string | null | undefined): string {
    if (value === 'episodic') return 'Episódica'
    if (value === 'semantic') return 'Semântica'
    if (value === 'procedural') return 'Procedural'
    return value || 'Memória'
  }

  generativeMemoryMetaLine(item: GenerativeMemoryItem): string {
    const parts = [this.memoryTypeLabel(item.type)]

    const meta = item.metadata || {}
    const rawImportance = typeof meta === 'object'
      ? (meta as Record<string, unknown>)['importance']
      : undefined
    const importance = typeof rawImportance === 'number'
      ? rawImportance
      : typeof rawImportance === 'string'
        ? Number(rawImportance)
        : NaN
    if (Number.isFinite(importance)) {
      parts.push(`Importância ${Math.round(importance)}`)
    }

    const scoreValue = item['score']
    const score = typeof scoreValue === 'number'
      ? scoreValue
      : typeof scoreValue === 'string'
        ? Number(scoreValue)
        : NaN
    if (Number.isFinite(score)) {
      parts.push(`Score ${score.toFixed(2)}`)
    }

    const timestamp = this.coerceDateInputToMs(item.created_at ?? item.updated_at)
    if (timestamp) {
      parts.push(new Date(timestamp).toLocaleString('pt-BR', {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
      }))
    }

    return parts.join(' · ')
  }

  memoryTrackKey(item: MemoryItem, index: number): string {
    const compositeId = String(item.composite_id || '').trim()
    if (compositeId) return compositeId
    const ts = Number(item.ts_ms)
    const normalizedTs = Number.isFinite(ts) ? ts : (this.coerceDateInputToMs(item.metadata?.timestamp) || 0)
    const content = this.sanitizeDiagnosticText(item.content, 'memory').slice(0, 48)
    return `${normalizedTs}:${content}:${index}`
  }

  setRagResultViewTab(tab: RagResultViewTab): void {
    this.ragResultViewTab.set(tab)
  }

  onRagResultTabKeydown(event: KeyboardEvent): void {
    this.moveTabSelection<RagResultViewTab>(
      event,
      this.ragResultViewTab(),
      this.ragResultTabOrder,
      (tab) => this.setRagResultViewTab(tab),
      'ragResult'
    )
  }

  ragHasAnswer(): boolean {
    return Boolean(this.ragResult()?.answer?.trim())
  }

  ragHasSources(): boolean {
    return Boolean(this.ragResult()?.citations?.length)
  }

  ragHasRows(): boolean {
    return Boolean(this.ragResult()?.results?.length)
  }

  isBusinessDocError(message: string | null | undefined): boolean {
    const value = String(message || '').toLowerCase()
    return value.includes('quota') || value.includes('limite') || value.includes('maior')
  }

  onGoalCreateTitleInput(event: Event): void {
    const target = event.target as HTMLInputElement | null
    this.goalCreateTitle.set(target?.value || '')
  }

  onGoalCreateDescriptionInput(event: Event): void {
    const target = event.target as HTMLTextAreaElement | null
    this.goalCreateDescription.set(target?.value || '')
  }

  onDocFileSelected(event: Event): void {
    const target = event.target as HTMLInputElement | null
    const file = target?.files?.[0] || null
    this.selectedUploadFile.set(file)
    this.docUploadError.set('')
  }

  uploadSelectedDoc(): void {
    const file = this.selectedUploadFile()
    if (!file) {
      this.docUploadError.set('Selecione um arquivo para upload.')
      return
    }
    const userId = this.userIdString()
    this.docUploadError.set('')
    this.clearNotice('docs')
    this.docUploadInFlight.set(true)
    this.docUploadProgress.set(0)
    this.api.uploadDocument(file, this.selectedId() || undefined, userId || undefined)
      .pipe(catchError((err) => {
        this.docUploadError.set(this.extractErrorMessage(err, 'Falha no upload do documento.'))
        this.docUploadInFlight.set(false)
        this.docUploadProgress.set(null)
        return of(null)
      }))
      .subscribe((evt) => {
        if (!evt) return
        if (typeof evt.progress === 'number') {
          this.docUploadProgress.set(evt.progress)
        }
        if (evt.response) {
          const status = String(evt.response.status || '')
          if (status === 'file_too_large') {
            this.docUploadError.set('Arquivo maior que o limite permitido.')
          } else if (status === 'quota_exceeded') {
            this.docUploadError.set('Quota de documentos excedida para este usuário.')
          } else {
            this.docUploadError.set('')
            this.setNotice('docs', 'success', 'Upload concluído.')
          }
          this.docUploadInFlight.set(false)
          this.docUploadProgress.set(status ? 100 : null)
          this.selectedUploadFile.set(null)
          this.refreshConversationContext()
        }
      })
  }

  linkDocumentUrl(): void {
    const url = this.docLinkUrl().trim()
    const conversationId = this.selectedId()
    if (!url) {
      this.docLinkError.set('Informe uma URL para vincular.')
      return
    }
    if (!conversationId) {
      this.docLinkError.set('Selecione ou crie uma conversa antes de vincular URL.')
      return
    }
    this.docLinkError.set('')
    this.clearNotice('docs')
    this.docLinkLoading.set(true)
    this.api.linkUrl(conversationId, url, this.userIdString() || undefined)
      .pipe(catchError((err) => {
        this.docLinkError.set(this.extractErrorMessage(err, 'Falha ao vincular URL.'))
        this.docLinkLoading.set(false)
        return of(null)
      }))
      .subscribe((resp) => {
        if (!resp) return
        this.docLinkLoading.set(false)
        if (resp.status === 'file_too_large') {
          this.docLinkError.set('Conteúdo remoto acima do limite.')
        } else if (resp.status === 'quota_exceeded') {
          this.docLinkError.set('Quota de documentos excedida.')
        } else {
          this.docLinkUrl.set('')
          this.docLinkError.set('')
          this.setNotice('docs', 'success', 'Documento vinculado.')
        }
        this.refreshConversationContext()
      })
  }

  searchDocs(): void {
    const query = this.docSearchQuery().trim()
    if (!query) {
      this.docSearchError.set('Digite um termo para buscar documentos.')
      this.docSearchResults.set([])
      return
    }
    this.docSearchError.set('')
    this.clearNotice('docs')
    this.docSearchLoading.set(true)
    this.api.searchDocuments(query, undefined, undefined, this.userIdString())
      .pipe(catchError((err) => {
        this.docSearchError.set(this.extractErrorMessage(err, 'Falha ao buscar documentos.'))
        this.docSearchLoading.set(false)
        return of({ results: [] as DocSearchResultItem[] })
      }))
      .subscribe((resp) => {
        this.docSearchResults.set(resp.results || [])
        this.docSearchLoading.set(false)
        if ((resp.results || []).length > 0) {
          this.setNotice('docs', 'info', 'Busca concluída.')
        }
      })
  }

  deleteDoc(docId: string): void {
    if (!docId) return
    if (typeof window !== 'undefined' && !window.confirm('Excluir este documento?')) return
    this.deletingDocIds.update((curr) => ({ ...curr, [docId]: true }))
    this.api.deleteDocument(docId, this.userIdString())
      .pipe(catchError((err) => {
        this.docSearchError.set(this.extractErrorMessage(err, 'Falha ao excluir documento.'))
        this.deletingDocIds.update((curr) => {
          const next = { ...curr }
          delete next[docId]
          return next
        })
        return of(null)
      }))
      .subscribe((resp) => {
        this.deletingDocIds.update((curr) => {
          const next = { ...curr }
          delete next[docId]
          return next
        })
        if (!resp) return
        this.docs.update((items) => items.filter((d) => d.doc_id !== docId))
        this.docSearchResults.update((items) => items.filter((d) => String(d.doc_id) !== docId))
        this.setNotice('docs', 'success', 'Documento removido.')
      })
  }

  addMemory(): void {
    const content = this.memoryDraft().trim()
    if (!content) {
      this.memoryAddError.set('Digite uma memória para adicionar.')
      return
    }
    this.memoryAddError.set('')
    this.clearNotice('memory')
    this.memoryAddLoading.set(true)
    const importance = this.memoryImportance()
    const userId = this.userIdString()
    const conversationId = this.selectedId() || undefined
    this.api.addGenerativeMemory(content, {
      type: this.memoryType(),
      importance: typeof importance === 'number' ? importance : undefined,
      userId,
      conversationId,
      sessionId: conversationId
    })
      .pipe(catchError((err) => {
        this.memoryAddError.set(this.extractErrorMessage(err, 'Falha ao adicionar memória.'))
        this.memoryAddLoading.set(false)
        return of(null)
      }))
      .subscribe((resp) => {
        if (!resp) return
        this.memoryDraft.set('')
        this.memoryAddLoading.set(false)
        this.setNotice('memory', 'success', 'Memória adicionada.')
        this.refreshConversationContext()
        if (this.memorySearchQuery().trim()) {
          this.searchGenerativeMemory()
        }
      })
  }

  searchGenerativeMemory(): void {
    const query = this.memorySearchQuery().trim()
    if (!query) {
      this.memorySearchError.set('Digite um termo para buscar memória generativa.')
      this.generativeMemoryResults.set([])
      return
    }
    this.memorySearchError.set('')
    this.clearNotice('memory')
    this.memorySearchLoading.set(true)
    this.api.getGenerativeMemories(query, this.memorySearchLimit(), {
      userId: this.userIdString(),
      conversationId: this.selectedId() || undefined
    })
      .pipe(catchError((err) => {
        this.memorySearchError.set(this.extractErrorMessage(err, 'Falha ao buscar memória generativa.'))
        this.memorySearchLoading.set(false)
        return of([] as GenerativeMemoryItem[])
      }))
      .subscribe((items) => {
        const next = items || []
        this.generativeMemoryResults.set(next)
        this.memorySearchLoading.set(false)
        this.setNotice('memory', 'info', next.length ? 'Busca concluída.' : 'Consulta concluída sem resultados.')
      })
  }

  runRagQuery(): void {
    const query = this.ragQuery().trim()
    if (!query) {
      this.ragError.set('Digite uma consulta para executar no RAG.')
      this.ragResult.set(null)
      return
    }
    const mode = this.ragMode()
    const userId = this.userIdString()
    const conversationId = this.selectedId() || undefined
    this.ragError.set('')
    this.clearNotice('rag')
    this.ragResultViewTab.set('resposta')
    this.ragLoading.set(true)

    let request$: Observable<unknown>

    if (mode === 'search') {
      request$ = this.api.ragSearch({ query, limit: 5 })
    } else if (mode === 'user-chat') {
      if (!userId) {
        this.ragLoading.set(false)
        this.ragError.set('Usuário autenticado necessário para RAG user-chat.')
        this.setNotice('rag', 'warning', 'Entre com usuário autenticado para usar este modo.')
        return
      }
      request$ = this.api.ragUserChat({ query, user_id: userId, session_id: conversationId, limit: 5 })
    } else if (mode === 'user_chat') {
      request$ = this.api.ragUserChatV2({ query, user_id: userId || undefined, session_id: conversationId, limit: 5 })
    } else if (mode === 'productivity') {
      if (!userId) {
        this.ragLoading.set(false)
        this.ragError.set('Usuário autenticado necessário para RAG productivity.')
        this.setNotice('rag', 'warning', 'Entre com usuário autenticado para usar este modo.')
        return
      }
      request$ = this.api.ragProductivitySearch({ query, user_id: userId, limit: 5 })
    } else {
      request$ = this.api.ragHybridSearch({ query, user_id: userId || undefined, limit: 5 })
    }

    request$
      .pipe(catchError((err) => {
        this.ragError.set(this.extractErrorMessage(err, 'Falha ao executar consulta RAG.'))
        this.ragLoading.set(false)
        return of(null)
      }))
      .subscribe((resp: unknown) => {
        this.ragLoading.set(false)
        if (!resp) {
          this.ragResult.set(null)
          return
        }
        if (typeof resp === 'object' && resp !== null && 'results' in resp) {
          const v2 = resp as RagUserChatV2Response
          const results = (v2.results || []) as Record<string, unknown>[]
          this.ragResult.set({ mode, results })
          this.setNotice('rag', 'info', results.length ? 'Consulta RAG concluída.' : 'Consulta concluída sem resultados.')
          return
        }
        if (typeof resp === 'object' && resp !== null && 'answer' in resp) {
          const standard = resp as RagSearchResponse | RagUserChatResponse | RagHybridResponse
          const answer = standard.answer || ''
          const citations = standard.citations || []
          this.ragResult.set({ mode, answer, citations })
          const hasAnswer = Boolean(answer.trim())
          const hasCitations = citations.length > 0
          this.setNotice('rag', 'info', hasAnswer || hasCitations ? 'Consulta RAG concluída.' : 'Consulta concluída sem resultados.')
          return
        }
        this.ragResult.set({ mode, results: [] })
        this.setNotice('rag', 'info', 'Consulta concluída sem resultados.')
      })
  }

  feedbackState(message: ChatMessageView): FeedbackUiState {
    return this.feedbackStateByMessageId()[message.id] || {}
  }

  feedbackCommentDraft(messageId: string): string {
    return this.feedbackCommentDraftByMessageId()[messageId] || ''
  }

  onFeedbackCommentInput(messageId: string, event: Event): void {
    const target = event.target as HTMLTextAreaElement | null
    const value = target?.value || ''
    this.feedbackCommentDraftByMessageId.update((curr) => ({ ...curr, [messageId]: value }))
  }

  toggleFeedbackComment(messageId: string): void {
    this.feedbackStateByMessageId.update((curr) => {
      const prev = curr[messageId] || {}
      return { ...curr, [messageId]: { ...prev, commentOpen: !prev.commentOpen } }
    })
  }

  sendThumbsUp(msg: ChatMessageView): void {
    this.submitFeedback(msg, 'positive')
  }

  sendThumbsDown(msg: ChatMessageView): void {
    this.submitFeedback(msg, 'negative')
  }

  createGoal(): void {
    const title = this.goalCreateTitle().trim()
    const description = this.goalCreateDescription().trim()
    if (!title) {
      this.goalCreateError.set('Informe um título para a meta.')
      return
    }
    this.goalCreateError.set('')
    this.clearNotice('autonomy')
    this.goalCreateLoading.set(true)
    this.api.createGoal({
      title,
      description,
      priority: 2
    })
      .pipe(catchError((err) => {
        this.goalCreateError.set(this.extractErrorMessage(err, 'Falha ao criar meta.'))
        this.goalCreateLoading.set(false)
        return of(null)
      }))
      .subscribe((goal) => {
        this.goalCreateLoading.set(false)
        if (!goal) return
        this.goalCreateTitle.set('')
        this.goalCreateDescription.set('')
        this.autonomyGoals.update((items) => [goal, ...items])
        this.setNotice('autonomy', 'success', 'Meta criada.')
      })
  }

  refreshAutonomy(): void {
    this.loadAutonomyContext()
  }

  toggleAutonomyLoop(): void {
    if (this.autonomySaving()) return
    this.autonomySaving.set(true)
    this.autonomyError.set('')
    this.clearNotice('autonomy')
    const active = Boolean(this.autonomyStatus()?.active)
    const request$ = active
      ? this.api.stopAutonomy()
      : this.api.startAutonomy({
        interval_seconds: 60,
        risk_profile: 'balanced',
        user_id: this.user()?.id ? String(this.user()?.id) : undefined
      })
    request$
      .pipe(catchError((err) => {
        this.autonomyError.set(this.extractErrorMessage(err, 'Falha ao atualizar autonomia.'))
        return of(null)
      }))
      .subscribe(() => {
        this.autonomySaving.set(false)
        this.setNotice('autonomy', 'success', active ? 'Loop autônomo interrompido.' : 'Loop autônomo iniciado.')
        this.loadAutonomyContext()
      })
  }

  markGoalStatus(goal: Goal, status: GoalStatus): void {
    if (!goal?.id || this.autonomySaving()) return
    this.autonomySaving.set(true)
    this.autonomyError.set('')
    this.clearNotice('autonomy')
    this.api.updateGoalStatus(goal.id, status)
      .pipe(catchError((err) => {
        this.autonomyError.set(this.extractErrorMessage(err, 'Falha ao atualizar meta.'))
        return of(null)
      }))
      .subscribe((updated) => {
        if (updated) {
          this.autonomyGoals.update((items) => items.map((item) => item.id === updated.id ? updated : item))
          this.setNotice('autonomy', 'success', 'Status da meta atualizado.')
        }
        this.autonomySaving.set(false)
      })
  }

  goalStatusLabel(goal: Goal): string {
    if (goal.status === 'in_progress') return 'Em andamento'
    if (goal.status === 'completed') return 'Concluida'
    if (goal.status === 'failed') return 'Falhou'
    return 'Pendente'
  }

  readonly traceSteps = signal<any[]>([])
  readonly showTrace = signal(false)
  readonly thoughtStream = signal<ThoughtStreamItem[]>([])
  private readonly advancedModeStorageKey = 'janus.conversations.show_advanced_mode'
  private readonly advancedRailTabStorageKey = 'janus.conversations.advanced_rail_tab'
  private readonly customerTabStorageKey = 'janus.conversations.customer_tab'

  // ... (inside class)

  toggleTrace() {
    this.showTrace.update(v => !v)
    if (this.showTrace() && this.selectedId()) {
      this.loadTrace(this.selectedId()!)
    }
  }

  private loadTrace(conversationId: string): void {
    this.api.getConversationTrace(conversationId).pipe(
      catchError(() => of([]))
    ).subscribe(steps => {
      this.traceSteps.set(steps)
    })
  }

  // Hook into selectConversation to clear/reload trace
  private selectConversation(id: string | null): void {
    if (id === this.selectedId()) return

    // During "create conversation + send first message", router param updates can arrive mid-stream.
    // Avoid tearing down the active stream/UI state for that transient navigation synchronization.
    if (!id && this.sending() && this.streamingMessageId && this.streamingConversationId) {
      return
    }

    this.selectedId.set(id)

    const preserveActiveStreamForTarget = Boolean(
      id &&
      this.sending() &&
      this.streamingMessageId &&
      this.streamingConversationId === id
    )

    if (preserveActiveStreamForTarget && id) {
      this.eventsService.connect(id)
      this.loadContext(id)
      if (this.showTrace()) {
        this.loadTrace(id)
      }
      return
    }

    this.messages.set([])
    this.events.set([])
    this.docs.set([])
    this.memoryUser.set([])
    this.docSearchResults.set([])
    this.generativeMemoryResults.set([])
    this.ragResult.set(null)
    this.ragError.set('')
    this.ragResultViewTab.set('resposta')
    this.docSearchError.set('')
    this.memorySearchError.set('')
    this.clearNotice('docs')
    this.clearNotice('memory')
    this.clearNotice('rag')
    this.clearNotice('autonomy')
    this.traceSteps.set([]) // Clear trace
    this.thoughtStream.set([])
    this.copiedCitation.set('')
    this.feedbackStateByMessageId.set({})
    this.feedbackCommentDraftByMessageId.set({})
    this.stream.stop()
    this.sending.set(false)
    this.responseStartedAt = null
    this.streamingBuffer = ''
    this.streamingMessageId = null
    this.streamingConversationId = null

    if (!id) {
      this.eventsService.disconnect()
      this.historyLoading.set(false)
      this.contextLoading.set(false)
      return
    }

    this.eventsService.connect(id)
    this.loadHistory(id)
    this.loadContext(id)
    if (this.showTrace()) {
      this.loadTrace(id)
    }
  }

  private loadConversations(): void {
    this.listLoading.set(true)
    const userId = this.user()?.id ? String(this.user()?.id) : undefined
    this.api.listConversations(userId ? { user_id: userId, limit: 60 } : { limit: 60 })
      .pipe(
        map((resp) => resp.conversations || []),
        catchError(() => of([]))
      )
      .subscribe((items) => {
        this.conversations.set(items)
        this.listLoading.set(false)
      })
  }

  private loadHistory(conversationId: string): void {
    this.historyLoading.set(true)
    this.api.getChatHistoryPaginated(conversationId, { limit: 80, offset: 0 })
      .pipe(
        map((resp) => resp.messages || []),
        catchError(() => of([]))
      )
      .subscribe((items) => {
        const mapped = items.map((msg) => this.mapMessage(msg))
        this.messages.set(this.reconcileResolvedPendingActions(mapped))
        this.historyLoading.set(false)
        this.queueScroll()
      })
  }

  private loadContext(conversationId: string): void {
    this.contextLoading.set(true)
    const userId = this.user()?.id ? String(this.user()?.id) : undefined
    forkJoin({
      docs: this.api.listDocuments(conversationId, userId).pipe(
        map((resp) => resp.items || []),
        catchError(() => of([]))
      ),
      memory: this.api.getMemoryTimeline({
        limit: 24,
        user_id: userId,
        conversation_id: conversationId
      }).pipe(
        map((items) => items.filter((item) => this.isConversationMemory(item, conversationId))),
        catchError(() => of([] as MemoryItem[]))
      )
    }).subscribe((result) => {
      this.docs.set(result.docs)
      this.memoryUser.set(result.memory)
      this.contextLoading.set(false)
    })
    this.loadAutonomyContext()
  }

  private refreshConversationContext(): void {
    const id = this.selectedId()
    if (!id) return
    this.loadContext(id)
  }

  private userIdString(): string | undefined {
    const id = this.user()?.id
    return id != null ? String(id) : undefined
  }

  private setNotice(section: RailNoticeSection, kind: RailNoticeKind, message: string, autoHideMs = 2800): void {
    const setter = this.noticeSignal(section)
    const existingTimer = this.noticeTimers.get(section)
    if (existingTimer) {
      clearTimeout(existingTimer)
      this.noticeTimers.delete(section)
    }
    setter.set({ kind, message, visible: true })
    if (kind === 'error') return
    const timer = setTimeout(() => {
      setter.set(null)
      this.noticeTimers.delete(section)
    }, autoHideMs)
    this.noticeTimers.set(section, timer)
  }

  private clearNotice(section: RailNoticeSection): void {
    const existingTimer = this.noticeTimers.get(section)
    if (existingTimer) {
      clearTimeout(existingTimer)
      this.noticeTimers.delete(section)
    }
    this.noticeSignal(section).set(null)
  }

  private noticeSignal(section: RailNoticeSection) {
    if (section === 'docs') return this.docsNotice
    if (section === 'memory') return this.memoryNotice
    if (section === 'rag') return this.ragNotice
    return this.autonomyNotice
  }

  private moveTabSelection<T extends string>(
    event: KeyboardEvent,
    current: T,
    order: readonly T[],
    setter: (tab: T) => void,
    group: TabGroup
  ): void {
    const key = event.key
    const currentIndex = order.indexOf(current)
    if (currentIndex < 0) return

    let nextIndex = currentIndex
    if (key === 'ArrowRight') nextIndex = (currentIndex + 1) % order.length
    else if (key === 'ArrowLeft') nextIndex = (currentIndex - 1 + order.length) % order.length
    else if (key === 'Home') nextIndex = 0
    else if (key === 'End') nextIndex = order.length - 1
    else if (key === 'Enter' || key === ' ') nextIndex = currentIndex
    else return

    event.preventDefault()
    const nextTab = order[nextIndex]
    setter(nextTab)

    if (typeof document === 'undefined') return
    const targetId = this.tabDomId(group, nextTab)
    document.getElementById(targetId)?.focus()
  }

  private tabDomId(group: TabGroup, tab: string): string {
    if (group === 'advancedRail') return `advanced-tab-${tab}`
    if (group === 'customer') return `customer-tab-${tab}`
    return `rag-view-tab-${tab}`
  }

  private submitFeedback(msg: ChatMessageView, rating: 'positive' | 'negative'): void {
    if (msg.role !== 'assistant') return
    const conversationId = this.selectedId()
    if (!conversationId) return
    const state = this.feedbackState(msg)
    if (state.submitting || state.submitted) return
    const messageId = String(msg.backendMessageId || msg.id)
    const userId = this.userIdString()
    const comment = this.feedbackCommentDraft(msg.id).trim() || undefined

    this.feedbackStateByMessageId.update((curr) => ({
      ...curr,
      [msg.id]: { ...(curr[msg.id] || {}), rating, submitting: true, error: '', serverMessage: '' }
    }))

    const request$ = rating === 'positive'
      ? this.api.thumbsUpFeedback({ conversation_id: conversationId, message_id: messageId, comment, user_id: userId })
      : this.api.thumbsDownFeedback({ conversation_id: conversationId, message_id: messageId, comment, user_id: userId })

    request$
      .pipe(catchError((err) => {
        const errorMsg = this.extractErrorMessage(err, 'Falha ao enviar feedback.')
        this.feedbackStateByMessageId.update((curr) => ({
          ...curr,
          [msg.id]: { ...(curr[msg.id] || {}), rating, submitting: false, submitted: false, error: errorMsg }
        }))
        return of(null as FeedbackQuickResponse | null)
      }))
      .subscribe((resp) => {
        if (!resp) return
        this.feedbackStateByMessageId.update((curr) => ({
          ...curr,
          [msg.id]: {
            ...(curr[msg.id] || {}),
            rating,
            submitting: false,
            submitted: true,
            error: '',
            serverMessage: resp.message || 'Feedback enviado.',
            commentOpen: false
          }
        }))
      })
  }

  private async ensureConversationId(
    forceCreate = false,
    navigateImmediately = true
  ): Promise<string | null> {
    const current = this.selectedId()
    if (current && !forceCreate) return current
    const userId = this.user()?.id ? String(this.user()?.id) : undefined
    try {
      const response = await firstValueFrom(
        this.api.startChat(undefined, undefined, userId).pipe(catchError(() => of(null)))
      )
      const conversationId = response?.conversation_id
      if (!conversationId) return null
      const now = Date.now()
      const meta: ConversationMeta = {
        conversation_id: conversationId,
        title: undefined,
        created_at: now,
        updated_at: now
      }
      this.conversations.update((items) => [meta, ...items])
      this.selectConversation(conversationId)
      if (navigateImmediately) {
        this.pendingConversationRouteId = null
        this.router.navigate(['/conversations', conversationId], { replaceUrl: true })
      } else {
        this.pendingConversationRouteId = conversationId
      }
      return conversationId
    } catch {
      return null
    }
  }

  private startStreaming(conversationId: string, message: string): void {
    this.streamingBuffer = ''
    this.streamingMessageId = this.createId()
    this.streamingConversationId = conversationId
    this.appendMessage({
      id: this.streamingMessageId,
      role: 'assistant',
      text: '',
      timestamp: Date.now(),
      streaming: true
    })
    this.queueScroll()
    this.stream.start({
      conversationId,
      text: message,
      role: this.selectedRole(),
      priority: this.selectedPriority()
    })
  }

  private sendClassic(conversationId: string, message: string): void {
    const userId = this.user()?.id ? String(this.user()?.id) : undefined
    this.api.sendChatMessage(conversationId, message, this.selectedRole(), this.selectedPriority(), undefined, userId)
      .pipe(catchError(() => of(null)))
      .subscribe((resp) => {
        const latencyMs = this.consumeResponseLatency()
        if (!resp) {
          this.appendMessage({
            id: this.createId(),
            role: 'assistant',
            text: 'Falha ao enviar mensagem.',
            timestamp: Date.now(),
            error: true
          })
        } else {
          const now = Date.now()
          const cleanText = this.sanitizeChatText(resp.response)
          const raw = resp as unknown as Record<string, unknown>
          const backendMessageId = typeof raw['message_id'] === 'string'
            ? String(raw['message_id'])
            : (typeof raw['id'] === 'string' ? String(raw['id']) : undefined)
          const localMessageId = this.createId()
          this.appendMessage({
            id: localMessageId,
            backendMessageId,
            role: 'assistant',
            text: cleanText,
            timestamp: now,
            citations: resp.citations || [],
            citation_status: resp.citation_status,
            understanding: resp.understanding,
            confirmation: resp.confirmation ?? resp.understanding?.confirmation,
            agent_state: resp.agent_state,
            latency_ms: latencyMs,
            provider: resp.provider,
            model: resp.model,
            delivery_status: resp.delivery_status,
            failure_classification: resp.failure_classification
          })
          this.updateConversationPreview(conversationId, 'assistant', cleanText, now)
          if (resp.delivery_status === 'pending_study' && resp.study_job) {
            this.startStudyPolling(resp.study_job, localMessageId)
            this.showStudyNotice(resp.study_notice || resp.study_job.placeholder_message || 'Estudando a base para responder com seguranca; isso pode demorar.')
          }
        }
        this.sending.set(false)
        this.flushPendingConversationNavigation(conversationId)
        this.queueScroll()
      })
  }

  private sendAdminCodeQa(conversationId: string, message: string): void {
    this.api.askAutonomyAdminCodeQa({
      question: message,
      limit: 12,
      citation_limit: 8
    })
      .pipe(catchError(() => of(null)))
      .subscribe((resp) => {
        const latencyMs = this.consumeResponseLatency()
        if (!resp) {
          this.appendMessage({
            id: this.createId(),
            role: 'assistant',
            text: 'Falha ao consultar codigo no modo admin.',
            timestamp: Date.now(),
            error: true
          })
        } else {
          const now = Date.now()
          const cleanText = this.sanitizeChatText(resp.answer)
          this.appendMessage({
            id: this.createId(),
            role: 'assistant',
            text: cleanText,
            timestamp: now,
            citations: resp.citations || [],
            latency_ms: latencyMs,
            provider: 'admin',
            model: 'code-qa'
          })
          this.updateConversationPreview(conversationId, 'assistant', cleanText, now)
        }
        this.sending.set(false)
        this.flushPendingConversationNavigation(conversationId)
        this.queueScroll()
      })
  }

  private handleStreamPartial(chunk: string): void {
    if (!this.streamingMessageId) return
    if (!this.streamingBuffer) {
      this.appendThought('stream', 'Resposta', 'Janus iniciou a geracao da resposta.')
    }
    this.streamingBuffer = this.sanitizeStreamingText(`${this.streamingBuffer}${chunk}`)
    this.updateMessage(this.streamingMessageId, {
      text: this.streamingBuffer,
      streaming: true
    })
    this.queueScroll()
  }

  private handleStreamDone(done: StreamDone): void {
    const latencyMs = this.consumeResponseLatency()
    const finalText = this.streamingBuffer
    if (this.streamingMessageId) {
      this.updateMessage(this.streamingMessageId, {
        backendMessageId: done.message_id,
        text: finalText,
        streaming: false,
        estimated_wait_seconds: done.estimated_wait_seconds,
        estimated_wait_range_seconds: done.estimated_wait_range_seconds,
        processing_profile: done.processing_profile,
        processing_notice: done.processing_notice || undefined,
        citations: done.citations || [],
        citation_status: done.citation_status,
        understanding: done.understanding,
        confirmation: done.confirmation ?? done.understanding?.confirmation,
        agent_state: done.agent_state,
        latency_ms: latencyMs,
        provider: done.provider,
        model: done.model
      })
      this.updateConversationPreview(done.conversation_id || this.selectedId() || '', 'assistant', finalText, Date.now())
    }
    this.streamingBuffer = ''
    this.streamingMessageId = null
    this.streamingConversationId = null
    this.sending.set(false)
    const modelParts = [done.provider, done.model].filter(Boolean)
    const modelLabel = modelParts.length ? ` (${modelParts.join(' / ')})` : ''
    const citationsCount = done.citations?.length || 0
    if (done.processing_notice) {
      this.appendThought('agent', 'Estimativa', done.processing_notice)
    }
    this.appendThought('stream', 'Resposta concluida', `Streaming finalizado${modelLabel}. Citacoes: ${citationsCount}.`)
    this.queueScroll()
    this.loadConversations()
    this.flushPendingConversationNavigation(done.conversation_id || this.selectedId())
  }

  private handleStreamError(reason: string): void {
    this.consumeResponseLatency()
    const id = this.streamingMessageId || this.createId()
    if (!this.streamingMessageId) {
      this.appendMessage({
        id,
        role: 'assistant',
        text: `Erro no streaming: ${reason}`,
        timestamp: Date.now(),
        error: true
      })
    } else {
      this.updateMessage(id, {
        text: `${this.streamingBuffer}\n\n[Erro no streaming: ${reason}]`,
        streaming: false,
        error: true
      })
    }
    this.streamingBuffer = ''
    this.streamingMessageId = null
    this.streamingConversationId = null
    this.sending.set(false)
    this.appendThought('system', 'Falha no streaming', reason || 'erro desconhecido')
    this.flushPendingConversationNavigation(this.selectedId())
  }

  private flushPendingConversationNavigation(targetId?: string | null): void {
    const pendingId = this.pendingConversationRouteId
    if (!pendingId) return
    const nextId = targetId || pendingId
    if (!nextId || pendingId !== nextId) return
    this.pendingConversationRouteId = null
    this.router.navigate(['/conversations', nextId], { replaceUrl: true })
  }

  private appendMessage(message: ChatMessageView): void {
    this.messages.update((items) => [...items, message])
  }

  private updateMessage(id: string, patch: Partial<ChatMessageView>): void {
    this.messages.update((items) => {
      const idx = items.findIndex((msg) => msg.id === id)
      if (idx < 0) return items
      const next = items.slice()
      next[idx] = { ...next[idx], ...patch }
      return next
    })
  }

  private updateConversationPreview(conversationId: string, role: string, text: string, timestamp: number): void {
    if (!conversationId) return
    this.conversations.update((items) => items.map((conv) => {
      if (conv.conversation_id !== conversationId) return conv
      return {
        ...conv,
        updated_at: timestamp,
        last_message: {
          role,
          text,
          timestamp
        }
      }
    }))
  }

  private conversationUpdatedAt(conv: ConversationMeta): number {
    const updated = Number(conv.updated_at)
    if (Number.isFinite(updated) && updated > 0) return updated
    const lastTimestamp = Number(conv.last_message?.timestamp)
    if (Number.isFinite(lastTimestamp) && lastTimestamp > 0) return lastTimestamp
    const created = Number(conv.created_at)
    if (Number.isFinite(created) && created > 0) return created
    return 0
  }

  private mapMessage(msg: ChatMessage): ChatMessageView {
    const raw = msg as unknown as Record<string, unknown>
    const latencyMsRaw = Number(raw['latency_ms'])
    const backendMessageId = typeof raw['message_id'] === 'string'
      ? String(raw['message_id'])
      : (typeof raw['id'] === 'string' ? String(raw['id']) : undefined)
    return {
      id: this.createId(),
      backendMessageId,
      role: (msg.role as ChatRole) || 'assistant',
      text: this.sanitizeChatText(msg.text),
      timestamp: msg.timestamp,
      citations: msg.citations || [],
      citation_status: (raw['citation_status'] as CitationStatus | undefined),
      understanding: msg.understanding,
      confirmation: (raw['confirmation'] as ChatConfirmationState | undefined) ?? msg.understanding?.confirmation,
      agent_state: (raw['agent_state'] as ChatAgentState | undefined),
      latency_ms: Number.isFinite(latencyMsRaw) && latencyMsRaw > 0 ? latencyMsRaw : undefined,
      provider: typeof raw['provider'] === 'string' ? String(raw['provider']) : undefined,
      model: typeof raw['model'] === 'string' ? String(raw['model']) : undefined,
      delivery_status: typeof raw['delivery_status'] === 'string' ? String(raw['delivery_status']) : undefined,
      failure_classification: typeof raw['failure_classification'] === 'string' ? String(raw['failure_classification']) : undefined
    }
  }

  private reconcileResolvedPendingActions(messages: ChatMessageView[]): ChatMessageView[] {
    const resolved = new Map<number, PendingActionResolution>()

    for (const msg of messages) {
      if (msg.role !== 'system') continue
      const match = ConversationsComponent.PENDING_ACTION_RESOLUTION_RE.exec(msg.text || '')
      if (!match) continue
      const actionId = Number(match[1])
      const status = match[2]?.toLowerCase() === 'aprovada' ? 'approved' : 'rejected'
      if (Number.isFinite(actionId)) {
        resolved.set(actionId, status)
      }
    }

    if (!resolved.size) return messages

    return messages.map((msg) => {
      if (msg.role !== 'assistant') return msg
      const confirmation = msg.confirmation || msg.understanding?.confirmation
      const actionId = confirmation?.pending_action_id
      if (typeof actionId !== 'number') return msg

      const resolution = resolved.get(actionId)
      if (!resolution) return msg

      const nextConfirmation: ChatConfirmationState = {
        ...(confirmation || { required: true }),
        required: false,
        status: resolution,
      }
      delete nextConfirmation.approve_endpoint
      delete nextConfirmation.reject_endpoint

      const nextUnderstanding = msg.understanding
        ? {
            ...msg.understanding,
            requires_confirmation: false,
            confirmation: {
              ...(msg.understanding.confirmation || nextConfirmation),
              required: false,
              status: resolution,
            },
          }
        : msg.understanding

      if (nextUnderstanding?.confirmation) {
        delete nextUnderstanding.confirmation.approve_endpoint
        delete nextUnderstanding.confirmation.reject_endpoint
      }

      return {
        ...msg,
        confirmation: nextConfirmation,
        understanding: nextUnderstanding,
        agent_state: {
          ...(msg.agent_state || { state: 'completed' }),
          state: 'completed',
          requires_confirmation: false,
          reason: resolution,
        },
      }
    })
  }

  private cognitiveStatusText(state: string, reason?: string): string {
    if (state === 'knowledge_wait_estimate') {
      return reason || 'Consulta grounded iniciada; isso pode demorar.'
    }
    if (state === 'studying_codebase') {
      return reason || 'Estudando a base para responder com seguranca; isso pode demorar.'
    }
    if (state === 'study_progress') {
      return reason || 'Estudo em andamento na base local.'
    }
    if (state === 'resuming_answer_generation') {
      return reason || 'Gerando a resposta final a partir do estudo.'
    }
    return `Estado: ${state}${reason ? ` (${reason})` : ''}`
  }

  private showStudyNotice(message: string): void {
    this.autonomyNotice.set({ kind: 'info', message, visible: true })
  }

  private startStudyPolling(job: ChatStudyJobRef, localMessageId: string): void {
    const jobId = String(job.job_id || '')
    if (!jobId) return
    const existing = this.studyPollTimers.get(jobId)
    if (existing) clearTimeout(existing)

    this.api.getChatStudyJob(jobId)
      .pipe(catchError(() => of(null)))
      .subscribe((resp) => {
        if (!resp) {
          this.scheduleStudyPoll(jobId, localMessageId, 2500)
          return
        }
        this.applyStudyJobUpdate(localMessageId, resp)
      })
  }

  private scheduleStudyPoll(jobId: string, localMessageId: string, delayMs: number): void {
    const timer = setTimeout(() => this.startStudyPolling({
      job_id: jobId,
      status: 'running',
      poll_url: '',
      conversation_id: this.selectedId() || ''
    }, localMessageId), delayMs)
    this.studyPollTimers.set(jobId, timer)
  }

  private applyStudyJobUpdate(localMessageId: string, job: ChatStudyJobResponse): void {
    const jobId = String(job.job_id || '')
    if (!jobId) return
    if (job.status === 'completed' && job.final_response) {
      const finalResponse = job.final_response
      const finalText = this.sanitizeChatText(finalResponse.response)
      this.updateMessage(localMessageId, {
        backendMessageId: finalResponse.message_id,
        text: finalText,
        citations: finalResponse.citations || [],
        citation_status: finalResponse.citation_status,
        understanding: finalResponse.understanding,
        confirmation: finalResponse.confirmation ?? finalResponse.understanding?.confirmation,
        agent_state: finalResponse.agent_state,
        provider: finalResponse.provider,
        model: finalResponse.model,
        delivery_status: finalResponse.delivery_status,
        failure_classification: finalResponse.failure_classification
      })
      this.updateConversationPreview(job.conversation_id, 'assistant', finalText, Date.now())
      this.studyPollTimers.delete(jobId)
      this.autonomyNotice.set(null)
      this.queueScroll()
      return
    }
    if (job.status === 'failed') {
      this.updateMessage(localMessageId, {
        text: job.error || 'Falha ao concluir o estudo automatico dessa resposta.',
        error: true,
        delivery_status: 'failed',
        failure_classification: job.failure_classification
      })
      this.studyPollTimers.delete(jobId)
      return
    }
    if (job.placeholder_message) {
      this.updateMessage(localMessageId, {
        text: this.sanitizeChatText(job.placeholder_message),
        delivery_status: 'pending_study',
        failure_classification: job.failure_classification
      })
    }
    this.scheduleStudyPoll(jobId, localMessageId, 2500)
  }

  private createId(): string {
    if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
      return crypto.randomUUID()
    }
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`
  }

  private queueScroll(): void {
    if (this.scrollQueued) return
    this.scrollQueued = true
    requestAnimationFrame(() => {
      this.scrollQueued = false
      this.scrollToBottom()
    })
  }

  private scrollToBottom(): void {
    const el = this.messageList?.nativeElement
    if (!el) return
    el.scrollTop = el.scrollHeight
  }

  thoughtIcon(item: ThoughtStreamItem): string {
    if (item.kind === 'agent') return 'smart_toy'
    if (item.kind === 'stream') return 'bolt'
    return 'info'
  }

  private handleStreamStatus(status: string): void {
    const previous = this.streamStatus()
    this.streamStatus.set(status)
    if (status === previous) return
    if (status === 'connecting') this.appendThought('stream', 'Conexao', 'Conectando ao stream de resposta...')
    if (status === 'retrying') this.appendThought('system', 'Reconexao', 'Tentando restabelecer o stream...')
    if (status === 'open') this.appendThought('stream', 'Conectado', 'Canal SSE ativo e pronto.')
    if (status === 'error') this.appendThought('system', 'Erro de stream', 'Falha de conexao com o stream.')
  }

  private appendThought(kind: ThoughtKind, title: string, text: string, timestamp?: number): void {
    const safeTitleRaw = this.sanitizeDiagnosticText(title, 'Evento').slice(0, 120)
    const safeTitle = safeTitleRaw.toLowerCase() === 'unknown' ? 'Agente' : safeTitleRaw
    const safeText = this.sanitizeDiagnosticText(text, 'Evento tecnico recebido')
    const item: ThoughtStreamItem = {
      id: this.createId(),
      kind,
      title: safeTitle || 'Evento',
      text: safeText,
      timestamp: this.coerceDateInputToMs(timestamp) || Date.now()
    }
    this.thoughtStream.update((items) => [item, ...items].slice(0, 40))
  }

  messageAgentState(msg: ChatMessageView): string {
    const explicit = String(msg.agent_state?.state || '').trim()
    if (explicit) return explicit
    if (msg.streaming) return 'streaming_response'
    const confirmation = this.messageConfirmation(msg)
    if (confirmation?.required && typeof confirmation.pending_action_id === 'number') return 'waiting_confirmation'
    if (msg.understanding?.low_confidence) return 'low_confidence'
    return ''
  }

  messageConfirmation(msg: ChatMessageView): ChatConfirmationState | null {
    const conf = msg.confirmation || msg.understanding?.confirmation
    if (!conf) return null
    const hasPendingAction = typeof conf.pending_action_id === 'number'
    const hasEndpoints = typeof conf.approve_endpoint === 'string' && typeof conf.reject_endpoint === 'string'
    if (!hasPendingAction && !hasEndpoints) return null
    if (conf.required === false && !hasPendingAction && !hasEndpoints) return null
    return conf
  }

  messageRiskSummary(msg: ChatMessageView): string {
    const risk = msg.understanding?.risk
    if (risk?.summary) return String(risk.summary)
    const reason = this.messageConfirmation(msg)?.reason
    if (reason === 'high_risk') return 'Ação classificada como alto risco; confirmação obrigatória.'
    if (reason === 'low_confidence') return 'Baixa confiança para executar ação; confirme antes de prosseguir.'
    return 'Ação requer confirmação antes de prosseguir.'
  }

  citationStatusLabel(status?: CitationStatus): string {
    const s = String(status?.status || '')
    if (s === 'present') return `Fontes: ${status?.count ?? 0}`
    if (s === 'missing_required') return 'Sem citação rastreável (obrigatória)'
    if (s === 'retrieval_failed') return 'Falha ao recuperar citações'
    return 'Sem citação'
  }

  citationStatusVariant(status?: CitationStatus): 'success' | 'warning' | 'error' | 'neutral' {
    const s = String(status?.status || '')
    if (s === 'present') return 'success'
    if (s === 'missing_required') return 'warning'
    if (s === 'retrieval_failed') return 'error'
    return 'neutral'
  }

  isPendingActionBusy(actionId?: number): boolean {
    if (typeof actionId !== 'number') return false
    return Boolean(this.pendingActionLoading()[actionId])
  }

  approvePendingActionForMessage(msg: ChatMessageView): void {
    const conf = this.messageConfirmation(msg)
    const actionId = conf?.pending_action_id
    if (typeof actionId !== 'number') return
    this.setPendingActionBusy(actionId, true)
    const action: PendingAction = { status: 'pending', source: 'sql', action_id: actionId }
    this.api.approvePendingAction(action)
      .pipe(catchError(() => of(null)))
      .subscribe((resp) => {
        this.setPendingActionBusy(actionId, false)
        if (!resp) {
          this.updateMessage(msg.id, { error: true, text: `${msg.text}\n\n[Falha ao aprovar ação pendente]` })
          return
        }
        this.updateMessage(msg.id, {
          confirmation: { ...(conf || { required: true }), required: false, pending_action_id: actionId, reason: conf?.reason, status: 'approved' },
          agent_state: { state: 'completed', reason: 'approved' }
        })
        this.appendMessage({
          id: this.createId(),
          role: 'system',
          text: `Ação pendente #${actionId} aprovada. ${resp.message || ''}`.trim(),
          timestamp: Date.now()
        })
      })
  }

  rejectPendingActionForMessage(msg: ChatMessageView): void {
    const conf = this.messageConfirmation(msg)
    const actionId = conf?.pending_action_id
    if (typeof actionId !== 'number') return
    this.setPendingActionBusy(actionId, true)
    const action: PendingAction = { status: 'pending', source: 'sql', action_id: actionId }
    this.api.rejectPendingAction(action)
      .pipe(catchError(() => of(null)))
      .subscribe((resp) => {
        this.setPendingActionBusy(actionId, false)
        if (!resp) {
          this.updateMessage(msg.id, { error: true, text: `${msg.text}\n\n[Falha ao rejeitar ação pendente]` })
          return
        }
        this.updateMessage(msg.id, {
          confirmation: { ...(conf || { required: true }), required: false, pending_action_id: actionId, reason: conf?.reason, status: 'rejected' },
          agent_state: { state: 'completed', reason: 'rejected' }
        })
        this.appendMessage({
          id: this.createId(),
          role: 'system',
          text: `Ação pendente #${actionId} rejeitada. ${resp.message || ''}`.trim(),
          timestamp: Date.now()
        })
      })
  }

  private setPendingActionBusy(actionId: number, busy: boolean): void {
    this.pendingActionLoading.update((curr) => {
      const next = { ...curr }
      if (busy) next[actionId] = true
      else delete next[actionId]
      return next
    })
  }

  private restoreAdvancedModePreference(): void {
    try {
      const saved = localStorage.getItem(this.advancedModeStorageKey)
      if (saved === '1') this.showAdvanced.set(true)
      if (saved === '0') this.showAdvanced.set(false)
    } catch {
      this.showAdvanced.set(false)
    }
  }

  private restoreRailTabPreferences(): void {
    try {
      const advanced = localStorage.getItem(this.advancedRailTabStorageKey)
      if (advanced === 'insights' || advanced === 'cliente' || advanced === 'autonomia') {
        this.advancedRailTab.set(advanced)
      }
      const customer = localStorage.getItem(this.customerTabStorageKey)
      if (customer === 'docs' || customer === 'memoria' || customer === 'rag') {
        this.customerTab.set(customer)
      }
    } catch {
      this.advancedRailTab.set('cliente')
      this.customerTab.set('docs')
    }
  }

  private persistAdvancedModePreference(enabled: boolean): void {
    try {
      localStorage.setItem(this.advancedModeStorageKey, enabled ? '1' : '0')
    } catch {
      // no-op
    }
  }

  private persistRailTabPreference(key: string, value: string): void {
    try {
      localStorage.setItem(key, value)
    } catch {
      // no-op
    }
  }

  private consumeResponseLatency(): number | undefined {
    if (!this.responseStartedAt) return undefined
    const latencyMs = Math.max(0, Date.now() - this.responseStartedAt)
    this.responseStartedAt = null
    return latencyMs
  }

  private loadAutonomyContext(): void {
    this.autonomyLoading.set(true)
    forkJoin({
      status: this.api.getAutonomyStatus().pipe(catchError(() => of(null))),
      goals: this.api.listGoals().pipe(catchError(() => of([] as Goal[]))),
      tools: this.api.getTools().pipe(
        map((resp) => resp.tools || []),
        catchError(() => of([] as Tool[]))
      )
    }).subscribe((result) => {
      this.autonomyStatus.set(result.status)
      this.autonomyGoals.set(result.goals)
      this.autonomyTools.set(result.tools)
      this.autonomyLoading.set(false)
    })
  }

  private isConversationMemory(item: MemoryItem, conversationId: string): boolean {
    const metadata = item.metadata || {}
    const target = String(conversationId || '').trim()
    if (!target) return false
    const sessionId = String(metadata.session_id || '').trim()
    const threadId = String(metadata['thread_id'] || '').trim()
    const convoId = String(metadata['conversation_id'] || '').trim()
    const taskId = String(metadata['task_id'] || '').trim()
    const compositeId = String(item.composite_id || '')
    if ([sessionId, threadId, convoId, taskId].some((value) => value === target)) return true
    if (!compositeId) return false
    const compositeTokens = compositeId.split(/[:/|]/g).map((part) => part.trim()).filter(Boolean)
    return compositeTokens.some((part) => part === target)
  }

  private coerceDateInputToMs(value: unknown): number | null {
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value > 10_000_000_000 ? value : value * 1000
    }
    if (typeof value === 'string' && value.trim()) {
      const numeric = Number(value)
      if (Number.isFinite(numeric)) {
        return numeric > 10_000_000_000 ? numeric : numeric * 1000
      }
      const parsed = Date.parse(value)
      if (Number.isFinite(parsed)) return parsed
    }
    return null
  }

  private extractErrorMessage(error: unknown, fallback: string): string {
    if (!error || typeof error !== 'object') return fallback
    const maybe = error as { error?: { detail?: string } }
    const detail = maybe.error?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    return fallback
  }

  private sanitizeChatText(value: unknown): string {
    if (value === null || value === undefined) return ''
    if (typeof value === 'string') {
      const cleaned = value
        .replace(/\[\s*object\s+object\s*\]/gi, '')
        .split('')
        .map((ch) => {
          const code = ch.charCodeAt(0)
          const isControl = (code >= 0x00 && code <= 0x08)
            || code === 0x0b
            || code === 0x0c
            || (code >= 0x0e && code <= 0x1f)
            || (code >= 0x7f && code <= 0x9f)
            || code === 0xfffd
          return isControl ? ' ' : ch
        })
        .join('')
        .replace(/\n{3,}/g, '\n\n')
      return cleaned.trim() ? cleaned : ''
    }
    if (typeof value === 'number' || typeof value === 'boolean') return String(value)
    try {
      return JSON.stringify(value, null, 2)
    } catch {
      return String(value)
    }
  }

  private sanitizeStreamingText(value: string): string {
    return String(value || '')
      .replace(/\[\s*object\s+object\s*\]/gi, '')
      .split('')
      .map((ch) => {
        const code = ch.charCodeAt(0)
        const isControl = (code >= 0x00 && code <= 0x08)
          || code === 0x0b
          || code === 0x0c
          || (code >= 0x0e && code <= 0x1f)
          || (code >= 0x7f && code <= 0x9f)
          || code === 0xfffd
        return isControl ? ' ' : ch
      })
      .join('')
      .replace(/\n{3,}/g, '\n\n')
  }

  private sanitizeDiagnosticText(value: unknown, fallback = ''): string {
    const raw = this.sanitizeChatText(value)
    if (!raw) return fallback
    const compact = raw.replace(/\s{2,}/g, ' ').trim()
    if (!compact) return fallback
    if (this.looksLikeBinaryPayload(compact) || this.looksLikeStructuredTelemetryNoise(compact)) {
      return fallback || 'Conteudo nao textual omitido'
    }
    return compact
  }

  private looksLikeBinaryPayload(value: string): boolean {
    if (value.length < 20) return false
    const alphaNumericCount = (value.match(/[A-Za-z0-9\u00C0-\u024F]/g) || []).length
    const symbolRatio = 1 - (alphaNumericCount / value.length)
    return symbolRatio > 0.55
  }

  private looksLikeStructuredTelemetryNoise(value: string): boolean {
    const lowered = value.toLowerCase()
    const markers = [
      'event_type',
      'agent_role',
      'task_id',
      'metadata',
      'entities_count',
      'relationships_count',
      'memory_consolidated',
    ]
    const hitCount = markers.reduce((acc, marker) => (lowered.includes(marker) ? acc + 1 : acc), 0)
    return hitCount >= 3
  }
}
</file>

<file path="app/features/home/widgets/autonomy-widget/autonomy-widget.html">
<div class="widget-card group">
  <!-- Glow Background -->
  <div class="glow-bg"></div>

  <!-- Header -->
  <div class="widget-header">
    <div class="flex items-center">
      <div class="widget-icon">
        <span class="material-icons">smart_toy</span>
      </div>
      <div class="widget-title">
        <h3>Autonomy Loop</h3>
        <span>Agent Status</span>
      </div>
    </div>
    
    <div class="status-indicator" [class.active]="(status$ | async)?.active"></div>
  </div>

  <!-- Stats Grid -->
  <div class="stats-grid">
    <div class="stat-item">
      <span class="value">{{ (status$ | async)?.cycle_count | number:'1.0-0' }}</span>
      <span class="label">Ciclos</span>
    </div>
    <div class="stat-item">
      <span class="value text-sm mt-1" [ngClass]="getRiskColor(getRiskProfile((status$ | async)))">
        {{ getRiskProfile((status$ | async)) | uppercase }}
      </span>
      <span class="label">Perfil de Risco</span>
    </div>
  </div>

  <!-- Config Summary -->
  <div class="tags-area">
    <h4>Configuração</h4>
    <div class="tags-list">
      <span class="tag">
        Intervalo <span class="count">{{ (status$ | async)?.config?.interval_seconds || 0 }}s</span>
      </span>
      <span class="tag">
        Max Ações <span class="count">{{ (status$ | async)?.config?.max_actions_per_cycle || 0 }}</span>
      </span>
    </div>
  </div>

  <!-- Footer -->
  <div class="widget-footer">
    <button type="button" (click)="openAutonomyPanel()">
      Configurar <span class="material-icons text-[14px]">settings</span>
    </button>
  </div>
</div>
</file>

<file path="app/features/home/widgets/autonomy-widget/autonomy-widget.scss">
@use '../knowledge-widget/knowledge-widget.scss';

/* Custom Overrides for Autonomy Widget (Purple Theme) */
.widget-icon {
  background: rgba(var(--janus-accent-rgb), 0.1);
  color: var(--janus-accent);
  box-shadow: 0 0 15px rgba(var(--janus-accent-rgb), 0.15);
  
  .group:hover & {
    background: var(--janus-accent);
    box-shadow: 0 0 20px rgba(var(--janus-accent-rgb), 0.4);
  }
}

.stat-item:hover {
  border-color: rgba(var(--janus-accent-rgb), 0.3);
}

.tag {
  background: rgba(var(--janus-accent-rgb), 0.08);
  border: 1px solid rgba(var(--janus-accent-rgb), 0.15);
  color: var(--janus-accent-light);
}

.widget-footer button:hover {
  color: var(--janus-accent);
}

.glow-bg {
  background: radial-gradient(circle, rgba(var(--janus-accent-rgb), 0.15) 0%, transparent 70%);
}

.risk-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 0.7rem;
  font-family: var(--janus-font-mono);
  text-transform: uppercase;
  border: 1px solid transparent;
  
  &.conservative {
    background: rgba(var(--janus-success-rgb), 0.1);
    border-color: rgba(var(--janus-success-rgb), 0.2);
    color: var(--janus-success);
  }
  
  &.balanced {
    background: rgba(var(--janus-warning-rgb), 0.1);
    border-color: rgba(var(--janus-warning-rgb), 0.2);
    color: var(--janus-warning);
  }
  
  &.aggressive {
    background: rgba(var(--janus-error-rgb), 0.1);
    border-color: rgba(var(--janus-error-rgb), 0.2);
    color: var(--janus-error);
  }
}
</file>

<file path="app/features/home/widgets/autonomy-widget/autonomy-widget.spec.ts">
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';

import { AutonomyWidget } from './autonomy-widget';

describe('AutonomyWidget', () => {
  let component: AutonomyWidget;
  let fixture: ComponentFixture<AutonomyWidget>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AutonomyWidget, HttpClientTestingModule, RouterTestingModule]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AutonomyWidget);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
</file>

<file path="app/features/home/widgets/autonomy-widget/autonomy-widget.ts">
import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { BackendApiService, AutonomyStatusResponse } from '../../../../services/backend-api.service';
import { Observable, of } from 'rxjs';
import { catchError, shareReplay } from 'rxjs/operators';

@Component({
  selector: 'app-autonomy-widget',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './autonomy-widget.html',
  styleUrls: ['./autonomy-widget.scss'],
})
export class AutonomyWidget {
  private api = inject(BackendApiService);
  private router = inject(Router);

  status$: Observable<AutonomyStatusResponse | null>;

  constructor() {
    this.status$ = this.api.getAutonomyStatus().pipe(
      catchError(() => of(null)),
      shareReplay({ bufferSize: 1, refCount: true })
    );
  }

  getRiskProfile(status: AutonomyStatusResponse | null): string {
    return status?.config?.risk_profile || 'Unknown';
  }

  getRiskColor(risk: string | undefined): string {
    switch (risk?.toLowerCase()) {
      case 'aggressive': return 'text-red-400';
      case 'balanced': return 'text-yellow-400';
      case 'conservative': return 'text-green-400';
      default: return 'text-gray-400';
    }
  }

  openAutonomyPanel(): void {
    try {
      localStorage.setItem('janus.conversations.show_advanced_mode', '1');
      localStorage.setItem('janus.conversations.advanced_rail_tab', 'autonomia');
    } catch {
      // no-op
    }
    void this.router.navigate(['/conversations']);
  }
}
</file>

<file path="app/features/home/widgets/knowledge-widget/knowledge-widget.html">
<div class="widget-card group">
  <!-- Glow Background -->
  <div class="glow-bg"></div>

  <!-- Header -->
  <div class="widget-header">
    <div class="flex items-center">
      <div class="widget-icon">
        <span class="material-icons">hub</span>
      </div>
      <div class="widget-title">
        <h3>Grafo de Conhecimento</h3>
        <span>Memória Semântica</span>
      </div>
    </div>
    
    <div class="status-indicator" [class.active]="(stats$ | async)"></div>
  </div>

  <!-- Stats Grid -->
  <div class="stats-grid">
    <div class="stat-item">
      <span class="value">{{ (stats$ | async)?.total_nodes | number:'1.0-0' }}</span>
      <span class="label">Nós</span>
    </div>
    <div class="stat-item">
      <span class="value">{{ (stats$ | async)?.total_relationships | number:'1.0-0' }}</span>
      <span class="label">Arestas</span>
    </div>
  </div>

  <!-- Tags / Labels -->
  <div class="tags-area">
    <h4>Principais Conceitos</h4>
    <div class="tags-list" *ngIf="(stats$ | async)?.labels; else emptyTags">
      <span *ngFor="let item of getTopLabels((stats$ | async)!)" class="tag">
        {{ item.label }} <span class="count">{{ item.count }}</span>
      </span>
    </div>
    <ng-template #emptyTags>
      <div class="tags-list">
        <span class="tag empty">Scanning codebase...</span>
        <span class="tag empty">Analyzing concepts...</span>
      </div>
    </ng-template>
  </div>

  <!-- Footer -->
  <div class="widget-footer">
    <button type="button" (click)="openKnowledgeView()">
      Explorar Grafo <span class="material-icons text-[14px]">arrow_forward</span>
    </button>
  </div>
</div>
</file>

<file path="app/features/home/widgets/knowledge-widget/knowledge-widget.scss">
@use 'styles/tokens' as *;
@use 'styles/mixins' as *;

.widget-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  position: relative;
  /* O estilo base do container vem do home.scss, aqui estilizamos o conteúdo */
}

/* HEADER
   -------------------------------------------------- */
.widget-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  position: relative;
  z-index: 2;
}

.widget-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.25rem;
  background: rgba(var(--janus-primary-rgb), 0.1);
  color: var(--janus-primary);
  box-shadow: 0 0 15px rgba(var(--janus-primary-rgb), 0.15);
  transition: all 0.3s ease;
  
  .group:hover & {
    background: var(--janus-primary);
    color: white;
    transform: scale(1.1) rotate(-5deg);
    box-shadow: 0 0 20px rgba(var(--janus-primary-rgb), 0.4);
  }
}

.widget-title {
  display: flex;
  flex-direction: column;
  margin-left: 12px;
  
  h3 {
    font-family: $font-display;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--janus-text-primary);
    margin: 0;
    letter-spacing: 0.02em;
  }
  
  span {
    font-family: $font-mono;
    font-size: 0.65rem;
    color: var(--janus-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
  }
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--janus-surface-3);
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.05);
  
  &.active {
    background: var(--janus-success);
    box-shadow: 0 0 8px var(--janus-success);
    animation: pulse-green 2s infinite;
  }
}

@keyframes pulse-green {
  0% { box-shadow: 0 0 0 0 rgba(var(--janus-success-rgb), 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(var(--janus-success-rgb), 0); }
  100% { box-shadow: 0 0 0 0 rgba(var(--janus-success-rgb), 0); }
}

/* STATS GRID
   -------------------------------------------------- */
.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 20px;
}

.stat-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 8px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  transition: border-color 0.3s;
  
  &:hover {
    border-color: rgba(var(--janus-primary-rgb), 0.3);
  }
  
  .value {
    font-family: $font-mono;
    font-size: 1.5rem;
    font-weight: 700;
    color: var(--janus-text-primary);
    line-height: 1.2;
  }
  
  .label {
    font-size: 0.7rem;
    color: var(--janus-text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 4px;
  }
}

/* TAGS AREA
   -------------------------------------------------- */
.tags-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 16px; // Garante espaço antes do footer/separador
  
  h4 {
    font-size: 0.7rem;
    text-transform: uppercase;
    color: var(--janus-text-muted);
    letter-spacing: 0.1em;
    margin-bottom: 4px;
  }
}

.tags-list {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.tag {
  font-family: $font-mono;
  font-size: 0.7rem;
  padding: 4px 8px;
  border-radius: 4px;
  background: rgba(var(--janus-primary-rgb), 0.08);
  border: 1px solid rgba(var(--janus-primary-rgb), 0.15);
  color: var(--janus-primary-light);
  
  .count {
    opacity: 0.6;
    margin-left: 4px;
    font-size: 0.65rem;
  }
  
  &.empty {
    background: rgba(255, 255, 255, 0.03);
    border-color: rgba(255, 255, 255, 0.05);
    color: var(--janus-text-muted);
    font-style: italic;
  }
}

/* FOOTER
   -------------------------------------------------- */
.widget-footer {
  margin-top: auto;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  justify-content: flex-end;
  
  button {
    background: none;
    border: none;
    color: var(--janus-text-secondary);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    cursor: pointer;
    transition: color 0.2s;
    display: flex;
    align-items: center;
    gap: 6px;
    
    &:hover {
      color: var(--janus-primary);
      
      span {
        transform: translateX(3px);
      }
    }
    
    span {
      transition: transform 0.2s;
    }
  }
}

/* GLOW EFFECT
   -------------------------------------------------- */
.glow-bg {
  position: absolute;
  top: -20%;
  right: -20%;
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(var(--janus-primary-rgb), 0.15) 0%, transparent 70%);
  filter: blur(40px);
  pointer-events: none;
  opacity: 0.5;
  transition: opacity 0.5s ease;
  
  .group:hover & {
    opacity: 0.8;
  }
}
</file>

<file path="app/features/home/widgets/knowledge-widget/knowledge-widget.spec.ts">
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';

import { KnowledgeWidget } from './knowledge-widget';

describe('KnowledgeWidget', () => {
  let component: KnowledgeWidget;
  let fixture: ComponentFixture<KnowledgeWidget>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KnowledgeWidget, HttpClientTestingModule, RouterTestingModule]
    })
    .compileComponents();

    fixture = TestBed.createComponent(KnowledgeWidget);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
</file>

<file path="app/features/home/widgets/knowledge-widget/knowledge-widget.ts">
import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { BackendApiService, KnowledgeStats } from '../../../../services/backend-api.service';
import { Observable, of } from 'rxjs';
import { catchError, shareReplay } from 'rxjs/operators';

@Component({
  selector: 'app-knowledge-widget',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './knowledge-widget.html',
  styleUrls: ['./knowledge-widget.scss'],
})
export class KnowledgeWidget {
  private api = inject(BackendApiService);
  private router = inject(Router);

  stats$: Observable<KnowledgeStats | null>;

  constructor() {
    this.stats$ = this.api.getKnowledgeStats().pipe(
      catchError(() => of(null)),
      shareReplay({ bufferSize: 1, refCount: true })
    );
  }

  getTopLabels(stats: KnowledgeStats): { label: string; count: number }[] {
    if (!stats?.labels) return [];
    return Object.entries(stats.labels)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 4)
      .map(([label, count]) => ({ label, count }));
  }

  openKnowledgeView(): void {
    void this.router.navigate(['/observability']);
  }
}
</file>

<file path="app/features/home/widgets/learning-widget/learning-widget.html">
<div class="widget-card group">
  <!-- Glow Background -->
  <div class="glow-bg"></div>

  <!-- Header -->
  <div class="widget-header">
    <div class="flex items-center">
      <div class="widget-icon">
        <span class="material-icons">lightbulb</span>
      </div>
      <div class="widget-title">
        <h3>Reflexão</h3>
        <span>Aprendizado Contínuo</span>
      </div>
    </div>
    
    <div class="status-indicator" [class.active]="(summary$ | async)?.lessons?.length"></div>
  </div>

  <!-- Content Area -->
  <div class="flex-1 overflow-hidden flex flex-col">
    <div *ngIf="(summary$ | async)?.lessons?.length; else emptyState" class="flex-1 overflow-y-auto pr-1 space-y-2">
      <div *ngFor="let lesson of (summary$ | async)?.lessons" class="lesson-card">
        <p>"{{ lesson.content }}"</p>
        <div class="meta">
          <span>{{ lesson.id }}</span>
          <span class="score" *ngIf="lesson.score">★ {{ lesson.score }}</span>
        </div>
      </div>
    </div>
    
    <ng-template #emptyState>
      <div class="empty-state">
        <span class="icon">🧠</span>
        <p>Ainda estou aprendendo...</p>
      </div>
    </ng-template>
  </div>

  <!-- Footer -->
  <div class="widget-footer">
    <button type="button" (click)="openLearningInsights()">
      Ver Todas as Lições <span class="material-icons text-[14px]">arrow_forward</span>
    </button>
  </div>
</div>
</file>

<file path="app/features/home/widgets/learning-widget/learning-widget.scss">
@use '../knowledge-widget/knowledge-widget.scss';

/* Custom Overrides for Learning Widget (Orange Theme) */
.widget-icon {
  background: rgba(var(--janus-warning-rgb), 0.1);
  color: var(--janus-warning);
  box-shadow: 0 0 15px rgba(var(--janus-warning-rgb), 0.15);
  
  .group:hover & {
    background: var(--janus-warning);
    box-shadow: 0 0 20px rgba(var(--janus-warning-rgb), 0.4);
  }
}

.widget-footer button:hover {
  color: var(--janus-warning);
}

.glow-bg {
  background: radial-gradient(circle, rgba(var(--janus-warning-rgb), 0.15) 0%, transparent 70%);
}

.lesson-card {
  background: rgba(var(--janus-surface-2-rgb), 0.4);
  border: 1px solid rgba(var(--janus-border-rgb), 0.3);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
  transition: all 0.2s;
  cursor: default;
  
  &:hover {
    border-color: rgba(var(--janus-warning-rgb), 0.4);
    background: rgba(var(--janus-surface-2-rgb), 0.6);
  }
  
  p {
    font-size: 0.8rem;
    color: var(--janus-text-secondary);
    line-height: 1.4;
    margin: 0 0 8px;
    
    // Clamp 2 lines
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  
  .meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.65rem;
    font-family: var(--janus-font-mono);
    color: var(--janus-text-muted);
    
    .score {
      color: var(--janus-warning);
      font-weight: 700;
    }
  }
}

.empty-state {
  height: 140px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  opacity: 0.8;
  
  .icon {
    font-size: 2rem;
    margin-bottom: 12px;
    filter: drop-shadow(0 0 10px rgba(var(--janus-warning-rgb), 0.3));
  }
  
  p {
    font-size: 0.9rem;
    color: var(--janus-text-secondary);
    margin-bottom: 12px;
  }

  .start-btn {
    background: rgba(var(--janus-warning-rgb), 0.15);
    border: 1px solid rgba(var(--janus-warning-rgb), 0.3);
    color: var(--janus-warning);
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;

    &:hover {
      background: var(--janus-warning);
      color: var(--janus-bg-dark);
      box-shadow: 0 0 15px rgba(var(--janus-warning-rgb), 0.4);
    }
  }
}
</file>

<file path="app/features/home/widgets/learning-widget/learning-widget.spec.ts">
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';

import { LearningWidget } from './learning-widget';

describe('LearningWidget', () => {
  let component: LearningWidget;
  let fixture: ComponentFixture<LearningWidget>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LearningWidget, HttpClientTestingModule, RouterTestingModule]
    })
    .compileComponents();

    fixture = TestBed.createComponent(LearningWidget);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
</file>

<file path="app/features/home/widgets/learning-widget/learning-widget.ts">
import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { BackendApiService, PostSprintSummaryResponse } from '../../../../services/backend-api.service';
import { Observable, of } from 'rxjs';
import { catchError, shareReplay } from 'rxjs/operators';

@Component({
  selector: 'app-learning-widget',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './learning-widget.html',
  styleUrls: ['./learning-widget.scss'],
})
export class LearningWidget {
  private api = inject(BackendApiService);
  private router = inject(Router);

  summary$: Observable<PostSprintSummaryResponse | null>;

  constructor() {
    this.summary$ = this.api.getReflexionSummary(5).pipe(
      catchError(() => of(null)),
      shareReplay({ bufferSize: 1, refCount: true })
    );
  }

  openLearningInsights(): void {
    try {
      localStorage.setItem('janus.conversations.show_advanced_mode', '1');
      localStorage.setItem('janus.conversations.advanced_rail_tab', 'insights');
    } catch {
      // no-op
    }
    void this.router.navigate(['/conversations']);
  }
}
</file>

<file path="app/features/home/home.html">
<section class="home">
  <app-header></app-header>

  <div class="home-shell">
    <!-- HERO SECTION: O Centro de Comando -->
    <header class="home-hero relative overflow-hidden">
      <!-- Background Abstract Elements -->
      <div class="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none z-0">
        <div class="absolute top-[-20%] right-[-10%] w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[100px]"></div>
        <div class="absolute bottom-[-10%] left-[-10%] w-[400px] h-[400px] bg-purple-600/10 rounded-full blur-[100px]"></div>
      </div>

      <div class="hero-content relative z-10 max-w-4xl mx-auto text-center pt-12 pb-8">
        <p class="eyebrow mb-4 inline-block px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-mono tracking-widest text-gray-400">
          JANUS // COCKPIT
        </p>
        
        <h1 class="text-4xl md:text-5xl font-bold text-white mb-4 tracking-tight">
          Olá, {{ displayName() }}
        </h1>
        
        <p class="sub text-lg text-gray-400 mb-8 max-w-2xl mx-auto">
          O que vamos criar, analisar ou explorar hoje? O sistema está pronto.
        </p>

        <!-- Main Input -->
        <div class="max-w-2xl mx-auto mb-8 relative group">
          <div class="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg blur opacity-30 group-hover:opacity-60 transition duration-500"></div>
          <div class="relative flex items-center bg-gray-900 rounded-lg border border-gray-700 shadow-2xl">
            <input 
              type="text" 
              [formControl]="prompt"
              (keyup.enter)="startChat()"
              placeholder="Descreva sua tarefa... (Ex: 'Criar um novo agente', 'Analisar logs')" 
              class="w-full bg-transparent border-none text-white px-6 py-4 text-lg focus:ring-0 placeholder-gray-500"
            />
            <button 
              (click)="startChat()"
              [disabled]="actionLoading()"
              class="mr-2 p-2 bg-blue-600 hover:bg-blue-500 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center min-w-[44px]"
            >
              <span class="material-icons" *ngIf="!actionLoading()">arrow_forward</span>
              <span class="animate-spin h-5 w-5 border-2 border-white/30 border-t-white rounded-full" *ngIf="actionLoading()"></span>
            </button>
          </div>
        </div>

        <!-- Quick Actions / Suggestions -->
        <div class="flex flex-wrap justify-center gap-2">
          @for (suggestion of suggestions; track suggestion) {
            <button 
              (click)="applySuggestion(suggestion)"
              class="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/5 rounded-full text-sm text-gray-400 hover:text-white transition-all cursor-pointer"
            >
              {{ suggestion }}
            </button>
          }
        </div>
      </div>
    </header>

    <!-- DASHBOARD GRID: Inteligência Ativa -->
    <div class="home-grid">
      <h2 class="section-title">Sistema & Inteligência</h2>
      
      <div class="widgets-row">
        <!-- Widget 1: Conhecimento (Grafo) -->
        <app-knowledge-widget class="h-full"></app-knowledge-widget>

        <!-- Widget 2: Autonomia (Agentes) -->
        <app-autonomy-widget class="h-full"></app-autonomy-widget>

        <!-- Widget 3: Aprendizado (Reflexion) -->
        <app-learning-widget class="h-full"></app-learning-widget>
      </div>

      <!-- RECENT ACTIVITY SECTION -->
      <div class="mt-12">
        <div class="flex items-center justify-between mb-6 px-2">
           <h2 class="section-title !mb-0">Conversas Recentes</h2>
           <button routerLink="/conversations" class="text-xs text-blue-400 hover:text-blue-300 font-mono uppercase tracking-wider">Ver todas</button>
        </div>

        <div class="activity-grid">
          @if (loading()) {
            <app-skeleton variant="card" [count]="2"></app-skeleton>
          } @else if (conversations().length) {
            @for (conv of conversations(); track conv.conversation_id) {
              <div 
                (click)="openConversation(conv.conversation_id)"
                class="activity-card"
              >
                <div class="flex justify-between items-start mb-2">
                  <h3>
                    {{ conv.title || 'Conversa sem título' }}
                  </h3>
                  <span class="meta">{{ conv.updated_at | date:'short' }}</span>
                </div>
                <p>
                  {{ conv.last_message?.text || 'Iniciar conversa...' }}
                </p>
              </div>
            }
          } @else {
            <div class="col-span-2 text-center py-8 border border-dashed border-gray-800 rounded-lg">
              <p class="text-gray-500 text-sm">Nenhuma conversa recente.</p>
            </div>
          }
        </div>
      </div>
    </div>
  </div>
</section>
</file>

<file path="app/features/home/home.scss">
@use 'styles/tokens' as *;
@use 'styles/mixins' as *;

.home {
  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--janus-bg-app);
}

.home-shell {
  width: 100%;
  display: flex;
  flex-direction: column;
}

/* HERO SECTION
   -------------------------------------------------- */
.home-hero {
  position: relative;
  width: 100%;
  min-height: 480px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid rgba(var(--janus-border-rgb), 0.6);
  background: 
    radial-gradient(circle at 50% 30%, rgba(var(--janus-primary-rgb), 0.08) 0%, transparent 60%),
    radial-gradient(circle at 80% 80%, rgba(var(--janus-secondary-rgb), 0.05) 0%, transparent 50%),
    var(--janus-bg-dark);
    
  &::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(var(--janus-primary-rgb), 0.5), transparent);
  }
}

.hero-content {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 900px;
  padding: 0 24px;
  text-align: center;
}

.eyebrow {
  font-family: $font-mono;
  font-size: 0.75rem;
  letter-spacing: 0.25em;
  text-transform: uppercase;
  color: var(--janus-text-muted);
  margin-bottom: 1.5rem;
  display: inline-block;
  padding: 6px 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(4px);
}

h1 {
  font-family: $font-display;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--janus-text-primary);
  margin-bottom: 1rem;
  text-shadow: 0 0 40px rgba(var(--janus-primary-rgb), 0.3);
}

.sub {
  font-family: $font-body;
  font-size: 1.1rem;
  line-height: 1.6;
  color: var(--janus-text-secondary);
  margin-bottom: 3rem;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

/* HERO INPUT
   -------------------------------------------------- */
.hero-input-wrapper {
  position: relative;
  max-width: 640px;
  margin: 0 auto 2rem;
  transition: transform 0.3s ease;
  
  &:hover {
    transform: translateY(-2px);
  }
  
  // Glow effect behind input
  &::before {
    content: '';
    position: absolute;
    inset: -2px;
    background: linear-gradient(45deg, var(--janus-primary), var(--janus-secondary));
    border-radius: 14px;
    filter: blur(12px);
    opacity: 0.25;
    transition: opacity 0.3s ease;
  }
  
  &:focus-within::before {
    opacity: 0.5;
  }
}

.hero-input-container {
  position: relative;
  display: flex;
  align-items: center;
  background: rgba(10, 14, 23, 0.85); // Darker surface
  backdrop-filter: blur(12px);
  border: 1px solid rgba(var(--janus-border-rgb), 0.8);
  border-radius: 12px;
  padding: 6px;
  box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.5);
  
  input {
    flex: 1;
    background: transparent;
    border: none;
    padding: 14px 20px;
    color: var(--janus-text-primary);
    font-size: 1.1rem;
    font-family: $font-body;
    outline: none;
    
    &::placeholder {
      color: rgba(var(--janus-text-muted-rgb), 0.6);
    }
  }
  
  button {
    background: var(--janus-primary);
    color: white;
    border: none;
    width: 44px;
    height: 44px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.2s;
    
    &:hover:not(:disabled) {
      background: var(--janus-primary-hover);
      box-shadow: 0 0 15px rgba(var(--janus-primary-rgb), 0.4);
    }
    
    &:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      background: var(--janus-surface-3);
    }
  }
}

/* DASHBOARD GRID
   -------------------------------------------------- */
.home-grid {
  padding: 40px 24px 80px;
  max-width: 1280px;
  margin: 0 auto;
  width: 100%;
}

.section-title {
  font-family: $font-mono;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  color: var(--janus-text-muted);
  margin-bottom: 1.5rem;
  padding-left: 8px;
  border-left: 2px solid var(--janus-primary);
}

.widgets-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  margin-bottom: 48px;
  
  @media (max-width: 1024px) {
    grid-template-columns: repeat(2, 1fr);
  }
  
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
}

/* CARDS GENÉRICOS (Fallback para widgets sem componente próprio) */
.widget-card {
  @include glass-panel;
  background: rgba(15, 23, 42, 0.6); // Base sólida escura
  border: 1px solid rgba(var(--janus-border-rgb), 0.5);
  border-radius: 16px;
  padding: 24px;
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
  position: relative;
  overflow: hidden;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); // Sombra leve
  
  // Subtle gradient overlay
  &::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(to bottom right, rgba(255,255,255,0.05), transparent 60%);
    pointer-events: none;
    border-radius: 16px; // Match card radius
  }

  &:hover {
    transform: translateY(-4px);
    border-color: rgba(var(--janus-primary-rgb), 0.4);
    box-shadow: 0 12px 40px -8px rgba(0, 0, 0, 0.4);
    background: rgba(15, 23, 42, 0.8); // Mais opaco no hover
  }
}

/* RECENT ACTIVITY
   -------------------------------------------------- */
.activity-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
}

.activity-card {
  @include glass-panel;
  background: rgba(var(--janus-surface-1-rgb), 0.3);
  border: 1px solid rgba(var(--janus-border-rgb), 0.4);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background: rgba(var(--janus-surface-2-rgb), 0.5);
    border-color: var(--janus-primary);
    transform: translateX(4px);
    
    h3 {
      color: var(--janus-primary);
    }
  }
  
  h3 {
    font-family: $font-display;
    font-size: 1rem;
    color: var(--janus-text-primary);
    margin-bottom: 0.5rem;
    transition: color 0.2s;
  }
  
  p {
    font-size: 0.9rem;
    color: var(--janus-text-secondary);
    line-height: 1.5;
    
    // Line clamp 2 lines
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  
  .meta {
    font-family: $font-mono;
    font-size: 0.75rem;
    color: var(--janus-text-muted);
    margin-top: 12px;
    display: block;
  }
}
</file>

<file path="app/features/home/home.ts">
import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core'
import { CommonModule } from '@angular/common'
import { RouterLink } from '@angular/router'
import { FormControl, ReactiveFormsModule } from '@angular/forms'
import { of } from 'rxjs'
import { catchError, map } from 'rxjs/operators'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import { Router } from '@angular/router'

import { AuthService } from '../../core/auth/auth.service'
import {
  ConversationMeta,
  BackendApiService
} from '../../services/backend-api.service'
import { Header } from '../../core/layout/header/header'
import { SkeletonComponent } from '../../shared/components/skeleton/skeleton.component'

// Widgets
import { KnowledgeWidget } from './widgets/knowledge-widget/knowledge-widget'
import { AutonomyWidget } from './widgets/autonomy-widget/autonomy-widget'
import { LearningWidget } from './widgets/learning-widget/learning-widget'

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    ReactiveFormsModule,
    Header,
    SkeletonComponent,
    KnowledgeWidget,
    AutonomyWidget,
    LearningWidget
  ],
  templateUrl: './home.html',
  styleUrls: ['./home.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class HomeComponent {
  private api = inject(BackendApiService)
  private auth = inject(AuthService)
  private destroyRef = inject(DestroyRef)
  private router = inject(Router)

  readonly prompt = new FormControl('', { nonNullable: true })
  readonly loading = signal(true)
  readonly actionLoading = signal(false)
  readonly error = signal('')
  readonly notice = signal('')
  
  readonly conversations = signal<ConversationMeta[]>([])

  readonly user = this.auth.user
  readonly suggestions = [
    'Criar um novo agente de vendas',
    'Analisar os logs de erro de hoje',
    'Resumir o documento de arquitetura',
    'Gerar testes para o módulo de pagamentos'
  ]

  readonly displayName = computed(() => {
    const user = this.user()
    return user?.display_name || user?.username || user?.email?.split('@')[0] || 'Criador'
  })

  constructor() {
    this.loadRecentConversations()
  }

  applySuggestion(value: string) {
    this.prompt.setValue(value)
  }

  startChat() {
    if (this.actionLoading()) return
    const intent = this.prompt.value.trim()
    
    this.actionLoading.set(true)
    this.notice.set('')
    this.error.set('')
    
    const userId = this.user()?.id ? String(this.user()?.id) : undefined
    
    // Se tiver intenção, passamos como mensagem inicial (ainda não suportado diretamente no startChat pelo front, 
    // mas vamos criar e depois enviar mensagem ou assumir que o fluxo de chat lida com isso. 
    // Por enquanto, criamos a conversa e navegamos.)
    
    this.api.startChat(undefined, undefined, userId)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError(() => {
          this.error.set('Falha ao iniciar conversa.')
          this.actionLoading.set(false)
          return of(null)
        })
      )
      .subscribe((resp) => {
        if (resp) {
          // Se tiver intenção, poderíamos enviar a mensagem aqui, mas vamos deixar o usuário digitar lá
          // ou passar via query param se o chat suportar.
          this.router.navigate(['/conversations', resp.conversation_id], {
             queryParams: intent ? { initialPrompt: intent } : undefined 
          })
        }
        this.actionLoading.set(false)
      })
  }

  openConversation(conversationId: string) {
    if (!conversationId) return
    this.router.navigate(['/conversations', conversationId])
  }

  private loadRecentConversations() {
    const userId = this.user()?.id ? String(this.user()?.id) : undefined
    this.api.listConversations(userId ? { user_id: userId, limit: 4 } : { limit: 4 })
      .pipe(
        map((resp) => (resp.conversations || []).map((conv) => this.normalizeConversationTimestamps(conv))),
        catchError(() => of([]))
      )
      .subscribe(convs => {
        this.conversations.set(convs)
        this.loading.set(false)
      })
  }

  private normalizeConversationTimestamps(conv: ConversationMeta): ConversationMeta {
    const createdAt = this.normalizeTimestamp(conv.created_at)
    const updatedAt = this.normalizeTimestamp(conv.updated_at) ?? createdAt
    return {
      ...conv,
      created_at: createdAt ?? undefined,
      updated_at: updatedAt ?? undefined,
    }
  }

  private normalizeTimestamp(value: unknown): number | null {
    if (value === null || value === undefined) return null
    const n = typeof value === 'string' ? Number(value) : Number(value)
    if (Number.isFinite(n)) {
      return n < 1_000_000_000_000 ? n * 1000 : n
    }
    if (typeof value === 'string') {
      const parsed = Date.parse(value)
      if (Number.isFinite(parsed)) return parsed
    }
    return null
  }
}
</file>

<file path="app/features/observability/widgets/database-health-widget/database-health-widget.html">
<div class="widget">
    @if (loading()) {
    <div class="loading-state">
        <div class="spinner"></div>
        <p>Loading DB validation...</p>
    </div>
    } @else if (error()) {
    <div class="error-state">
        <span class="material-icons">error_outline</span>
        <p>{{ error() }}</p>
    </div>
    } @else {
    <div class="widget-header">
        <h3>Database Validation</h3>
        <button class="export-btn" (click)="exportToJSON()" title="Export to JSON">
            <span class="material-icons">download</span>
        </button>
    </div>

    <!-- Summary Cards -->
    <div class="summary-grid">
        <div class="summary-card exists">
            <span class="count">{{ getStatusSummary().exists }}</span>
            <span class="label">Exists</span>
        </div>
        <div class="summary-card missing">
            <span class="count">{{ getStatusSummary().missing }}</span>
            <span class="label">Missing</span>
        </div>
    </div>

    <!-- Filter Buttons -->
    <div class="filter-bar">
        <button [class.active]="filter() === 'all'" (click)="filter.set('all')">All</button>
        <button [class.active]="filter() === 'exists'" (click)="filter.set('exists')">Exists</button>
        <button [class.active]="filter() === 'missing'" (click)="filter.set('missing')">Missing</button>
    </div>

    <!-- Checks Table -->
    <div class="table-container">
        <table>
            <thead>
                <tr>
                    <th>Table</th>
                    <th>Object</th>
                    <th>Type</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                @for (check of filteredChecks(); track check.name) {
                <tr>
                    <td>{{ check.table }}</td>
                    <td class="object-name">{{ check.name }}</td>
                    <td><span class="type-badge">{{ check.kind }}</span></td>
                    <td>
                        <span class="status-icon" [class.exists]="check.exists" [class.missing]="!check.exists">
                            <span class="material-icons">{{ check.exists ? 'check_circle' : 'cancel' }}</span>
                        </span>
                    </td>
                </tr>
                } @empty {
                <tr>
                    <td colspan="4" class="no-data">No checks match current filter</td>
                </tr>
                }
            </tbody>
        </table>
    </div>
    }
</div>
</file>

<file path="app/features/observability/widgets/database-health-widget/database-health-widget.scss">
@use '../system-status-widget/system-status-widget';

.export-btn {
    padding: 0.5rem 1rem;
    background: rgba(59, 130, 246, 0.15);
    border: 1px solid rgba(59, 130, 246, 0.3);
    border-radius: 0.375rem;
    color: #60a5fa;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    transition: all 0.2s;

    .material-icons {
        font-size: 1.125rem;
    }

    &:hover {
        background: rgba(59, 130, 246, 0.25);
        border-color: rgba(59, 130, 246, 0.5);
    }
}

.summary-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.75rem;
    margin-bottom: 1rem;
}

.summary-card {
    padding: 1rem;
    border-radius: 0.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.25rem;

    &.exists {
        background: rgba(34, 197, 94, 0.1);
        border: 1px solid rgba(34, 197, 94, 0.2);
    }

    &.missing {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.2);
    }

    .count {
        font-size: 2rem;
        font-weight: 700;
        color: #ffffff;
    }

    .label {
        font-size: 0.75rem;
        color: #9ca3af;
        text-transform: uppercase;
    }
}

.filter-bar {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;

    button {
        padding: 0.5rem 1rem;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 0.375rem;
        color: #9ca3af;
        font-size: 0.85rem;
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
            background: rgba(255, 255, 255, 0.08);
        }

        &.active {
            background: rgba(59, 130, 246, 0.15);
            border-color: rgba(59, 130, 246, 0.4);
            color: #60a5fa;
        }
    }
}

.table-container {
    overflow-x: auto;
    border-radius: 0.5rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

table {
    width: 100%;
    border-collapse: collapse;

    thead {
        background: rgba(255, 255, 255, 0.05);

        th {
            padding: 0.75rem;
            text-align: left;
            font-size: 0.75rem;
            font-weight: 600;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
    }

    tbody {
        tr {
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);

            &:hover {
                background: rgba(255, 255, 255, 0.03);
            }
        }

        td {
            padding: 0.75rem;
            font-size: 0.875rem;
            color: #e0e0e0;

            &.object-name {
                font-family: 'Courier New', monospace;
                font-size: 0.8rem;
                color: #60a5fa;
            }

            &.no-data {
                text-align: center;
                color: #6b7280;
                padding: 2rem;
            }
        }
    }
}

.type-badge {
    display: inline-block;
    padding: 0.25rem 0.5rem;
    background: rgba(139, 92, 246, 0.15);
    border-radius: 0.25rem;
    font-size: 0.75rem;
    color: #a78bfa;
    text-transform: uppercase;
}

.status-icon {
    display: flex;
    align-items: center;

    .material-icons {
        font-size: 1.25rem;
    }

    &.exists .material-icons {
        color: #4ade80;
    }

    &.missing .material-icons {
        color: #f87171;
    }
}
</file>

<file path="app/features/observability/widgets/database-health-widget/database-health-widget.ts">
import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { interval, Subscription } from 'rxjs';
import { switchMap, catchError } from 'rxjs/operators';
import { of } from 'rxjs';
import { BackendApiService, DbValidationResponse, DbValidationCheck } from '../../../../services/backend-api.service';

@Component({
    selector: 'app-database-health-widget',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './database-health-widget.html',
    styleUrls: ['./database-health-widget.scss']
})
export class DatabaseHealthWidgetComponent implements OnInit, OnDestroy {
    private api = inject(BackendApiService);
    private refreshSub?: Subscription;

    validation = signal<DbValidationResponse | null>(null);
    loading = signal(true);
    error = signal<string | null>(null);
    filter = signal<'all' | 'exists' | 'missing'>('all');

    ngOnInit(): void {
        this.loadData();
        this.startAutoRefresh();
    }

    ngOnDestroy(): void {
        this.refreshSub?.unsubscribe();
    }

    private loadData(): void {
        this.loading.set(true);
        this.error.set(null);

        this.api.getSystemDbValidate().pipe(
            catchError((err) => {
                this.error.set(err.message || 'Failed to load DB validation');
                return of(null);
            })
        ).subscribe(data => {
            this.validation.set(data);
            this.loading.set(false);
        });
    }

    private startAutoRefresh(): void {
        this.refreshSub = interval(5000).pipe(
            switchMap(() => this.api.getSystemDbValidate().pipe(catchError(() => of(null))))
        ).subscribe(data => {
            if (data) this.validation.set(data);
        });
    }

    filteredChecks(): DbValidationCheck[] {
        const checks = this.validation()?.checks || [];
        const f = this.filter();
        if (f === 'exists') return checks.filter(c => c.exists);
        if (f === 'missing') return checks.filter(c => !c.exists);
        return checks;
    }

    exportToJSON(): void {
        const data = JSON.stringify(this.validation(), null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `db-validation-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    getStatusSummary(): { exists: number; missing: number } {
        const checks = this.validation()?.checks || [];
        return {
            exists: checks.filter(c => c.exists).length,
            missing: checks.filter(c => !c.exists).length
        };
    }
}
</file>

<file path="app/features/observability/widgets/knowledge-health-widget/knowledge-health-widget.html">
<div class="widget">
    @if (loading()) {
    <div class="loading-state">
        <div class="spinner"></div>
        <p>Loading knowledge health...</p>
    </div>
    } @else if (error()) {
    <div class="error-state">
        <span class="material-icons">error_outline</span>
        <p>{{ error() }}</p>
    </div>
    } @else {
    <div class="widget-header">
        <h3>Knowledge Health</h3>
        <span class="status-badge" [class]="'status-' + getOverallStatus()">
            {{ getOverallStatus() }}
        </span>
    </div>

    <!-- Connection Status -->
    <div class="connection-grid">
        <div class="connection-card">
            <div class="connection-header">
                <span class="connection-name">Neo4j</span>
                <span class="connection-status" [class.connected]="health()?.neo4j_connected"
                    [class.disconnected]="!health()?.neo4j_connected">
                    {{ getConnectionStatus('neo4j') }}
                </span>
            </div>
            @if (health()?.neo4j_connected) {
            <div class="connection-metrics">
                <span>{{ health()?.total_nodes || 0 }} nodes</span>
                <span>{{ health()?.total_relationships || 0 }} relationships</span>
            </div>
            }
        </div>

        <div class="connection-card">
            <div class="connection-header">
                <span class="connection-name">Qdrant</span>
                <span class="connection-status" [class.connected]="health()?.qdrant_connected"
                    [class.disconnected]="!health()?.qdrant_connected">
                    {{ getConnectionStatus('qdrant') }}
                </span>
            </div>
        </div>
    </div>

    <!-- Circuit Breaker -->
    <div class="circuit-breaker-section">
        <div class="circuit-header">
            <span class="circuit-label">Circuit Breaker</span>
            <div class="circuit-indicator" [class.open]="health()?.circuit_breaker_open"
                [class.closed]="!health()?.circuit_breaker_open">
                <span class="indicator-light"></span>
                <span>{{ health()?.circuit_breaker_open ? 'OPEN' : 'CLOSED' }}</span>
            </div>
        </div>
        @if (health()?.circuit_breaker_open) {
        <button class="reset-btn" (click)="resetCircuitBreaker()" [disabled]="resetting()">
            <span class="material-icons">refresh</span>
            {{ resetting() ? 'Resetting...' : 'Reset Circuit Breaker' }}
        </button>
        }
    </div>

    <!-- Detailed Metrics (Collapsible) -->
    @if (detailed()) {
    <button class="toggle-detailed-btn" (click)="toggleDetailed()">
        <span>{{ showDetailed() ? 'Hide' : 'Show' }} Detailed Metrics</span>
        <span class="material-icons">{{ showDetailed() ? 'expand_less' : 'expand_more' }}</span>
    </button>

    @if (showDetailed()) {
    <div class="detailed-metrics">
        <div class="metric-item">
            <span class="metric-label">Status:</span>
            <span>{{ detailed()?.overall_status }}</span>
        </div>
        <div class="metric-item">
            <span class="metric-label">Timestamp:</span>
            <span>{{ detailed()?.timestamp }}</span>
        </div>
        @if (detailed()?.recommendations && detailed()!.recommendations.length > 0) {
        <div class="recommendations">
            <h5>Recommendations:</h5>
            <ul>
                @for (rec of detailed()!.recommendations; track rec) {
                <li>{{ rec }}</li>
                }
            </ul>
        </div>
        }
    </div>
    }
    }
    }
</div>
</file>

<file path="app/features/observability/widgets/knowledge-health-widget/knowledge-health-widget.scss">
@use '../system-status-widget/system-status-widget';

.connection-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 0.75rem;
    margin-bottom: 1.5rem;
}

.connection-card {
    padding: 1rem;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 0.5rem;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .connection-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;

        .connection-name {
            font-weight: 600;
            color: #ffffff;
            font-size: 0.95rem;
        }

        .connection-status {
            font-size: 0.75rem;
            padding: 0.25rem 0.5rem;
            border-radius: 0.25rem;
            text-transform: uppercase;
            font-weight: 600;

            &.connected {
                background: rgba(34, 197, 94, 0.15);
                color: #4ade80;
            }

            &.disconnected {
                background: rgba(239, 68, 68, 0.15);
                color: #f87171;
            }
        }
    }

    .connection-metrics {
        display: flex;
        gap: 0.75rem;
        font-size: 0.8rem;
        color: #9ca3af;

        span {
            &::before {
                content: '●';
                margin-right: 0.25rem;
                color: #60a5fa;
            }
        }
    }
}

.circuit-breaker-section {
    padding: 1rem;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 0.5rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
    margin-bottom: 1rem;

    .circuit-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.75rem;

        .circuit-label {
            font-weight: 600;
            color: #ffffff;
            font-size: 0.95rem;
        }

        .circuit-indicator {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.375rem 0.75rem;
            border-radius: 0.375rem;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;

            .indicator-light {
                width: 10px;
                height: 10px;
                border-radius: 50%;
            }

            &.closed {
                background: rgba(34, 197, 94, 0.15);
                color: #4ade80;
                border: 1px solid rgba(34, 197, 94, 0.3);

                .indicator-light {
                    background: #4ade80;
                    box-shadow: 0 0 8px rgba(74, 222, 128, 0.6);
                }
            }

            &.open {
                background: rgba(239, 68, 68, 0.15);
                color: #f87171;
                border: 1px solid rgba(239, 68, 68, 0.3);

                .indicator-light {
                    background: #f87171;
                    box-shadow: 0 0 8px rgba(248, 113, 113, 0.6);
                    animation: pulse 2s infinite;
                }
            }
        }
    }

    .reset-btn {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.625rem 1rem;
        background: rgba(251, 191, 36, 0.15);
        border: 1px solid rgba(251, 191, 36, 0.3);
        border-radius: 0.375rem;
        color: #fbbf24;
        font-size: 0.85rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s;
        width: 100%;
        justify-content: center;

        .material-icons {
            font-size: 1.125rem;
        }

        &:hover:not(:disabled) {
            background: rgba(251, 191, 36, 0.25);
            border-color: rgba(251, 191, 36, 0.5);
        }

        &:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
    }
}

@keyframes pulse {

    0%,
    100% {
        opacity: 1;
    }

    50% {
        opacity: 0.5;
    }
}

.toggle-detailed-btn {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.5rem;
    color: #e0e0e0;
    font-size: 0.9rem;
    cursor: pointer;
    transition: all 0.2s;
    width: 100%;
    margin-bottom: 1rem;

    &:hover {
        background: rgba(255, 255, 255, 0.05);
        border-color: rgba(255, 255, 255, 0.2);
    }

    .material-icons {
        font-size: 1.25rem;
        color: #60a5fa;
    }
}

.detailed-metrics {
    padding: 1rem;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 0.5rem;
    border: 1px solid rgba(255, 255, 255, 0.1);

    .metric-item {
        display: flex;
        justify-content: space-between;
        padding: 0.5rem 0;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
        font-size: 0.85rem;

        &:last-child {
            border-bottom: none;
        }

        .metric-label {
            font-weight: 600;
            color: #9ca3af;
        }

        span:last-child {
            color: #e0e0e0;
        }
    }

    .recommendations {
        margin-top: 0.75rem;
        padding-top: 0.75rem;
        border-top: 1px solid rgba(255, 255, 255, 0.1);

        h5 {
            font-size: 0.85rem;
            font-weight: 600;
            color: #fbbf24;
            margin: 0 0 0.5rem 0;
            text-transform: uppercase;
        }

        ul {
            list-style: none;
            padding: 0;
            margin: 0;

            li {
                padding: 0.375rem 0;
                font-size: 0.8rem;
                color: #9ca3af;

                &::before {
                    content: '▸';
                    margin-right: 0.5rem;
                    color: #fbbf24;
                }
            }
        }
    }
}

.status-degraded {
    background: rgba(251, 191, 36, 0.15);
    color: #fbbf24;
    border: 1px solid rgba(251, 191, 36, 0.3);
}

.status-unknown {
    background: rgba(156, 163, 175, 0.15);
    color: #9ca3af;
    border: 1px solid rgba(156, 163, 175, 0.3);
}
</file>

<file path="app/features/observability/widgets/knowledge-health-widget/knowledge-health-widget.ts">
import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { interval, Subscription } from 'rxjs';
import { switchMap, catchError } from 'rxjs/operators';
import { of } from 'rxjs';
import { BackendApiService, KnowledgeHealthResponse, KnowledgeHealthDetailedResponse } from '../../../../services/backend-api.service';

@Component({
    selector: 'app-knowledge-health-widget',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './knowledge-health-widget.html',
    styleUrls: ['./knowledge-health-widget.scss']
})
export class KnowledgeHealthWidgetComponent implements OnInit, OnDestroy {
    private api = inject(BackendApiService);
    private refreshSub?: Subscription;

    health = signal<KnowledgeHealthResponse | null>(null);
    detailed = signal<KnowledgeHealthDetailedResponse | null>(null);
    loading = signal(true);
    error = signal<string | null>(null);
    showDetailed = signal(false);
    resetting = signal(false);

    ngOnInit(): void {
        this.loadData();
        this.startAutoRefresh();
    }

    ngOnDestroy(): void {
        this.refreshSub?.unsubscribe();
    }

    private loadData(): void {
        this.loading.set(true);
        this.error.set(null);

        this.api.getKnowledgeHealth().pipe(
            catchError((err) => {
                this.error.set(err.message || 'Failed to load knowledge health');
                return of(null);
            })
        ).subscribe(data => {
            this.health.set(data);
            this.loading.set(false);
        });

        this.api.getKnowledgeHealthDetailed().pipe(
            catchError(() => of(null))
        ).subscribe(data => {
            this.detailed.set(data);
        });
    }

    private startAutoRefresh(): void {
        this.refreshSub = interval(5000).pipe(
            switchMap(() => this.api.getKnowledgeHealth().pipe(catchError(() => of(null))))
        ).subscribe(data => {
            if (data) this.health.set(data);
        });
    }

    resetCircuitBreaker(): void {
        if (!confirm('Are you sure you want to reset the circuit breaker?')) return;

        this.resetting.set(true);
        this.api.resetKnowledgeCircuitBreaker().pipe(
            catchError((err) => {
                alert('Failed to reset circuit breaker: ' + err.message);
                return of(null);
            })
        ).subscribe(() => {
            this.resetting.set(false);
            this.loadData(); // Refresh data after reset
        });
    }

    toggleDetailed(): void {
        this.showDetailed.update(v => !v);
    }

    getOverallStatus(): string {
        const h = this.health();
        if (!h) return 'unknown';
        if (h.circuit_breaker_open) return 'degraded';
        if (!h.neo4j_connected || !h.qdrant_connected) return 'degraded';
        return h.status?.toLowerCase() || 'unknown';
    }

    getConnectionStatus(service: 'neo4j' | 'qdrant'): string {
        const h = this.health();
        if (!h) return 'unknown';
        return service === 'neo4j' ? (h.neo4j_connected ? 'connected' : 'disconnected')
            : (h.qdrant_connected ? 'connected' : 'disconnected');
    }
}
</file>

<file path="app/features/observability/widgets/system-status-widget/system-status-widget.html">
<div class="widget">
    @if (loading()) {
    <div class="loading-state">
        <div class="spinner"></div>
        <p>Loading system status...</p>
    </div>
    } @else if (error()) {
    <div class="error-state">
        <span class="material-icons">error_outline</span>
        <p>{{ error() }}</p>
    </div>
    } @else {
    <!-- Widget Header -->
    <div class="widget-header">
        <h3>System Status</h3>
        <span class="status-badge" [class]="'status-' + getStatusColor(systemStatus()?.status)">
            {{ systemStatus()?.status || 'UNKNOWN' }}
        </span>
    </div>

    <!-- System Info Grid -->
    <div class="info-grid">
        <div class="info-card">
            <span class="label">Version</span>
            <span class="value">{{ systemStatus()?.app_name }} v{{ systemStatus()?.version }}</span>
        </div>
        <div class="info-card">
            <span class="label">Environment</span>
            <span class="value env-badge">{{ systemStatus()?.environment }}</span>
        </div>
        <div class="info-card">
            <span class="label">Uptime</span>
            <span class="value">{{ formatUptime(systemStatus()?.uptime_seconds) }}</span>
        </div>
    </div>

    <!-- Services Health -->
    <div class="services-section">
        <h4>Services Health</h4>
        <div class="services-grid">
            @for (service of services(); track service.key) {
            <div class="service-card">
                <div class="service-indicator" [class]="'indicator-' + getStatusColor(service.status)"></div>
                <div class="service-info">
                    <span class="service-name">{{ service.name }}</span>
                    @if (service.metric_text) {
                    <span class="service-metric">{{ service.metric_text }}</span>
                    }
                </div>
            </div>
            }
            @if (services().length === 0) {
            <p class="no-data">No services data available</p>
            }
        </div>
    </div>
    }
</div>
</file>

<file path="app/features/observability/widgets/system-status-widget/system-status-widget.scss">
// Shared widget styles
.widget {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0.75rem;
    padding: 1.5rem;
    height: 100%;
    display: flex;
    flex-direction: column;
}

.widget-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.25rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);

    h3 {
        font-size: 1.25rem;
        font-weight: 600;
        color: #ffffff;
        margin: 0;
    }
}

// Status badges
.status-badge {
    padding: 0.375rem 0.75rem;
    border-radius: 0.375rem;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;

    &.status-green {
        background: rgba(34, 197, 94, 0.15);
        color: #4ade80;
        border: 1px solid rgba(34, 197, 94, 0.3);
    }

    &.status-yellow {
        background: rgba(251, 191, 36, 0.15);
        color: #fbbf24;
        border: 1px solid rgba(251, 191, 36, 0.3);
    }

    &.status-red {
        background: rgba(239, 68, 68, 0.15);
        color: #f87171;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }

    &.status-gray {
        background: rgba(156, 163, 175, 0.15);
        color: #9ca3af;
        border: 1px solid rgba(156, 163, 175, 0.3);
    }
}

// Info grid
.info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0.75rem;
    margin-bottom: 1.5rem;
}

.info-card {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    padding: 0.75rem;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 0.5rem;
    border: 1px solid rgba(255, 255, 255, 0.05);

    .label {
        font-size: 0.75rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .value {
        font-size: 1rem;
        font-weight: 600;
        color: #ffffff;
    }

    .env-badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        background: rgba(59, 130, 246, 0.15);
        border-radius: 0.25rem;
        font-size: 0.85rem;
        color: #60a5fa;
    }
}

// Services section
.services-section {
    h4 {
        font-size: 0.95rem;
        font-weight: 600;
        color: #e0e0e0;
        margin: 0 0 0.75rem 0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
}

.services-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 0.75rem;
}

.service-card {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    background: rgba(255, 255, 255, 0.03);
    border-radius: 0.5rem;
    border: 1px solid rgba(255, 255, 255, 0.05);

    .service-indicator {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        flex-shrink: 0;

        &.indicator-green {
            background: #4ade80;
            box-shadow: 0 0 8px rgba(74, 222, 128, 0.5);
        }

        &.indicator-yellow {
            background: #fbbf24;
            box-shadow: 0 0 8px rgba(251, 191, 36, 0.5);
        }

        &.indicator-red {
            background: #f87171;
            box-shadow: 0 0 8px rgba(248, 113, 113, 0.5);
        }

        &.indicator-gray {
            background: #9ca3af;
        }
    }

    .service-info {
        display: flex;
        flex-direction: column;
        gap: 0.125rem;

        .service-name {
            font-size: 0.9rem;
            font-weight: 500;
            color: #ffffff;
        }

        .service-metric {
            font-size: 0.75rem;
            color: #9ca3af;
        }
    }
}

// Loading/Error states
.loading-state,
.error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    min-height: 250px;
    color: #9ca3af;

    .spinner {
        border: 3px solid rgba(255, 255, 255, 0.1);
        border-top-color: #60a5fa;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1s linear infinite;
        margin-bottom: 1rem;
    }

    .material-icons {
        font-size: 3rem;
        color: #ef4444;
        margin-bottom: 0.5rem;
    }

    p {
        font-size: 0.9rem;
        margin: 0;
    }
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

.no-data {
    grid-column: 1 / -1;
    text-align: center;
    color: #6b7280;
    font-size: 0.85rem;
    padding: 1rem;
}
</file>

<file path="app/features/observability/widgets/system-status-widget/system-status-widget.ts">
import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { interval, Subscription } from 'rxjs';
import { switchMap, catchError } from 'rxjs/operators';
import { of } from 'rxjs';
import { BackendApiService, SystemStatus, ServiceHealthItem } from '../../../../services/backend-api.service';

@Component({
    selector: 'app-system-status-widget',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './system-status-widget.html',
    styleUrls: ['./system-status-widget.scss']
})
export class SystemStatusWidgetComponent implements OnInit, OnDestroy {
    private api = inject(BackendApiService);
    private refreshSub?: Subscription;

    systemStatus = signal<SystemStatus | null>(null);
    services = signal<ServiceHealthItem[]>([]);
    loading = signal(true);
    error = signal<string | null>(null);

    ngOnInit(): void {
        this.loadData();
        this.startAutoRefresh();
    }

    ngOnDestroy(): void {
        this.refreshSub?.unsubscribe();
    }

    private loadData(): void {
        this.loading.set(true);
        this.error.set(null);

        this.api.getSystemStatus().pipe(
            catchError(() => of(null))
        ).subscribe(status => {
            this.systemStatus.set(status);
            this.loading.set(false);
        });

        this.api.getServicesHealth().pipe(
            catchError(() => of({ services: [] }))
        ).subscribe(res => {
            this.services.set(res.services);
        });
    }

    private startAutoRefresh(): void {
        this.refreshSub = interval(5000).pipe(
            switchMap(() => {
                return this.api.getSystemStatus().pipe(catchError(() => of(null)));
            })
        ).subscribe(status => {
            if (status) this.systemStatus.set(status);
        });
    }

    formatUptime(seconds?: number): string {
        if (!seconds) return 'N/A';
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const mins = Math.floor((seconds % 3600) / 60);

        if (days > 0) return `${days}d ${hours}h ${mins}m`;
        if (hours > 0) return `${hours}h ${mins}m`;
        return `${mins}m ${Math.floor(seconds % 60)}s`;
    }

    getStatusColor(status?: string): string {
        if (!status) return 'gray';
        const s = status.toUpperCase();
        if (s === 'OPERATIONAL' || s === 'HEALTHY' || s === 'OK') return 'green';
        if (s === 'DEGRADED' || s === 'WARNING') return 'yellow';
        return 'red';
    }
}
</file>

<file path="app/features/observability/observability.html">
<div class="observability-container">
  <!-- Header with Title and Auto-Refresh Toggle -->
  <header class="obs-header">
    <div class="obs-title-section">
      <h1 class="obs-title">Observability Dashboard</h1>
      <p class="obs-subtitle">Real-time system monitoring and health checks</p>
    </div>

    <div class="obs-controls">
      <button class="auto-refresh-toggle" [class.active]="autoRefreshEnabled()" (click)="toggleAutoRefresh()"
        title="{{ autoRefreshEnabled() ? 'Auto-refresh: ON (5s)' : 'Auto-refresh: OFF' }}">
        <span class="material-icons">
          {{ autoRefreshEnabled() ? 'sync' : 'sync_disabled' }}
        </span>
        <span class="toggle-text">Auto-refresh</span>
      </button>
    </div>
  </header>

  <section class="operator-panel">
    <div class="operator-panel__header">
      <div>
        <p class="operator-panel__eyebrow">Modo Operador</p>
        <h2>Workers e filas críticas</h2>
      </div>
      <div class="operator-panel__meta">
        <span *ngIf="operatorLoading()">Atualizando...</span>
        <span *ngIf="!operatorLoading() && lastRefreshAt()">Ultima coleta: {{ lastRefreshAt() }}</span>
      </div>
    </div>

    <p class="operator-panel__error" *ngIf="operatorError()">{{ operatorError() }}</p>

    <div class="operator-grid">
      <article class="operator-card">
        <div class="operator-card__title">Workers</div>
        <div class="operator-list" *ngIf="workers().length; else emptyWorkers">
          <div class="operator-list__item" *ngFor="let worker of workers()">
            <div>
              <strong>{{ worker.name }}</strong>
              <p>{{ worker.state }}</p>
            </div>
            <span class="operator-badge" [class.is-running]="worker.running" [class.is-stopped]="!worker.running">
              {{ worker.running ? 'running' : worker.state }}
            </span>
          </div>
        </div>
      </article>

      <article class="operator-card">
        <div class="operator-card__title">Filas</div>
        <div class="operator-list" *ngIf="queues().length; else emptyQueues">
          <div class="operator-list__item" *ngFor="let queue of queues()">
            <div>
              <strong>{{ queue.name }}</strong>
              <p>{{ queue.consumers }} consumer(s)</p>
            </div>
            <span class="operator-badge" [class.is-alert]="queue.messages > 0 || queue.messages < 0">
              {{ queue.messages < 0 ? 'indisponivel' : (queue.messages + ' msg') }}
            </span>
          </div>
        </div>
      </article>
    </div>
  </section>

  <!-- Dashboard Grid -->
  <div class="obs-grid">
    <!-- System Status Widget (FE1-001) -->
    <app-system-status-widget />

    <!-- Database Health Widget (FE1-007) -->
    <app-database-health-widget />

    <!-- Knowledge Health Widget (FE1-008) -->
    <app-knowledge-health-widget />
  </div>
</div>

<ng-template #emptyWorkers>
  <p class="operator-card__empty">Nenhum worker rastreado no momento.</p>
</ng-template>

<ng-template #emptyQueues>
  <p class="operator-card__empty">Nenhuma fila monitorada no momento.</p>
</ng-template>
</file>

<file path="app/features/observability/observability.scss">
.observability-container {
  min-height: 100vh;
  padding: 2rem;
  background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 100%);
  color: #e0e0e0;
}

// Header Section
.obs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.obs-title-section {
  .obs-title {
    font-size: 2rem;
    font-weight: 700;
    color: #ffffff;
    margin: 0 0 0.5rem 0;
    letter-spacing: -0.5px;
  }

  .obs-subtitle {
    font-size: 0.95rem;
    color: #9ca3af;
    margin: 0;
  }
}

.obs-controls {
  display: flex;
  gap: 1rem;
}

.auto-refresh-toggle {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1.25rem;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 0.5rem;
  color: #9ca3af;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;

  .material-icons {
    font-size: 1.25rem;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    border-color: rgba(255, 255, 255, 0.2);
  }

  &.active {
    background: rgba(59, 130, 246, 0.15);
    border-color: rgba(59, 130, 246, 0.4);
    color: #60a5fa;

    .material-icons {
      animation: spin 2s linear infinite;
    }
  }
}

.operator-panel {
  margin-bottom: 1.5rem;
  padding: 1.25rem;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 1rem;
  background: linear-gradient(180deg, rgba(22, 28, 45, 0.9), rgba(10, 14, 24, 0.92));
}

.operator-panel__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;

  h2 {
    margin: 0.2rem 0 0;
    font-size: 1.2rem;
    color: #f8fafc;
  }
}

.operator-panel__eyebrow {
  margin: 0;
  font-size: 0.72rem;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #7dd3fc;
}

.operator-panel__meta {
  color: #94a3b8;
  font-size: 0.85rem;
}

.operator-panel__error {
  margin: 0 0 1rem;
  color: #fda4af;
}

.operator-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}

.operator-card {
  padding: 1rem;
  border-radius: 0.9rem;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.operator-card__title {
  margin-bottom: 0.85rem;
  font-size: 0.92rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #cbd5e1;
}

.operator-card__empty {
  margin: 0;
  color: #94a3b8;
}

.operator-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.operator-list__item {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;

  strong {
    display: block;
    color: #f8fafc;
  }

  p {
    margin: 0.2rem 0 0;
    color: #94a3b8;
    font-size: 0.85rem;
  }
}

.operator-badge {
  border-radius: 999px;
  padding: 0.25rem 0.65rem;
  font-size: 0.78rem;
  font-weight: 700;
  background: rgba(148, 163, 184, 0.16);
  color: #cbd5e1;
}

.operator-badge.is-running {
  background: rgba(34, 197, 94, 0.16);
  color: #86efac;
}

.operator-badge.is-stopped,
.operator-badge.is-alert {
  background: rgba(248, 113, 113, 0.16);
  color: #fca5a5;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

// Dashboard Grid
.obs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 1.5rem;
}

// Placeholder Styles (will be replaced by actual widgets)
.widget-placeholder {
  background: rgba(255, 255, 255, 0.03);
  border: 1px dashed rgba(255, 255, 255, 0.2);
  border-radius: 0.75rem;
  padding: 2rem;
  text-align: center;
  min-height: 300px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;

  h3 {
    font-size: 1.25rem;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 0.5rem;
  }

  p {
    color: #6b7280;
    font-size: 0.9rem;
  }
}

// Responsive Design
@media (max-width: 768px) {
  .observability-container {
    padding: 1rem;
  }

  .obs-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .obs-grid {
    grid-template-columns: 1fr;
  }

  .operator-panel__header,
  .operator-list__item {
    flex-direction: column;
    align-items: flex-start;
  }
}
</file>

<file path="app/features/observability/observability.ts">
import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription, catchError, forkJoin, interval, map, of, startWith } from 'rxjs';
import { SystemStatusWidgetComponent } from './widgets/system-status-widget/system-status-widget';
import { DatabaseHealthWidgetComponent } from './widgets/database-health-widget/database-health-widget';
import { KnowledgeHealthWidgetComponent } from './widgets/knowledge-health-widget/knowledge-health-widget';
import { AppLoggerService } from '../../core/services/app-logger.service';
import {
  BackendApiService,
  OrchestratorWorkerTaskStatus,
  QueueInfoResponse,
} from '../../services/backend-api.service';

@Component({
    selector: 'app-observability',
    standalone: true,
    imports: [CommonModule, SystemStatusWidgetComponent, DatabaseHealthWidgetComponent, KnowledgeHealthWidgetComponent],
    templateUrl: './observability.html',
    styleUrls: ['./observability.scss']
})
export class ObservabilityComponent implements OnInit, OnDestroy {
    autoRefreshEnabled = signal(true); // Default: ON per user requirement
    operatorLoading = signal(false);
    operatorError = signal<string | null>(null);
    workers = signal<OrchestratorWorkerTaskStatus[]>([]);
    queues = signal<QueueInfoResponse[]>([]);
    lastRefreshAt = signal<string | null>(null);
    private refreshSubscription?: Subscription;
    private readonly REFRESH_INTERVAL_MS = 5000; // 5 seconds
    private readonly logger = inject(AppLoggerService);
    private readonly api = inject(BackendApiService);
    private readonly queueNames = [
        'janus.tasks.router',
        'janus.agent.tasks',
        'janus.knowledge.consolidation',
        'janus.tasks.codex',
    ];

    ngOnInit(): void {
        this.startAutoRefresh();
    }

    ngOnDestroy(): void {
        this.stopAutoRefresh();
    }

    toggleAutoRefresh(): void {
        this.autoRefreshEnabled.update(enabled => !enabled);
        if (this.autoRefreshEnabled()) {
            this.startAutoRefresh();
        } else {
            this.stopAutoRefresh();
        }
    }

    private startAutoRefresh(): void {
        this.stopAutoRefresh();
        this.refreshSubscription = interval(this.REFRESH_INTERVAL_MS)
            .pipe(startWith(0))
            .subscribe(() => this.refreshOperatorView());
        this.logger.info('[Observability] Auto-refresh enabled', {
            intervalMs: this.REFRESH_INTERVAL_MS,
        });
    }

    private stopAutoRefresh(): void {
        this.refreshSubscription?.unsubscribe();
        this.refreshSubscription = undefined;
        this.logger.info('[Observability] Auto-refresh disabled');
    }

    private refreshOperatorView(): void {
        this.operatorLoading.set(true);
        this.operatorError.set(null);

        const queueRequests = this.queueNames.map((queueName) =>
            this.api.getQueueInfo(queueName).pipe(
                catchError(() =>
                    of({
                        name: queueName,
                        messages: -1,
                        consumers: 0,
                    } satisfies QueueInfoResponse)
                )
            )
        );

        forkJoin({
            workers: this.api.getWorkersStatus().pipe(map((response) => response.workers || [])),
            queues: queueRequests.length ? forkJoin(queueRequests) : of([] as QueueInfoResponse[]),
        })
            .pipe(
                catchError((error) => {
                    this.logger.error('[Observability] Failed to refresh operator view', error);
                    this.operatorError.set('Nao foi possivel atualizar a visao de operador.');
                    return of({
                        workers: [] as OrchestratorWorkerTaskStatus[],
                        queues: [] as QueueInfoResponse[],
                    });
                })
            )
            .subscribe((snapshot) => {
                this.workers.set(snapshot.workers);
                this.queues.set(snapshot.queues);
                this.operatorLoading.set(false);
                this.lastRefreshAt.set(new Date().toLocaleTimeString());
            });
    }
}
</file>

<file path="app/features/tools/tools.html">
<section class="tools-page">
  <app-header></app-header>

  <div class="tools-shell">
    <header class="tools-hero">
      <div>
        <p class="eyebrow">LLM & TOOLS</p>
        <h1>Visibilidade de Ferramentas</h1>
        <p class="sub">
          Monitoramento de execucao, eventos de auditoria e fila de aprovacoes humanas.
        </p>
      </div>
      <div class="hero-actions">
        @if (isAdmin()) {
          <ui-badge variant="info">Modo Admin</ui-badge>
        }
        <button ui-button variant="ghost" size="lg" (click)="refresh()" [disabled]="loading()">
          Atualizar
        </button>
        <a ui-button variant="default" size="lg" routerLink="/conversations">
          Nova conversa
        </a>
      </div>
    </header>

    @if (error()) {
      <div class="inline-alert" role="alert">
        <span class="material-icons">error_outline</span>
        {{ error() }}
      </div>
    }

    @if (success()) {
      <div class="inline-success" role="status">
        <span class="material-icons">check_circle</span>
        {{ success() }}
      </div>
    }

    <div class="tools-grid">
      <section class="tools-card col-4">
        <div class="card-head">
          <h3>Codex</h3>
          <ui-badge variant="neutral">{{ codexTools().length }}</ui-badge>
        </div>
        @if (loading()) {
          <app-skeleton variant="paragraph" [count]="3"></app-skeleton>
        } @else {
          <div class="metric-grid">
            <div>
              <span class="muted">Execucoes</span>
              <strong>{{ codexUsage().total }}</strong>
            </div>
            <div>
              <span class="muted">Sucesso</span>
              <strong>{{ codexUsage().successRate }}%</strong>
            </div>
            <div>
              <span class="muted">Latencia media</span>
              <strong>{{ codexUsage().avgDuration }}ms</strong>
            </div>
          </div>
          <div class="chip-row">
            @for (tool of codexTools(); track tool.name) {
              <span class="chip subtle">{{ tool.name }}</span>
            }
          </div>
        }
      </section>

      <section class="tools-card col-4">
        <div class="card-head">
          <h3>Centro de aprovacoes</h3>
          <ui-badge [variant]="pendingCount() ? 'warning' : 'success'">{{ pendingCount() }}</ui-badge>
        </div>
        @if (loading()) {
          <app-skeleton variant="text" [count]="2"></app-skeleton>
        } @else if (pendingCount()) {
          <div class="pending-summary">
            <span class="chip danger">Alto: {{ pendingRiskSummary().high }}</span>
            <span class="chip warn">Medio: {{ pendingRiskSummary().medium }}</span>
            <span class="chip ok">Baixo: {{ pendingRiskSummary().low }}</span>
          </div>
          <div class="pending-filters">
            <div class="filter-row">
              <button ui-button size="sm" [variant]="riskFilter() === 'all' ? 'default' : 'ghost'" (click)="setRiskFilter('all')">Risco: todos</button>
              <button ui-button size="sm" [variant]="riskFilter() === 'high' ? 'default' : 'ghost'" (click)="setRiskFilter('high')">Alto</button>
              <button ui-button size="sm" [variant]="riskFilter() === 'medium' ? 'default' : 'ghost'" (click)="setRiskFilter('medium')">Medio</button>
              <button ui-button size="sm" [variant]="riskFilter() === 'low' ? 'default' : 'ghost'" (click)="setRiskFilter('low')">Baixo</button>
            </div>
            <div class="filter-row">
              <button ui-button size="sm" [variant]="sourceFilter() === 'all' ? 'default' : 'ghost'" (click)="setSourceFilter('all')">Origem: todas</button>
              <button ui-button size="sm" [variant]="sourceFilter() === 'sql' ? 'default' : 'ghost'" (click)="setSourceFilter('sql')">SQL</button>
              <button ui-button size="sm" [variant]="sourceFilter() === 'langgraph' ? 'default' : 'ghost'" (click)="setSourceFilter('langgraph')">LangGraph</button>
            </div>
            <input
              class="pending-search"
              type="text"
              placeholder="Filtrar por tool, usuario, args, id..."
              [value]="queryFilter()"
              (input)="setQueryFilter($any($event.target).value)"
            />
            @if (hasPendingFilters()) {
              <button ui-button size="sm" variant="ghost" (click)="clearPendingFilters()">
                Limpar filtros
              </button>
            }
          </div>

          <ul class="list">
            @for (action of pendingActionsFiltered(); track (action.action_id || action.thread_id || action.message)) {
              <li class="list-item">
                <div>
                  <span class="item-title">
                    {{ action.action_id ? ('#' + action.action_id + ' (SQL)') : action.thread_id }}
                    <ui-badge variant="neutral">{{ sourceLabel(action) }}</ui-badge>
                  </span>
                  <span class="muted">{{ action.message || 'Aguardando decisao' }}</span>
                  @if (action.tool_name || action.user_id) {
                    <p class="muted meta-inline">Tool: {{ action.tool_name || 'n/d' }} · User: {{ action.user_id || 'n/d' }}</p>
                  }
                  <div class="risk-row">
                    <ui-badge [variant]="riskVariant(action)">{{ riskLabel(action) }}</ui-badge>
                    <span class="muted">{{ action.risk_summary || 'Sem resumo de risco.' }}</span>
                  </div>
                  @if (argsPreview(action)) {
                    <pre class="args-preview">{{ argsPreview(action) }}</pre>
                  }
                </div>
                <div class="action-row">
                  <button ui-button variant="ghost" size="sm" (click)="reject(action)" [disabled]="actionLoading()">
                    Rejeitar
                  </button>
                  <button ui-button variant="default" size="sm" (click)="approve(action)" [disabled]="actionLoading()">
                    Aprovar
                  </button>
                </div>
              </li>
            }
          </ul>
          @if (!pendingActionsFiltered().length) {
            <p class="muted">Nenhuma aprovacao corresponde aos filtros atuais.</p>
          }
        } @else {
          <p class="muted">Nenhuma aprovacao pendente.</p>
        }
      </section>

      <section class="tools-card col-4">
        <div class="card-head">
          <h3>Ferramentas registradas</h3>
          <ui-badge variant="neutral">{{ data().tools.length }}</ui-badge>
        </div>
        @if (loading()) {
          <app-skeleton variant="paragraph" [count]="3"></app-skeleton>
        } @else {
          <p class="muted">
            Total de chamadas: {{ data().toolStats?.total_calls || 0 }} ·
            Sucesso: {{ (data().toolStats?.success_rate ?? 0) * 100 }}%
          </p>
          <div class="chip-row">
            @for (tool of data().tools.slice(0, 8); track tool.name) {
              <span class="chip">{{ tool.name }}</span>
            }
          </div>
        }
      </section>

      <section class="tools-card col-12" id="audit-events">
        <div class="card-head">
          <h3>Eventos Codex (auditoria)</h3>
          <ui-badge variant="neutral">{{ codexEvents().length }}</ui-badge>
        </div>
        @if (loading()) {
          <app-skeleton variant="text" [count]="4"></app-skeleton>
        } @else if (codexEvents().length) {
          <ui-table [striped]="true">
            <thead>
              <tr>
                <th>Tool</th>
                <th>Status</th>
                <th>Latencia</th>
                <th>Quando</th>
              </tr>
            </thead>
            <tbody>
              @for (event of codexEvents(); track event.id) {
                <tr>
                  <td>{{ event.tool }}</td>
                  <td>{{ event.status || 'ok' }}</td>
                  <td>{{ event.latency_ms || 0 }}ms</td>
                  <td>{{ formatAuditTimestamp(event.created_at) }}</td>
                </tr>
              }
            </tbody>
          </ui-table>
        } @else {
          <p class="muted">Nenhum evento codex registrado.</p>
        }
      </section>

      <section class="tools-card col-12">
        <div class="card-head">
          <h3>Catalogo de ferramentas</h3>
        </div>
        @if (loading()) {
          <app-skeleton variant="text" [count]="4"></app-skeleton>
        } @else if (data().tools.length) {
          <ui-table [striped]="true">
            <thead>
              <tr>
                <th>Nome</th>
                <th>Categoria</th>
                <th>Permissao</th>
                <th>Tags</th>
              </tr>
            </thead>
            <tbody>
              @for (tool of data().tools; track tool.name) {
                <tr>
                  <td>{{ tool.name }}</td>
                  <td>{{ tool.category || 'geral' }}</td>
                  <td>{{ tool.permission_level || '—' }}</td>
                  <td>{{ formatToolTags(tool.tags) }}</td>
                </tr>
              }
            </tbody>
          </ui-table>
        } @else {
          <p class="muted">Nenhuma ferramenta registrada.</p>
        }
      </section>
    </div>
  </div>
</section>
</file>

<file path="app/features/tools/tools.scss">
@use 'styles/tokens' as *;
@use 'styles/mixins' as *;

.tools-page {
  position: relative;
  min-height: calc(100vh - 64px);
  padding-bottom: 80px;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.tools-shell {
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 32px;
  padding: clamp(24px, 4vw, 48px) clamp(16px, 4vw, 40px) 0;
}

.tools-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  flex-wrap: wrap;
}

.eyebrow {
  font-family: $font-mono;
  font-size: 0.7rem;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: $color-text-muted;
}

.sub {
  color: $color-text-secondary;
  font-size: 1rem;
}

.hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.tools-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 24px;
}

.tools-card {
  @include glass-panel;
  border-radius: var(--janus-radius-lg);
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: relative;
  overflow: hidden;
}

.tools-card::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at top right, rgba(var(--janus-secondary-rgb), 0.12), transparent 55%);
  pointer-events: none;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.col-12 {
  grid-column: span 12;
}

.col-4 {
  grid-column: span 4;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;

  strong {
    display: block;
    font-family: $font-display;
    font-size: 1.05rem;
    color: $color-text-primary;
  }
}

.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  border: 1px solid rgba(var(--janus-secondary-rgb), 0.3);
  background: rgba(255, 255, 255, 0.02);
  color: $color-text-secondary;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-family: $font-mono;
}

.chip.subtle {
  border-color: rgba(255, 255, 255, 0.08);
  color: $color-text-muted;
}

.chip.danger {
  border-color: rgba(var(--error-rgb), 0.55);
  color: rgba(var(--error-rgb), 1);
}

.chip.warn {
  border-color: rgba(var(--warning-rgb), 0.55);
  color: rgba(var(--warning-rgb), 1);
}

.chip.ok {
  border-color: rgba(var(--success-rgb), 0.55);
  color: rgba(var(--success-rgb), 1);
}

.list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  list-style: none;
  padding: 0;
  margin: 0;
}

.list-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: $radius-md;
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.item-title {
  font-family: $font-display;
  font-size: 0.95rem;
  color: $color-text-primary;
  display: block;
}

.muted {
  color: $color-text-muted;
  font-size: 0.8rem;
}

.action-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.risk-row {
  margin-top: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.pending-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pending-filters {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pending-search {
  width: 100%;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(var(--janus-bg-dark-rgb), 0.28);
  color: $color-text-primary;
  padding: 8px 10px;
  font-size: 0.82rem;
}

.meta-inline {
  margin-top: 6px;
  margin-bottom: 0;
}

.args-preview {
  margin-top: 8px;
  margin-bottom: 0;
  padding: 8px;
  border-radius: 8px;
  background: rgba(var(--janus-bg-dark-rgb), 0.35);
  border: 1px solid rgba(255, 255, 255, 0.08);
  color: $color-text-secondary;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.74rem;
}

.inline-alert {
  display: flex;
  align-items: center;
  gap: 10px;
  border-radius: $radius-md;
  padding: 12px 16px;
  font-size: 0.9rem;
  background: rgba(var(--error-rgb), 0.16);
  border: 1px solid rgba(var(--error-rgb), 0.4);
}

.inline-success {
  display: flex;
  align-items: center;
  gap: 10px;
  border-radius: $radius-md;
  padding: 12px 16px;
  font-size: 0.9rem;
  background: rgba(var(--success-rgb), 0.16);
  border: 1px solid rgba(var(--success-rgb), 0.35);
}

@media (max-width: 1100px) {
  .col-4 {
    grid-column: span 12;
  }
}
</file>

<file path="app/features/tools/tools.ts">
import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core'
import { CommonModule } from '@angular/common'
import { RouterLink } from '@angular/router'
import { forkJoin, of } from 'rxjs'
import { catchError, map } from 'rxjs/operators'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'

import {
  AuditEvent,
  BackendApiService,
  PendingAction,
  Tool,
  ToolStats
} from '../../services/backend-api.service'
import { UiBadgeComponent } from '../../shared/components/ui/ui-badge/ui-badge.component'
import { UiButtonComponent } from '../../shared/components/ui/button/button.component'
import { UiTableComponent } from '../../shared/components/ui/ui-table/ui-table.component'
import { Header } from '../../core/layout/header/header'
import { AuthService } from '../../core/auth/auth.service'
import { SkeletonComponent } from '../../shared/components/skeleton/skeleton.component'

interface ToolsData {
  tools: Tool[]
  toolStats: ToolStats | null
  auditEvents: AuditEvent[]
  pendingActions: PendingAction[]
}

@Component({
  selector: 'app-tools',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    UiBadgeComponent,
    UiButtonComponent,
    UiTableComponent,
    Header,
    SkeletonComponent
  ],
  templateUrl: './tools.html',
  styleUrls: ['./tools.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ToolsComponent {
  private api = inject(BackendApiService)
  private auth = inject(AuthService)
  private destroyRef = inject(DestroyRef)

  readonly loading = signal(true)
  readonly actionLoading = signal(false)
  readonly error = signal('')
  readonly success = signal('')
  readonly riskFilter = signal<'all' | 'high' | 'medium' | 'low'>('all')
  readonly sourceFilter = signal<'all' | 'sql' | 'langgraph'>('all')
  readonly queryFilter = signal('')
  readonly isAdmin = this.auth.isAdmin
  readonly data = signal<ToolsData>({
    tools: [],
    toolStats: null,
    auditEvents: [],
    pendingActions: []
  })

  readonly codexTools = computed(() => this.data().tools.filter((tool) => tool.name?.startsWith('codex_')))
  readonly codexEvents = computed(() => {
    const events = this.data().auditEvents || []
    return events.filter((ev) => String(ev.tool || '').startsWith('codex_')).slice(0, 12)
  })
  readonly codexUsage = computed(() => {
    const usage = this.data().toolStats?.tool_usage || {}
    const entries = Object.entries(usage).filter(([name]) => name.startsWith('codex_'))
    const total = entries.reduce((sum, [, stats]) => sum + (stats?.total || 0), 0)
    const success = entries.reduce((sum, [, stats]) => sum + (stats?.success || 0), 0)
    const avgDuration = entries.length
      ? Math.round(entries.reduce((sum, [, stats]) => sum + (stats?.avg_duration || 0), 0) / entries.length * 1000)
      : 0
    const successRate = total > 0 ? Math.round((success / total) * 100) : 0
    return { total, success, successRate, avgDuration }
  })
  readonly pendingCount = computed(() => this.data().pendingActions.length)
  readonly pendingRiskSummary = computed(() => {
    const actions = this.data().pendingActions || []
    let high = 0
    let medium = 0
    let low = 0
    for (const action of actions) {
      const risk = String(action.risk_level || '').toLowerCase()
      if (risk === 'high') high += 1
      else if (risk === 'medium') medium += 1
      else low += 1
    }
    return { total: actions.length, high, medium, low }
  })
  readonly hasPendingFilters = computed(
    () => this.riskFilter() !== 'all' || this.sourceFilter() !== 'all' || !!this.queryFilter().trim()
  )
  readonly pendingActionsFiltered = computed(() => {
    const riskFilter = this.riskFilter()
    const sourceFilter = this.sourceFilter()
    const query = this.queryFilter().trim().toLowerCase()

    const riskRank = (action: PendingAction): number => {
      const risk = String(action.risk_level || '').toLowerCase()
      if (risk === 'high') return 3
      if (risk === 'medium') return 2
      if (risk === 'low') return 1
      return 0
    }
    const actionTime = (action: PendingAction): number => {
      const raw = String(action.created_at || '').trim()
      const ts = raw ? Date.parse(raw) : 0
      return Number.isFinite(ts) ? ts : 0
    }

    const filtered = (this.data().pendingActions || []).filter((action) => {
      const risk = String(action.risk_level || '').toLowerCase()
      const source = String(action.source || '').toLowerCase()
      if (riskFilter !== 'all' && risk !== riskFilter) return false
      if (sourceFilter !== 'all' && source !== sourceFilter) return false
      if (!query) return true

      const haystack = [
        action.tool_name,
        action.user_id,
        action.message,
        action.args_json,
        action.thread_id,
        typeof action.action_id === 'number' ? String(action.action_id) : ''
      ]
        .map((value) => String(value || '').toLowerCase())
        .join(' ')

      return haystack.includes(query)
    })

    return filtered.sort((a, b) => {
      const riskDiff = riskRank(b) - riskRank(a)
      if (riskDiff !== 0) return riskDiff
      return actionTime(b) - actionTime(a)
    })
  })

  constructor() {
    this.refresh()
  }

  refresh() {
    this.loading.set(true)
    this.error.set('')

    const tools$ = this.api.getTools()
      .pipe(
        map((resp) => resp.tools || []),
        catchError(() => of([]))
      )
    const toolStats$ = this.api.getToolStats()
      .pipe(catchError(() => of(null)))
    const auditEvents$ = this.api.listAuditEvents({ limit: 100 })
      .pipe(
        map((resp) => resp.events || []),
        catchError(() => of([]))
      )
    const pendingActions$ = this.api.listPendingActions({ include_sql: true, include_graph: false })
      .pipe(catchError(() => of([])))

    forkJoin({
      tools: tools$,
      toolStats: toolStats$,
      auditEvents: auditEvents$,
      pendingActions: pendingActions$
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.data.set(result)
          this.loading.set(false)
        },
        error: (err) => {
          this.error.set(this.extractApiErrorMessage(err, 'Falha ao carregar dados de ferramentas.'))
          this.loading.set(false)
        }
      })
  }

  setRiskFilter(value: 'all' | 'high' | 'medium' | 'low') {
    this.riskFilter.set(value)
  }

  setSourceFilter(value: 'all' | 'sql' | 'langgraph') {
    this.sourceFilter.set(value)
  }

  setQueryFilter(value: string) {
    this.queryFilter.set(String(value || ''))
  }

  clearPendingFilters() {
    this.riskFilter.set('all')
    this.sourceFilter.set('all')
    this.queryFilter.set('')
  }

  approve(action: PendingAction) {
    if (!action || this.actionLoading()) return
    this.actionLoading.set(true)
    this.api.approvePendingAction(action)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((err) => {
          this.error.set(this.extractApiErrorMessage(err, 'Falha ao aprovar a acao.'))
          this.actionLoading.set(false)
          return of(null)
        })
      )
      .subscribe((resp) => {
        if (resp) {
          this.success.set('Acao aprovada com sucesso. Veja a trilha de auditoria abaixo.')
        }
        this.actionLoading.set(false)
        this.refresh()
      })
  }

  reject(action: PendingAction) {
    if (!action || this.actionLoading()) return
    this.actionLoading.set(true)
    this.api.rejectPendingAction(action)
      .pipe(
        takeUntilDestroyed(this.destroyRef),
        catchError((err) => {
          this.error.set(this.extractApiErrorMessage(err, 'Falha ao rejeitar a acao.'))
          this.actionLoading.set(false)
          return of(null)
        })
      )
      .subscribe((resp) => {
        if (resp) {
          this.success.set('Acao rejeitada com sucesso. Veja a trilha de auditoria abaixo.')
        }
        this.actionLoading.set(false)
        this.refresh()
      })
  }

  formatAuditTimestamp(ts?: number | null): string {
    if (!ts) return 'n/d'
    return new Date(ts * 1000).toLocaleString()
  }

  formatToolTags(tags?: string[]) {
    if (!tags || !tags.length) return '—'
    return tags.join(', ')
  }

  riskVariant(action: PendingAction): 'error' | 'warning' | 'success' | 'neutral' {
    const level = String(action.risk_level || '').toLowerCase()
    if (level === 'high') return 'error'
    if (level === 'medium') return 'warning'
    if (level === 'low') return 'success'
    return 'neutral'
  }

  riskLabel(action: PendingAction): string {
    const level = String(action.risk_level || '').toLowerCase()
    if (level === 'high') return 'Risco alto'
    if (level === 'medium') return 'Risco medio'
    if (level === 'low') return 'Risco baixo'
    return 'Risco n/d'
  }

  argsPreview(action: PendingAction): string {
    const raw = String(action.args_json || '').trim()
    if (!raw) return ''
    if (raw.length <= 180) return raw
    return `${raw.slice(0, 177)}...`
  }

  sourceLabel(action: PendingAction): string {
    const source = String(action.source || '').toLowerCase()
    if (source === 'sql') return 'SQL'
    if (source === 'langgraph') return 'LangGraph'
    return 'Origem n/d'
  }

  private extractApiErrorMessage(err: unknown, fallback: string): string {
    const body = (err as any)?.error
    const detail = body?.detail ? String(body.detail) : ''
    const code = body?.error_code ? String(body.error_code) : ''
    if (code && detail) return `${fallback} [${code}] ${detail}`
    if (code) return `${fallback} [${code}]`
    if (detail) return `${fallback} ${detail}`
    return fallback
  }
}
</file>

<file path="app/models/autonomy.models.ts">
import { Citation } from './chat.models';

// Meta-Agent
export interface MetaAgentRecommendation {
  id: string;
  category?: string;
  title: string;
  description?: string;
  rationale?: string;
  estimated_impact?: string;
  priority?: number;
  suggested_agent?: string | null;
  created_at?: string;
}

export interface MetaAgentExecutionResult {
  title?: string;
  status?: string;
  [key: string]: unknown;
}

export interface MetaAgentReport {
  cycle_id: string;
  timestamp: string;
  overall_status: string;
  health_score: number;
  issues_detected: Record<string, unknown>[];
  recommendations: MetaAgentRecommendation[];
  summary: string;
  metrics_snapshot: Record<string, unknown>;
  execution_results?: MetaAgentExecutionResult[];
}

export interface MetaAgentLatestReportResponse {
  message: string;
  report: MetaAgentReport | null;
}

export interface MetaAgentHeartbeatStatus {
  heartbeat_active: boolean;
  total_cycles_executed: number;
  last_analysis?: string | null;
}

// Goals
export interface Goal {
  id: string
  title: string
  description: string
  priority: number
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  success_criteria?: string
  deadline_ts?: number
  created_at: number
  updated_at: number
}

export interface GoalCreateRequest {
  title: string
  description: string
  priority?: number
  success_criteria?: string
  deadline_ts?: number
}

// Autonomy
export interface AutonomyStartRequest {
  interval_seconds?: number
  user_id?: string
  project_id?: string
  risk_profile?: 'conservative' | 'balanced' | 'aggressive'
  auto_confirm?: boolean
  allowlist?: string[]
  blocklist?: string[]
  max_actions_per_cycle?: number
  max_seconds_per_cycle?: number
  plan?: { tool: string; args: Record<string, unknown> }[]
}

export interface AutonomyConfig {
  risk_profile?: string;
  interval_seconds?: number;
  max_actions_per_cycle?: number;
  [key: string]: unknown;
}

export interface AutonomyStatusResponse {
  active: boolean
  cycle_count: number
  last_cycle_at?: number | null
  config: AutonomyConfig
}

export interface AutonomyPlanResponse {
  status: string
  active: boolean
  steps_count: number
  plan: { tool: string; args: Record<string, unknown> }[]
}

export interface AutonomyPolicyUpdateRequest {
  risk_profile?: string
  auto_confirm?: boolean
  allowlist?: string[]
  blocklist?: string[]
  max_actions_per_cycle?: number
  max_seconds_per_cycle?: number
}

export interface AdminBacklogSyncResponse {
  created: number
  deduped: number
  capped: number
  closed: number
  fallback_used_count: number
  findings_total: number
}

export interface AdminBacklogTask {
  id: string
  title: string
  description: string
  status: string
  priority: number
  source_kind?: string | null
  source_fingerprint?: string | null
  area?: string | null
  severity?: string | null
  auto_created?: boolean
  created_at?: string | null
  updated_at?: string | null
}

export interface AdminBacklogSprint {
  id: string
  name: string
  status: string
  start_ts?: number | null
  end_ts?: number | null
  tasks: AdminBacklogTask[]
}

export interface AdminBacklogSprintType {
  sprint_type: { id: string; name: string; slug: string }
  sprints: AdminBacklogSprint[]
}

export interface SelfStudyRunFile {
  id: number
  file_path: string
  change_type?: string | null
  sha_before?: string | null
  sha_after?: string | null
  summary_status: string
  error?: string | null
}

export interface SelfStudyRun {
  id: number
  trigger_type: string
  mode: 'incremental' | 'full' | string
  status: string
  files_total: number
  files_processed: number
  error?: string | null
  base_commit?: string | null
  target_commit?: string | null
  created_at?: string | null
  finished_at?: string | null
  files?: SelfStudyRunFile[]
}

export interface SelfStudyStatusResponse {
  last_studied_commit?: string | null
  last_success_at?: string | null
  running?: {
    id: number
    status: string
    mode: string
    created_at?: string | null
    files_total?: number
    files_processed?: number
    current_file_path?: string | null
    current_file_index?: number | null
  } | null
  recent_runs: SelfStudyRun[]
}

export interface AdminCodeQaResponse {
  answer: string
  citations: Citation[]
  self_memory: Array<{ file_path?: string; summary?: string; updated_at?: string | number }>
}
</file>

<file path="app/models/chat.models.ts">
export interface ChatStartResponse {
  conversation_id: string
  created_at?: number
  updated_at?: number
}
export interface ChatStartRequest {
  persona?: string;
  user_id?: string;
  project_id?: string;
  title?: string;
}

export interface ChatMessageRequest {
  conversation_id: string;
  message: string;
  role?: string;
  priority?: string;
  timeout_seconds?: number;
  user_id?: string;
  project_id?: string;
  knowledge_space_id?: string;
}
export interface CitationStatus {
  mode: 'required' | 'optional' | string;
  status: 'present' | 'missing_required' | 'not_applicable' | 'retrieval_failed' | string;
  count: number;
  reason?: string | null;
}
export interface ChatRoutingState {
  requested_role?: string;
  selected_role?: string;
  route_applied?: boolean;
  intent?: string;
  risk_level?: string;
  confidence?: number;
  [key: string]: unknown;
}
export interface ChatRiskState {
  level?: 'low' | 'medium' | 'high' | string;
  source?: string;
  summary?: string;
  requires_confirmation?: boolean;
  [key: string]: unknown;
}
export interface ChatConfirmationState {
  required: boolean;
  status?: string;
  reason?: string | null;
  source?: string;
  pending_action_id?: number | null;
  approve_endpoint?: string | null;
  reject_endpoint?: string | null;
  [key: string]: unknown;
}
export interface ChatAgentState {
  state: 'thinking' | 'using_tool' | 'waiting_confirmation' | 'low_confidence' | 'streaming_response' | 'completed' | 'error' | string;
  confidence_band?: 'high' | 'medium' | 'low' | string;
  requires_confirmation?: boolean;
  reason?: string;
  [key: string]: unknown;
}
export interface ChatUnderstanding {
  intent: string;
  summary: string;
  confidence?: number;
  confidence_band?: 'high' | 'medium' | 'low' | string;
  low_confidence?: boolean;
  requires_confirmation?: boolean;
  confirmation_reason?: string | null;
  signals?: string[];
  routing?: ChatRoutingState;
  risk?: ChatRiskState;
  confirmation?: ChatConfirmationState;
  [key: string]: unknown;
}
export interface ChatMessage {
  message_id?: string;
  role: string;
  text: string;
  timestamp: number;
  knowledge_space_id?: string;
  mode_used?: string;
  base_used?: string;
  estimated_wait_seconds?: number;
  estimated_wait_range_seconds?: number[];
  processing_profile?: string;
  processing_notice?: string | null;
  source_scope?: Record<string, unknown> | null;
  gaps_or_conflicts?: string[];
  citations?: Citation[]
  citation_status?: CitationStatus;
  reasoning?: string;
  ui?: { type: string; data: any };
  understanding?: ChatUnderstanding;
  confirmation?: ChatConfirmationState;
  agent_state?: ChatAgentState;
  delivery_status?: string;
  failure_classification?: string;
  provider?: string;
  model?: string;
}

export interface ChatStudyJobRef {
  job_id: string;
  status: string;
  poll_url: string;
  conversation_id: string;
  message_id?: string;
  placeholder_message?: string;
}

export interface ChatStudyJobResponse {
  job_id: string;
  status: string;
  progress: number;
  conversation_id: string;
  message_id?: string;
  placeholder_message?: string;
  failure_classification?: string;
  final_response?: ChatMessageResponse;
  error?: string;
  updated_at?: number;
}

export interface ChatMessageResponse {
  response: string;
  provider: string;
  model: string;
  role: string;
  conversation_id: string;
  message_id?: string;
  knowledge_space_id?: string;
  mode_used?: string;
  base_used?: string;
  estimated_wait_seconds?: number;
  estimated_wait_range_seconds?: number[];
  processing_profile?: string;
  processing_notice?: string | null;
  source_scope?: Record<string, unknown> | null;
  gaps_or_conflicts?: string[];
  citations: Citation[];
  citation_status?: CitationStatus;
  ui?: { type: string; data: any };
  understanding?: ChatUnderstanding;
  confirmation?: ChatConfirmationState;
  agent_state?: ChatAgentState;
  delivery_status?: string;
  study_job?: ChatStudyJobRef;
  study_notice?: string;
  failure_classification?: string;
}
export interface ChatHistoryResponse { conversation_id: string; messages: ChatMessage[] }
export interface ChatListItem {
  conversation_id: string;
  title?: string;
  created_at?: number;
  updated_at?: number;
  last_message?: ChatMessage;
}

export interface ChatHistoryPaginatedResponse {
  conversation_id: string;
  persona?: string;
  messages: ChatMessage[];
  total_count: number;
  has_more: boolean;
  next_offset?: number;
  limit: number;
  offset: number;
}
export interface Citation {
  id?: string;
  title?: string;
  url?: string;
  snippet?: string;
  score?: number;
  source_type?: string;
  doc_id?: string;
  file_path?: string;
  origin?: string;
  type?: string;
  line?: number | string;
  line_start?: number | string;
  line_end?: number | string;
}

export interface RagUserChatResponse {
  answer: string;
  citations: Citation[];
}

export interface RagUserChatV2Result {
  id?: string;
  score?: number;
  role?: string;
  session_id?: string;
  timestamp?: number;
  [key: string]: unknown;
}

export interface RagUserChatV2Response {
  results: RagUserChatV2Result[];
}

export interface TraceStep {
  stepId: string;
  timestamp: number;
  agent: string;
  type: string;
  content: any;
  metadata?: {
    task_id?: string;
    trace_id?: string;
    model?: string;
  };
}
</file>

<file path="app/models/core.models.ts">
import { ReflexionLesson } from './observability.models';
import { ChatMessage } from './chat.models';

export interface ConversationMeta {
  conversation_id: string;
  title?: string;
  last_message_at?: string;
  created_at?: number;
  updated_at?: number;
  last_message?: ChatMessage
  message_count?: number
  tags?: string[]
}
export interface ConversationsListResponse { conversations: ConversationMeta[] }
export interface PostSprintSummaryResponse {
  lessons: ReflexionLesson[]
  meta_report?: Record<string, unknown>
}
</file>

<file path="app/models/index.ts">
export * from './system.models';
export * from './chat.models';
export * from './knowledge.models';
export * from './autonomy.models';
export * from './observability.models';
export * from './tools.models';
export * from './llm.models';
export * from './memory.models';
export * from './productivity.models';
export * from './core.models';
</file>

<file path="app/models/knowledge.models.ts">
import { Citation } from './chat.models';

// Knowledge Health
export interface KnowledgeHealthResponse {
  status: string;
  neo4j_connected: boolean;
  qdrant_connected: boolean;
  circuit_breaker_open: boolean;
  total_nodes: number;
  total_relationships: number;
}

export interface KnowledgeHealthDetailedResponse {
  timestamp: string;
  overall_status: string;
  basic_health: KnowledgeHealthResponse;
  detailed_status: {
    offline: boolean;
    circuit_breaker_open: boolean;
    metrics: Record<string, unknown>;
  };
  monitoring: Record<string, unknown> | null;
  recommendations: string[];
}

export interface ContextInfo { [key: string]: unknown }
export interface WebSearchResult { [key: string]: unknown }
export interface WebCacheStatus { [key: string]: unknown }

// Documents / RAG
export interface UploadResponse { doc_id: string; chunks: number; status: string; consolidation?: Record<string, unknown> | null }
export interface DocListItem { doc_id: string; file_name?: string; chunks: number; conversation_id?: string; last_index_ts?: number }
export interface DocListResponse { items: DocListItem[] }
export interface DocSearchResultItem {
  id: string;
  score: number;
  doc_id: string;
  file_name?: string;
  index?: number;
  timestamp?: number;
  [key: string]: unknown;
}

export interface DocSearchResponse {
  results: DocSearchResultItem[];
}

export interface KnowledgeSpace {
  knowledge_space_id: string;
  user_id: string;
  name: string;
  source_type: string;
  source_id?: string | null;
  edition_or_version?: string | null;
  language?: string | null;
  parent_collection_id?: string | null;
  description?: string | null;
  consolidation_status: string;
  consolidation_summary?: string | null;
  last_consolidated_at?: string | null;
}

export interface KnowledgeSpaceStatus extends KnowledgeSpace {
  documents_total: number;
  documents_indexed: number;
  documents_processing: number;
  documents_queued: number;
  documents_failed: number;
  chunks_total: number;
  chunks_indexed: number;
  progress: number;
}

export interface KnowledgeSpaceCreateRequest {
  name: string;
  user_id?: string;
  source_type?: string;
  source_id?: string;
  edition_or_version?: string;
  language?: string;
  parent_collection_id?: string;
  description?: string;
}

export interface KnowledgeSpaceListResponse {
  items: KnowledgeSpace[];
}

export interface KnowledgeSpaceAttachRequest {
  user_id?: string;
  source_type?: string;
  source_id?: string;
  edition_or_version?: string;
  language?: string;
  parent_collection_id?: string;
}

export interface KnowledgeSpaceConsolidationResponse {
  message: string;
  stats: {
    status: string;
    task_id?: string;
    status_url?: string;
    [key: string]: unknown;
  };
}

export interface KnowledgeSpaceQueryResponse {
  answer: string;
  mode_used: string;
  base_used: string;
  source_scope: Record<string, unknown>;
  citations: Citation[];
  confidence: number;
  gaps_or_conflicts: string[];
}

export interface RagSearchResponse {
  answer: string;
  citations: Citation[];
}

export interface RagHybridResponse {
  answer: string;
  citations: Citation[];
}

// Knowledge Graph
export interface KnowledgeStats {
  total_nodes: number
  total_relationships: number
  labels: Record<string, number>
}

export interface EntityRelationshipItem {
  related_entity: string
  related_type: string
  relationship: string
  distance: number
}

export interface EntityRelationshipsResponse {
  results: EntityRelationshipItem[]
}

export interface GraphNode {
  data: {
    id: string;
    label: string;
    type?: string;
    color?: string;
  };
}

export interface GraphEdge {
  data: {
    source: string;
    target: string;
    label: string;
  };
}

export interface ContextualGraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}
</file>

<file path="app/models/llm.models.ts">
// LLM providers
export interface LLMProviderMeta { priority?: number; enabled?: boolean; models?: string[]; type?: string }
export type LLMProvidersResponse = Record<string, LLMProviderMeta>;

// LLM health
export interface LLMSubsystemHealth {
  status: string;
  providers?: Record<string, { status: string; latency_ms?: number; error?: string | null }>;
}

export interface LLMCacheEntry { [key: string]: unknown }
export interface LLMCacheStatusResponse { total_cached: number; cache_entries: LLMCacheEntry[] }
export interface CircuitBreakerStatus { provider: string; state: string; failure_count: number; last_failure_time?: number | null }

export interface ExperimentArmStats {
  arm_id: number;
  name: string;
  model_spec: string;
  n: number;
  mean: number;
  var: number;
  values?: number[];
}
export interface ExperimentWinnerResponse { winner: ExperimentArmStats; arms: ExperimentArmStats[]; metric: string; p_value?: number | null }
export interface AssignmentResponse { experiment_id: number; user_id: string; arm_id: number }
export interface FeedbackSubmitResponse { id: number; status: string }
export interface DeploymentStageResponse { model_id: string; status: string; rollout_percent: number }
export interface DeploymentPublishResponse { model_id: string; status: string; rollout_percent: number }
export interface GPUBudgetResponse { user_id: string; budget: number }
export interface GPUUsageResponse { used: number; updated_at?: string | null }
export interface ABExperimentSetResponse { status: string; LLM_AB_EXPERIMENT_ID: number }
export interface FeedbackQuickRequest {
  conversation_id: string;
  message_id: string;
  comment?: string;
  user_id?: string;
}

export interface FeedbackQuickResponse {
  id: string;
  rating: string;
  message: string;
}
</file>

<file path="app/models/memory.models.ts">
export interface GenerativeMemoryItem {
  id?: string;
  content: string;
  score?: number;
  type?: string;
  created_at?: string | number;
  updated_at?: string | number;
  metadata?: {
    importance?: number | string;
    user_id?: string;
    conversation_id?: string;
    session_id?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface UserPreferenceMemoryItem {
  id?: string;
  content: string;
  ts_ms?: number;
  preference_kind?: 'do' | 'dont' | string;
  instruction_text?: string;
  scope?: string;
  confidence?: number;
  user_id?: string;
  conversation_id?: string;
  session_id?: string;
  active?: boolean;
  origin?: string;
  dedupe_key?: string;
  metadata?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface MemoryItem {
  content: string;
  ts_ms: number;
  composite_id?: string;
  metadata?: {
    type?: string;
    user_id?: string;
    conversation_id?: string;
    session_id?: string;
    role?: string;
    timestamp?: number;
    [key: string]: unknown;
  };
}
</file>

<file path="app/models/observability.models.ts">
export interface MetricsSummary {
  llm: { cached_llms: number; circuit_breakers: Record<string, { state: string; failure_count: number }> };
  multi_agent: { active_agents: number; workspace_tasks: number; workspace_artifacts: number };
  poison_pills: Record<string, unknown>;
}

export interface QuarantinedMessage {
  message_id: string; queue: string; reason: string; failure_count: number; quarantined_at: string;
}

export interface QuarantinedMessagesResponse {
  total_quarantined: number; messages: QuarantinedMessage[];
}

export interface GraphQuarantineItem { node_id: number; reason?: string; type?: string; from_name?: string; to_name?: string; confidence?: number; source_snippet?: string }
export type GraphQuarantineListResponse = GraphQuarantineItem[]

export interface AuditEvent { id: number; user_id?: number; endpoint?: string; action?: string; tool?: string; status?: string; latency_ms?: number; trace_id?: string; created_at?: number }
export interface AuditEventsResponse { total: number; events: AuditEvent[] }
export interface ReviewerMetricsResponse { user_id: number; decisions_total: number; approvals: number; rejections: number; synonyms: number; approval_rate: number; rejection_rate: number; avg_latency_ms: number }
export interface PeriodReportResponse { period: string; buckets: { bucket: string; total: number; promote: number; reject: number; synonym: number }[] }
export interface ConsentItem { scope: string; granted: boolean; expires_at?: string | null }
export interface ConsentsListResponse { user_id: number; consents: ConsentItem[] }
export interface PendingAction {
  source?: 'langgraph' | 'sql' | string;
  thread_id?: string;
  action_id?: number;
  status: string;
  message?: string | null;
  user_id?: string;
  tool_name?: string;
  args_json?: string;
  created_at?: string;
  risk_level?: 'low' | 'medium' | 'high' | string;
  risk_summary?: string;
  scope_summary?: string;
  scope_targets?: string[];
  simulation?: Record<string, unknown> | null;
}

// Poison pill stats
export interface PoisonPillStats {
  total: number;
  by_queue: Record<string, { count: number; last_quarantined_at?: string }>;
}

// Reflexion
export interface ReflexionLesson {
  id: string
  content: string
  score?: number
  metadata?: Record<string, unknown>
}
</file>

<file path="app/models/productivity.models.ts">
export interface UserRolesResponse { user_id: number; roles: string[] }
export interface TokenResponse { token: string }
export interface ProductivityLimitUsage { max_per_day: number; used: number; remaining: number }
export interface ProductivityLimitsStatusResponse { user_id: string; limits: Record<string, ProductivityLimitUsage> }
export interface GoogleOAuthStartResponse { authorize_url: string }
export interface GoogleOAuthCallbackResponse { status: string; state?: string }
export interface CalendarEvent { title: string; start_ts: number; end_ts: number; location?: string; notes?: string }
export interface CalendarAddRequest { user_id: number; event: CalendarEvent; index?: boolean }
export interface MailMessage { to: string; subject: string; body: string }
export interface MailSendRequest { user_id: number; message: MailMessage; index?: boolean }
export interface UserStatusResponse { user_id: string; conversations: number; messages: number; approx_in_tokens: number; approx_out_tokens: number; vector_points: number }
</file>

<file path="app/models/system.models.ts">
export interface SystemStatus {
  app_name: string;
  version: string;
  environment: string;
  status: string;
  timestamp?: string;
  uptime_seconds?: number;
  system?: Record<string, unknown>;
  process?: Record<string, unknown>;
  performance?: Record<string, unknown>;
  config?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface ServiceHealthItem {
  key: string;
  name: string;
  status: string;
  metric_text?: string;
}

export interface ServiceHealthResponse {
  services: ServiceHealthItem[];
}

export interface WorkerStatusResponse {
  id: string;
  status: string;
  last_heartbeat: string | Date; // Backend sends datetime string, but frontend might parse it
  tasks_processed: number;
}

export interface OrchestratorWorkerTaskStatus {
  name: string;
  running: boolean;
  done: boolean;
  cancelled: boolean;
  exception?: string | null;
  state: string;
  reason?: string;
  detail?: string;
  composite?: boolean;
  children?: OrchestratorWorkerTaskStatus[];
}

export interface QueueInfoResponse {
  name: string;
  messages: number;
  consumers: number;
}

export interface SystemOverviewResponse {
  system_status: SystemStatus;
  services_status: ServiceHealthItem[];
  workers_status: WorkerStatusResponse[];
}

// Database Validation
export interface DbValidationCheck {
  table: string;
  name: string;
  kind: string;
  exists: boolean;
}

export interface DbValidationResponse {
  status: string;
  checks: DbValidationCheck[];
}

// Observability health
export interface ObservabilitySystemHealth {
  status: string;
  dependencies?: Record<string, { status: string; details?: Record<string, unknown> }>;
}

export interface QueueAck { status: string; task_id?: string }
export interface WorkersStatusResponse {
  tracked: number;
  workers: OrchestratorWorkerTaskStatus[];
}

// Auto Analysis
export interface HealthInsight {
  issue: string
  severity: string
  suggestion: string
  estimated_impact: string
}

export interface AutoAnalysisResponse {
  timestamp: string
  overall_health: string
  insights: HealthInsight[]
  fun_fact: string
}

export type WorkersStatusItem = WorkerStatusResponse;
</file>

<file path="app/models/tools.models.ts">
export interface Tool {
  name: string;
  description: string;
  args_schema?: Record<string, unknown>;
  category?: string;
  permission_level?: string;
  rate_limit_per_minute?: number;
  requires_confirmation?: boolean;
  tags?: string[];
  enabled?: boolean;
}

export interface ToolListResponse {
  tools: Tool[];
}

export interface ToolStats {
  total_tools_registered?: number;
  total_calls?: number;
  successful_calls?: number;
  success_rate?: number;
  tool_usage?: Record<string, { total: number; success: number; avg_duration: number }>;
}
</file>

<file path="app/services/domain/autonomy-api-service.ts">
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { MetaAgentLatestReportResponse, MetaAgentHeartbeatStatus, Goal, GoalCreateRequest, AutonomyStartRequest, AutonomyStatusResponse, AutonomyPlanResponse, AutonomyPolicyUpdateRequest, AdminBacklogSyncResponse, AdminBacklogSprintType, SelfStudyRun, SelfStudyStatusResponse, AdminCodeQaResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class AutonomyApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getMetaAgentLatestReport(): Observable<MetaAgentLatestReportResponse> {
    return this.http.get<MetaAgentLatestReportResponse>(this.apiContext.buildUrl(`/api/v1/meta-agent/report/latest`));
  }

getMetaAgentHeartbeatStatus(): Observable<MetaAgentHeartbeatStatus> {
    return this.http.get<MetaAgentHeartbeatStatus>(this.apiContext.buildUrl(`/api/v1/meta-agent/heartbeat/status`));
  }

startAutonomy(req: AutonomyStartRequest): Observable<{ status: string; interval_seconds: number }> {
    return this.http.post<{ status: string; interval_seconds: number }>(this.apiContext.buildUrl(`/api/v1/autonomy/start`), req)
  }

stopAutonomy(): Observable<{ status: string }> {
    return this.http.post<{ status: string }>(this.apiContext.buildUrl(`/api/v1/autonomy/stop`), {})
  }

getAutonomyStatus(): Observable<AutonomyStatusResponse> {
    return this.http.get<AutonomyStatusResponse>(this.apiContext.buildUrl(`/api/v1/autonomy/status`))
  }

getAutonomyPlan(): Observable<AutonomyPlanResponse> {
    return this.http.get<AutonomyPlanResponse>(this.apiContext.buildUrl(`/api/v1/autonomy/plan`))
  }

updateAutonomyPlan(plan: { tool: string; args: Record<string, unknown> }[]): Observable<{ status: string; steps_count: number }> {
    return this.http.put<{ status: string; steps_count: number }>(this.apiContext.buildUrl('/api/v1/autonomy/plan'), { plan })
  }

updateAutonomyPolicy(req: AutonomyPolicyUpdateRequest): Observable<{ status: string; policy: Record<string, unknown> }> {
    return this.http.put<{ status: string; policy: Record<string, unknown> }>(this.apiContext.buildUrl(`/api/v1/autonomy/policy`), req)
  }

listGoals(status?: string): Observable<Goal[]> {
    const qs = new URLSearchParams()
    if (status) qs.set('status', status)
    return this.http.get<Goal[]>(this.apiContext.buildUrl(`/api/v1/autonomy/goals${qs.toString() ? '?' + qs.toString() : ''}`))
  }

getGoal(goal_id: string): Observable<Goal> {
    return this.http.get<Goal>(this.apiContext.buildUrl(`/api/v1/autonomy/goals/${encodeURIComponent(goal_id)}`))
  }

createGoal(req: GoalCreateRequest): Observable<Goal> {
    return this.http.post<Goal>(this.apiContext.buildUrl(`/api/v1/autonomy/goals`), req)
  }

updateGoalStatus(goal_id: string, status: 'pending' | 'in_progress' | 'completed' | 'failed'): Observable<Goal> {
    return this.http.patch<Goal>(this.apiContext.buildUrl(`/api/v1/autonomy/goals/${encodeURIComponent(goal_id)}/status`), { status })
  }

deleteGoal(goal_id: string): Observable<{ status: string; goal_id: string }> {
    return this.http.delete<{ status: string; goal_id: string }>(this.apiContext.buildUrl(`/api/v1/autonomy/goals/${encodeURIComponent(goal_id)}`))
  }

syncAutonomyAdminBacklog(): Observable<AdminBacklogSyncResponse> {
    return this.http.post<AdminBacklogSyncResponse>(this.apiContext.buildUrl(`/api/v1/autonomy/admin/backlog/sync`), {})
  }

getAutonomyAdminBoard(params: { status?: string; limit?: number } = {}): Observable<{ items: AdminBacklogSprintType[] }> {
    const qs = new URLSearchParams()
    if (params.status) qs.set('status', String(params.status))
    qs.set('limit', String(params.limit ?? 200))
    return this.http.get<{ items: AdminBacklogSprintType[] }>(this.apiContext.buildUrl(`/api/v1/autonomy/admin/board?${qs.toString()}`))
  }

runAutonomyAdminSelfStudy(req: { mode: 'incremental' | 'full'; reason?: string }): Observable<{ status: string; run_id: number }> {
    return this.http.post<{ status: string; run_id: number }>(this.apiContext.buildUrl(`/api/v1/autonomy/admin/self-study/run`), req)
  }

getAutonomyAdminSelfStudyStatus(): Observable<SelfStudyStatusResponse> {
    return this.http.get<SelfStudyStatusResponse>(this.apiContext.buildUrl(`/api/v1/autonomy/admin/self-study/status`))
  }

listAutonomyAdminSelfStudyRuns(limit: number = 20): Observable<{ items: SelfStudyRun[] }> {
    const qs = new URLSearchParams()
    qs.set('limit', String(limit))
    return this.http.get<{ items: SelfStudyRun[] }>(this.apiContext.buildUrl(`/api/v1/autonomy/admin/self-study/runs?${qs.toString()}`))
  }

askAutonomyAdminCodeQa(req: { question: string; limit?: number; citation_limit?: number }): Observable<AdminCodeQaResponse> {
    return this.http.post<AdminCodeQaResponse>(this.apiContext.buildUrl(`/api/v1/autonomy/admin/code-qa`), req)
  }
}
</file>

<file path="app/services/domain/chat-api-service.ts">
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { AppLoggerService } from '../../core/services/app-logger.service';
import { ChatStartResponse, ChatStartRequest, ChatMessageRequest, ChatMessage, ChatStudyJobResponse, ChatMessageResponse, ChatHistoryResponse, ChatListItem, ChatHistoryPaginatedResponse, Citation, TraceStep, ConversationMeta, ConversationsListResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class ChatApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService,
    private logger: AppLoggerService
  ) {}

getConversationTrace(conversationId: string): Observable<TraceStep[]> {
    return this.http.get<TraceStep[]>(this.apiContext.buildUrl(`/api/v1/chat/${encodeURIComponent(conversationId)}/trace`));
  }

startChat(title?: string, persona?: string, user_id?: string, project_id?: string): Observable<ChatStartResponse> {
    const body: ChatStartRequest = { title }
    if (persona) body.persona = persona
    if (user_id) body.user_id = user_id
    if (project_id) body.project_id = project_id
    return this.http.post<ChatStartResponse>(this.apiContext.buildUrl(`/api/v1/chat/start`), body)
  }

sendChatMessage(conversation_id: string, content: string, role: string = 'orchestrator', priority: string = 'fast_and_cheap', timeout_seconds?: number, user_id?: string, project_id?: string, knowledge_space_id?: string): Observable<ChatMessageResponse & { citations?: Citation[] }> {
    // Validate required fields
    // Validate required fields
    if (!conversation_id || conversation_id.trim().length < 1) {
      this.logger.error('[BackendApiService] Invalid conversation_id provided to sendChatMessage', { conversation_id });
      throw new Error(`Invalid conversation_id: ${conversation_id}`);
    }

    this.logger.debug('[BackendApiService] Sending chat message', {
      conversation_id_raw: conversation_id,
      conversation_id_trimmed: conversation_id.trim(),
      role,
      priority,
    });

    const body: ChatMessageRequest = {
      conversation_id: conversation_id.trim(),
      message: content,
      role: role || 'orchestrator',
      priority: priority || 'fast_and_cheap'
    };

    if (typeof timeout_seconds !== 'undefined') body.timeout_seconds = timeout_seconds
    if (user_id) body.user_id = user_id
    if (project_id) body.project_id = project_id
    if (knowledge_space_id) body.knowledge_space_id = knowledge_space_id

    this.logger.debug('[BackendApiService] Sending chat message payload', body);

    return this.http.post<ChatMessageResponse>(this.apiContext.buildUrl(`/api/v1/chat/message`), body).pipe(
      tap({
        next: (res) => this.logger.debug('[BackendApiService] Chat message success', res),
        error: (err) => this.logger.error('[BackendApiService] Chat message failed', err)
      })
    )
  }

getChatStudyJob(jobId: string): Observable<ChatStudyJobResponse> {
    return this.http.get<ChatStudyJobResponse>(this.apiContext.buildUrl(`/api/v1/chat/study-jobs/${encodeURIComponent(jobId)}`))
  }

getChatHistory(conversation_id: string): Observable<ChatHistoryResponse> {
    return this.http.get<ChatHistoryResponse>(this.apiContext.buildUrl(`/api/v1/chat/${encodeURIComponent(conversation_id)}/history`)).pipe(
      map((resp) => {
        const msgs = Array.isArray(resp?.messages) ? resp.messages : []
        const mapped = msgs.map((m) => ({
          message_id: typeof m?.message_id === 'string' ? String(m.message_id) : undefined,
          role: String(m?.role || ''),
          text: this.normalizeChatText(m?.text),
          timestamp: m?.timestamp != null ? Number(m.timestamp) : 0,
          citations: m?.citations,
          citation_status: m?.citation_status,
          reasoning: m?.reasoning,
          ui: m?.ui,
          understanding: m?.understanding,
          confirmation: m?.confirmation,
          agent_state: m?.agent_state,
          delivery_status: typeof m?.delivery_status === 'string' ? String(m.delivery_status) : undefined,
          failure_classification: typeof m?.failure_classification === 'string' ? String(m.failure_classification) : undefined,
          provider: typeof m?.provider === 'string' ? String(m.provider) : undefined,
          model: typeof m?.model === 'string' ? String(m.model) : undefined,
        }))
        return { conversation_id: String(resp?.conversation_id || conversation_id), messages: mapped } as ChatHistoryResponse
      })
    )
  }

getChatHistoryPaginated(conversation_id: string, params: {
    limit?: number;
    offset?: number;
    before_ts?: number;
    after_ts?: number;
  } = {}): Observable<{
    conversation_id: string;
    messages: ChatMessage[];
    total_count: number;
    has_more: boolean;
    next_offset?: number;
    limit: number;
    offset: number;
  }> {
    const qs = new URLSearchParams()
    if (params.limit) qs.set('limit', String(params.limit))
    if (params.offset) qs.set('offset', String(params.offset))
    if (params.before_ts) qs.set('before_ts', String(params.before_ts))
    if (params.after_ts) qs.set('after_ts', String(params.after_ts))

    const url = this.apiContext.buildUrl(`/api/v1/chat/${encodeURIComponent(conversation_id)}/history${qs.toString() ? '?' + qs.toString() : ''}`)

    return this.http.get<ChatHistoryPaginatedResponse>(url).pipe(
      map((resp) => {
        const msgs = Array.isArray(resp?.messages) ? resp.messages : []
        const mapped = msgs.map((m) => ({
          message_id: typeof m?.message_id === 'string' ? String(m.message_id) : undefined,
          role: String(m?.role || ''),
          text: this.normalizeChatText(m?.text),
          timestamp: m?.timestamp != null ? Number(m.timestamp) : 0,
          citations: m?.citations,
          citation_status: m?.citation_status,
          reasoning: m?.reasoning,
          ui: m?.ui,
          understanding: m?.understanding,
          confirmation: m?.confirmation,
          agent_state: m?.agent_state,
          delivery_status: typeof m?.delivery_status === 'string' ? String(m.delivery_status) : undefined,
          failure_classification: typeof m?.failure_classification === 'string' ? String(m.failure_classification) : undefined,
          provider: typeof m?.provider === 'string' ? String(m.provider) : undefined,
          model: typeof m?.model === 'string' ? String(m.model) : undefined,
        }))

        return {
          conversation_id: String(resp?.conversation_id || conversation_id),
          messages: mapped,
          total_count: Number(resp?.total_count || 0),
          has_more: Boolean(resp?.has_more || false),
          next_offset: resp?.next_offset != null ? Number(resp.next_offset) : undefined,
          limit: Number(resp?.limit || params.limit || 50),
          offset: Number(resp?.offset || params.offset || 0)
        }
      })
    )
  }

checkChatHealth(): Observable<{ status: string, repository_accessible: boolean, total_conversations: number }> {
    return this.http.get<{ status: string, repository_accessible: boolean, total_conversations: number }>(this.apiContext.buildUrl('/api/v1/chat/health'))
  }

listConversations(params: { user_id?: string; project_id?: string; limit?: number } = {}): Observable<ConversationsListResponse> {
    const qs = new URLSearchParams()
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.project_id) qs.set('project_id', params.project_id)
    qs.set('limit', String(params.limit ?? 50))

    return this.http.get<ChatListItem[] | { conversations: ChatListItem[] }>(this.apiContext.buildUrl(`/api/v1/chat/conversations?${qs.toString()}`)).pipe(
      map((resp) => {
        // Backend now returns array directly, not {conversations: [...]}
        const items = Array.isArray(resp) ? resp : (resp as { conversations: ChatListItem[] }).conversations || []

        const mapped = items.map((it) => {
          const lm = it?.last_message
          const last_message: ChatMessage | undefined = lm && typeof lm === 'object' ? {
            role: String(lm?.role || ''),
            text: this.normalizeChatText(lm?.text),
            timestamp: lm?.timestamp != null ? Number(lm.timestamp) : 0,
            citations: lm?.citations,
            citation_status: lm?.citation_status,
            reasoning: lm?.reasoning,
            ui: lm?.ui,
            understanding: lm?.understanding,
            confirmation: lm?.confirmation,
            agent_state: lm?.agent_state,
          } : undefined
          return {
            conversation_id: String(it?.conversation_id || ''),
            title: it?.title,
            created_at: it?.created_at,
            updated_at: it?.updated_at,
            last_message,
            message_count: undefined, // Not in backend response
            tags: undefined, // Not in backend response
          } as ConversationMeta
        })

        return { conversations: mapped } as ConversationsListResponse
      })
    )
  }

renameConversation(conversation_id: string, new_title: string): Observable<{ status: string }> {
    return this.http.put<{ status: string }>(this.apiContext.buildUrl(`/api/v1/chat/${encodeURIComponent(conversation_id)}/rename`), { new_title })
  }

deleteConversation(conversation_id: string): Observable<{ status: string }> {
    return this.http.delete<{ status: string }>(this.apiContext.buildUrl(`/api/v1/chat/${encodeURIComponent(conversation_id)}`))
  }

public normalizeChatText(value: unknown): string {
    if (value === null || value === undefined) return ''
    if (typeof value === 'string') return value
    if (typeof value === 'number' || typeof value === 'boolean') return String(value)
    try {
      return JSON.stringify(value, null, 2)
    } catch {
      return String(value)
    }
  }
}
</file>

<file path="app/services/domain/context-api-service.ts">
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { ContextInfo, WebSearchResult, WebCacheStatus } from '../../models';

@Injectable({ providedIn: 'root' })
export class ContextApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getCurrentContext(): Observable<ContextInfo> {
    return this.http.get<ContextInfo>(this.apiContext.buildUrl(`/api/v1/context/current`))
  }

searchWeb(query: string, max_results: number = 5, search_depth: 'basic' | 'advanced' = 'basic'): Observable<WebSearchResult> {
    const params = new URLSearchParams({ query, max_results: String(max_results), search_depth })
    return this.http.get<WebSearchResult>(this.apiContext.buildUrl(`/api/v1/context/web-search?${params.toString()}`))
  }

getWebCacheStatus(): Observable<WebCacheStatus> {
    return this.http.get<WebCacheStatus>(this.apiContext.buildUrl(`/api/v1/context/web-cache/status`))
  }

invalidateWebCache(query?: string): Observable<Record<string, unknown>> {
    return this.http.post<Record<string, unknown>>(this.apiContext.buildUrl(`/api/v1/context/web-cache/invalidate`), { query })
  }
}
</file>

<file path="app/services/domain/documents-api-service.ts">
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { AppLoggerService } from '../../core/services/app-logger.service';
import { UploadResponse, DocListResponse, DocSearchResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class DocumentsApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService,
    private logger: AppLoggerService
  ) {}

linkUrl(conversation_id: string, url: string, user_id?: string): Observable<UploadResponse> {
    const form = new FormData()
    form.append('url', url)
    form.append('conversation_id', conversation_id)
    if (user_id) form.append('user_id', user_id)
    return this.http.post<UploadResponse>(this.apiContext.buildUrl(`/api/v1/documents/link-url`), form)
  }

listDocuments(conversationId?: string, userId?: string): Observable<DocListResponse> {
    const qs = new URLSearchParams();
    if (conversationId) qs.set('conversation_id', conversationId);
    if (userId) qs.set('user_id', userId);
    const headers = this.apiContext.headersFor(userId);
    return this.http.get<DocListResponse>(this.apiContext.buildUrl(`/api/v1/documents/list${qs.toString() ? '?' + qs.toString() : ''}`), { headers });
  }

uploadDocument(file: File, conversationId?: string, userId?: string): Observable<{ progress?: number; response?: UploadResponse }> {
    const form = new FormData();
    form.append('file', file);
    if (conversationId) form.append('conversation_id', conversationId);
    if (userId) form.append('user_id', userId);

    const headers = this.apiContext.headersFor(userId);
    this.logger.debug('[BackendApiService] uploadDocument params', { userId, userHeader: headers['X-User-Id'] });
    return this.http.post<UploadResponse>(this.apiContext.buildUrl(`/api/v1/documents/upload`), form, { headers, reportProgress: true, observe: 'events' }).pipe(
      map((event: HttpEvent<UploadResponse>) => {
        if (event.type === HttpEventType.UploadProgress) {
          const pct = Math.round((event.loaded / Math.max(1, event.total || 1)) * 100)
          return { progress: pct }
        } else if (event.type === HttpEventType.Response) {
          return { response: event.body || undefined }
        }
        return {}
      })
    )
  }

searchDocuments(query: string, minScore?: number, docId?: string, userId?: string): Observable<DocSearchResponse> {
    const qs = new URLSearchParams()
    qs.set('query', query)
    if (minScore !== undefined) qs.set('min_score', String(minScore))
    if (docId) qs.set('doc_id', docId)
    if (userId) qs.set('user_id', String(userId))
    const headers = userId ? this.apiContext.headersFor(userId) : undefined
    return this.http.get<DocSearchResponse>(
      this.apiContext.buildUrl(`/api/v1/documents/search?${qs.toString()}`),
      headers ? { headers } : undefined
    )
  }

deleteDocument(docId: string, userId?: string): Observable<{ status: string; doc_id: string }> {
    const qs = new URLSearchParams()
    if (userId) qs.set('user_id', String(userId))
    const headers = userId ? this.apiContext.headersFor(userId) : undefined
    return this.http.delete<{ status: string; doc_id: string }>(
      this.apiContext.buildUrl(`/api/v1/documents/${encodeURIComponent(docId)}${qs.toString() ? '?' + qs.toString() : ''}`),
      headers ? { headers } : undefined
    )
  }
}
</file>

<file path="app/services/domain/experiment-api-service.ts">
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { ExperimentWinnerResponse, AssignmentResponse, FeedbackSubmitResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class ExperimentApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getExperimentWinner(experiment_id: number, metric_name: string = 'accuracy'): Observable<ExperimentWinnerResponse> {
    const qs = new URLSearchParams({ metric_name })
    return this.http.get<ExperimentWinnerResponse>(this.apiContext.buildUrl(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/winner?${qs.toString()}`))
  }

assignUserToExperiment(experiment_id: number, user_id: string): Observable<AssignmentResponse> {
    return this.http.post<AssignmentResponse>(this.apiContext.buildUrl(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/assign`), { user_id })
  }

submitExperimentFeedback(experiment_id: number, user_id: string, rating: number, notes?: string): Observable<FeedbackSubmitResponse> {
    return this.http.post<FeedbackSubmitResponse>(this.apiContext.buildUrl(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/feedback`), { user_id, rating, notes })
  }

getExperimentFeedbackStats(experiment_id: number): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(this.apiContext.buildUrl(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/feedback/stats`))
  }
}
</file>

<file path="app/services/domain/feedback-api-service.ts">
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { FeedbackQuickRequest, FeedbackQuickResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class FeedbackApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

thumbsUpFeedback(req: FeedbackQuickRequest): Observable<FeedbackQuickResponse> {
    const qs = new URLSearchParams()
    if (req.user_id) qs.set('user_id', String(req.user_id))
    return this.http.post<FeedbackQuickResponse>(
      this.apiContext.buildUrl(`/api/v1/feedback/thumbs-up${qs.toString() ? '?' + qs.toString() : ''}`),
      {
        conversation_id: req.conversation_id,
        message_id: req.message_id,
        comment: req.comment,
      }
    )
  }

thumbsDownFeedback(req: FeedbackQuickRequest): Observable<FeedbackQuickResponse> {
    const qs = new URLSearchParams()
    if (req.user_id) qs.set('user_id', String(req.user_id))
    return this.http.post<FeedbackQuickResponse>(
      this.apiContext.buildUrl(`/api/v1/feedback/thumbs-down${qs.toString() ? '?' + qs.toString() : ''}`),
      {
        conversation_id: req.conversation_id,
        message_id: req.message_id,
        comment: req.comment,
      }
    )
  }
}
</file>

<file path="app/services/domain/graph-api-service.ts">
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { ContextualGraphResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class GraphApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getContextualGraph(query?: string, conversationId?: string, hops: number = 1): Observable<ContextualGraphResponse> {
    const qs = new URLSearchParams();
    if (query) qs.set('query', query);
    if (conversationId) qs.set('conversation_id', conversationId);
    qs.set('hops', String(hops));
    return this.http.get<ContextualGraphResponse>(this.apiContext.buildUrl(`/api/v1/admin/graph/contextual?${qs.toString()}`));
  }
}
</file>

<file path="app/services/domain/knowledge-api-service.ts">
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { RagUserChatResponse, RagUserChatV2Response, KnowledgeHealthResponse, KnowledgeHealthDetailedResponse, KnowledgeSpace, KnowledgeSpaceStatus, KnowledgeSpaceCreateRequest, KnowledgeSpaceListResponse, KnowledgeSpaceAttachRequest, KnowledgeSpaceConsolidationResponse, KnowledgeSpaceQueryResponse, RagSearchResponse, RagHybridResponse, KnowledgeStats, EntityRelationshipsResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class KnowledgeApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

createKnowledgeSpace(payload: KnowledgeSpaceCreateRequest): Observable<KnowledgeSpace> {
    const headers = payload.user_id ? this.apiContext.headersFor(payload.user_id) : undefined
    return this.http.post<KnowledgeSpace>(
      this.apiContext.buildUrl('/api/v1/knowledge/spaces'),
      payload,
      headers ? { headers } : undefined
    )
  }

listKnowledgeSpaces(userId?: string, limit: number = 100): Observable<KnowledgeSpaceListResponse> {
    const qs = new URLSearchParams()
    if (userId) qs.set('user_id', String(userId))
    qs.set('limit', String(limit))
    const headers = userId ? this.apiContext.headersFor(userId) : undefined
    return this.http.get<KnowledgeSpaceListResponse>(
      this.apiContext.buildUrl(`/api/v1/knowledge/spaces?${qs.toString()}`),
      headers ? { headers } : undefined
    )
  }

getKnowledgeSpaceStatus(knowledgeSpaceId: string, userId?: string): Observable<KnowledgeSpaceStatus> {
    const qs = new URLSearchParams()
    if (userId) qs.set('user_id', String(userId))
    const headers = userId ? this.apiContext.headersFor(userId) : undefined
    return this.http.get<KnowledgeSpaceStatus>(
      this.apiContext.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}${qs.toString() ? '?' + qs.toString() : ''}`),
      headers ? { headers } : undefined
    )
  }

attachDocumentToKnowledgeSpace(
    knowledgeSpaceId: string,
    docId: string,
    payload: KnowledgeSpaceAttachRequest = {},
  ): Observable<{ status: string; document: Record<string, unknown> }> {
    const headers = payload.user_id ? this.apiContext.headersFor(payload.user_id) : undefined
    return this.http.post<{ status: string; document: Record<string, unknown> }>(
      this.apiContext.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}/documents/${encodeURIComponent(docId)}/attach`),
      payload,
      headers ? { headers } : undefined
    )
  }

consolidateKnowledgeSpace(
    knowledgeSpaceId: string,
    payload: { user_id?: string; limit_docs?: number } = {},
  ): Observable<KnowledgeSpaceConsolidationResponse> {
    const headers = payload.user_id ? this.apiContext.headersFor(payload.user_id) : undefined
    return this.http.post<KnowledgeSpaceConsolidationResponse>(
      this.apiContext.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}/consolidate`),
      payload,
      headers ? { headers } : undefined
    )
  }

queryKnowledgeSpace(
    knowledgeSpaceId: string,
    payload: { user_id?: string; question: string; mode?: string; limit?: number },
  ): Observable<KnowledgeSpaceQueryResponse> {
    const headers = payload.user_id ? this.apiContext.headersFor(payload.user_id) : undefined
    return this.http.post<KnowledgeSpaceQueryResponse>(
      this.apiContext.buildUrl(`/api/v1/knowledge/spaces/${encodeURIComponent(knowledgeSpaceId)}/query`),
      payload,
      headers ? { headers } : undefined
    )
  }

ragSearch(params: {
    query: string
    type?: string
    origin?: string
    doc_id?: string
    file_path?: string
    limit?: number
    min_score?: number
  }): Observable<RagSearchResponse> {
    const qs = new URLSearchParams()
    qs.set('query', params.query)
    if (params.type) qs.set('type', params.type)
    if (params.origin) qs.set('origin', params.origin)
    if (params.doc_id) qs.set('doc_id', params.doc_id)
    if (params.file_path) qs.set('file_path', params.file_path)
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.min_score != null) qs.set('min_score', String(params.min_score))
    return this.http.get<RagSearchResponse>(this.apiContext.buildUrl(`/api/v1/rag/search?${qs.toString()}`))
  }

ragUserChat(params: {
    query: string
    user_id: string
    session_id?: string
    role?: string
    limit?: number
    min_score?: number
  }): Observable<RagUserChatResponse> {
    const qs = new URLSearchParams()
    qs.set('query', params.query)
    qs.set('user_id', params.user_id)
    if (params.session_id) qs.set('session_id', params.session_id)
    if (params.role) qs.set('role', params.role)
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.min_score != null) qs.set('min_score', String(params.min_score))
    return this.http.get<RagUserChatResponse>(this.apiContext.buildUrl(`/api/v1/rag/user-chat?${qs.toString()}`))
  }

ragUserChatV2(params: {
    query: string
    user_id?: string
    session_id?: string
    start_ts_ms?: number
    end_ts_ms?: number
    limit?: number
    min_score?: number
  }): Observable<RagUserChatV2Response> {
    const qs = new URLSearchParams()
    qs.set('query', params.query)
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.session_id) qs.set('session_id', params.session_id)
    if (params.start_ts_ms != null) qs.set('start_ts_ms', String(params.start_ts_ms))
    if (params.end_ts_ms != null) qs.set('end_ts_ms', String(params.end_ts_ms))
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.min_score != null) qs.set('min_score', String(params.min_score))
    const headers = params.user_id ? this.apiContext.headersFor(params.user_id) : undefined
    return this.http.get<RagUserChatV2Response>(
      this.apiContext.buildUrl(`/api/v1/rag/user_chat?${qs.toString()}`),
      headers ? { headers } : undefined
    )
  }

ragHybridSearch(params: {
    query: string
    user_id?: string
    limit?: number
    min_score?: number
  }): Observable<RagHybridResponse> {
    const qs = new URLSearchParams()
    qs.set('query', params.query)
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.min_score != null) qs.set('min_score', String(params.min_score))
    const headers = params.user_id ? this.apiContext.headersFor(params.user_id) : undefined
    return this.http.get<RagHybridResponse>(
      this.apiContext.buildUrl(`/api/v1/rag/hybrid_search?${qs.toString()}`),
      headers ? { headers } : undefined
    )
  }

ragProductivitySearch(params: {
    query: string
    user_id: string
    limit?: number
    min_score?: number
  }): Observable<RagSearchResponse> {
    const qs = new URLSearchParams()
    qs.set('query', params.query)
    qs.set('user_id', params.user_id)
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.min_score != null) qs.set('min_score', String(params.min_score))
    const headers = this.apiContext.headersFor(params.user_id)
    return this.http.get<RagSearchResponse>(this.apiContext.buildUrl(`/api/v1/rag/productivity?${qs.toString()}`), { headers })
  }

getKnowledgeStats(): Observable<KnowledgeStats> {
    return this.http.get<KnowledgeStats>(this.apiContext.buildUrl(`/api/v1/knowledge/stats`))
  }

getEntityRelationships(entityName: string): Observable<EntityRelationshipsResponse> {
    const qs = new URLSearchParams({ max_depth: '1', limit: '20' })
    return this.http.get<EntityRelationshipsResponse>(this.apiContext.buildUrl(`/api/v1/knowledge/entity/${encodeURIComponent(entityName)}/relationships?${qs.toString()}`))
  }

getKnowledgeHealth(): Observable<KnowledgeHealthResponse> {
    return this.http.get<KnowledgeHealthResponse>(this.apiContext.buildUrl(`/api/v1/knowledge/health`))
  }

getKnowledgeHealthDetailed(): Observable<KnowledgeHealthDetailedResponse> {
    return this.http.get<KnowledgeHealthDetailedResponse>(this.apiContext.buildUrl(`/api/v1/knowledge/health/detailed`))
  }

resetKnowledgeCircuitBreaker(): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(this.apiContext.buildUrl(`/api/v1/knowledge/health/reset-circuit-breaker`), {})
  }
}
</file>

<file path="app/services/domain/llm-api-service.ts">
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { LLMProvidersResponse, LLMSubsystemHealth, LLMCacheStatusResponse, CircuitBreakerStatus, DeploymentStageResponse, DeploymentPublishResponse, GPUBudgetResponse, GPUUsageResponse, ABExperimentSetResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class LlmApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

listLLMProviders(): Observable<LLMProvidersResponse> {
    return this.http.get<LLMProvidersResponse>(this.apiContext.buildUrl(`/api/v1/llm/providers`))
  }

getLLMHealth(): Observable<LLMSubsystemHealth> {
    return this.http.get<LLMSubsystemHealth>(this.apiContext.buildUrl(`/api/v1/llm/health`))
  }

getLLMCacheStatus(): Observable<LLMCacheStatusResponse> {
    return this.http.get<LLMCacheStatusResponse>(this.apiContext.buildUrl(`/api/v1/llm/cache/status`))
  }

getLLMCircuitBreakers(): Observable<CircuitBreakerStatus[]> {
    return this.http.get<CircuitBreakerStatus[]>(this.apiContext.buildUrl(`/api/v1/llm/circuit-breakers`))
  }

getBudgetSummary(): Observable<any> {
    return this.http.get(this.apiContext.buildUrl(`/api/v1/llm/budget/summary`))
  }

stageDeployment(model_id: string, rollout_percent: number): Observable<DeploymentStageResponse> {
    return this.http.post<DeploymentStageResponse>(this.apiContext.buildUrl(`/api/v1/deployment/stage`), { model_id, rollout_percent })
  }

publishDeployment(model_id: string): Observable<DeploymentPublishResponse> {
    return this.http.post<DeploymentPublishResponse>(this.apiContext.buildUrl(`/api/v1/deployment/publish?model_id=${encodeURIComponent(model_id)}`), {})
  }

rollbackDeployment(model_id: string): Observable<DeploymentPublishResponse> {
    return this.http.post<DeploymentPublishResponse>(this.apiContext.buildUrl(`/api/v1/deployment/rollback?model_id=${encodeURIComponent(model_id)}`), {})
  }

precheckDeployment(model_id: string): Observable<{ precheck_passed: boolean; bias_score: number; safety_warnings?: string | null }> {
    return this.http.post<{ precheck_passed: boolean; bias_score: number; safety_warnings?: string | null }>(this.apiContext.buildUrl(`/api/v1/deployment/precheck?model_id=${encodeURIComponent(model_id)}`), {})
  }

getGPUUsage(user_id: string): Observable<GPUUsageResponse> {
    return this.http.get<GPUUsageResponse>(this.apiContext.buildUrl(`/api/v1/resources/gpu/usage/${encodeURIComponent(user_id)}`))
  }

setGPUBudget(user_id: string, budget: number): Observable<GPUBudgetResponse> {
    return this.http.post<GPUBudgetResponse>(this.apiContext.buildUrl(`/api/v1/resources/gpu/budget`), { user_id, budget })
  }

setLLMABExperiment(experiment_id: number): Observable<ABExperimentSetResponse> {
    return this.http.post<ABExperimentSetResponse>(this.apiContext.buildUrl(`/api/v1/llm/ab/set-experiment`), { experiment_id })
  }
}
</file>

<file path="app/services/domain/memory-api-service.ts">
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { GenerativeMemoryItem, UserPreferenceMemoryItem, MemoryItem } from '../../models';

@Injectable({ providedIn: 'root' })
export class MemoryApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getMemoryTimeline(params: {
    start_date?: string
    end_date?: string
    query?: string
    limit?: number
    min_score?: number
    user_id?: string
    conversation_id?: string
  } = {}): Observable<MemoryItem[]> {
    const qs = new URLSearchParams()
    if (params.start_date) qs.set('start_date', params.start_date)
    if (params.end_date) qs.set('end_date', params.end_date)
    if (params.query) qs.set('query', params.query)
    if (params.limit) qs.set('limit', String(params.limit))
    if (params.min_score !== undefined) qs.set('min_score', String(params.min_score))
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.conversation_id) qs.set('conversation_id', params.conversation_id)
    const headers = params.user_id ? this.apiContext.headersFor(params.user_id) : undefined
    return this.http.get<MemoryItem[]>(
      this.apiContext.buildUrl(`/api/v1/memory/timeline${qs.toString() ? '?' + qs.toString() : ''}`),
      headers ? { headers } : undefined
    )
  }

getGenerativeMemories(
    query: string,
    limit: number = 10,
    filters: { type?: string; userId?: string; conversationId?: string } = {}
  ): Observable<GenerativeMemoryItem[]> {
    const qs = new URLSearchParams()
    qs.set('query', query)
    qs.set('limit', String(limit))
    if (filters.type) qs.set('type', String(filters.type))
    if (filters.userId) qs.set('user_id', String(filters.userId))
    if (filters.conversationId) qs.set('conversation_id', String(filters.conversationId))
    return this.http.get<GenerativeMemoryItem[]>(this.apiContext.buildUrl(`/api/v1/memory/generative?${qs.toString()}`))
  }

addGenerativeMemory(
    content: string,
    opts: { importance?: number; type?: string; userId?: string; conversationId?: string; sessionId?: string } = {}
  ): Observable<GenerativeMemoryItem> {
    const qs = new URLSearchParams()
    qs.set('content', content)
    if (typeof opts.importance === 'number') qs.set('importance', String(opts.importance))
    if (opts.type) qs.set('type', String(opts.type))
    if (opts.userId) qs.set('user_id', String(opts.userId))
    if (opts.conversationId) qs.set('conversation_id', String(opts.conversationId))
    if (opts.sessionId) qs.set('session_id', String(opts.sessionId))
    return this.http.post<GenerativeMemoryItem>(this.apiContext.buildUrl(`/api/v1/memory/generative?${qs.toString()}`), {})
  }

getUserPreferences(params: {
    userId?: string
    conversationId?: string
    query?: string
    limit?: number
    activeOnly?: boolean
  } = {}): Observable<UserPreferenceMemoryItem[]> {
    const qs = new URLSearchParams()
    if (params.userId) qs.set('user_id', String(params.userId))
    if (params.conversationId) qs.set('conversation_id', String(params.conversationId))
    if (params.query) qs.set('query', String(params.query))
    if (typeof params.limit === 'number') qs.set('limit', String(params.limit))
    if (typeof params.activeOnly === 'boolean') qs.set('active_only', String(params.activeOnly))
    const headers = params.userId ? this.apiContext.headersFor(params.userId) : undefined
    return this.http.get<UserPreferenceMemoryItem[]>(
      this.apiContext.buildUrl(`/api/v1/memory/preferences${qs.toString() ? '?' + qs.toString() : ''}`),
      headers ? { headers } : undefined
    )
  }
}
</file>

<file path="app/services/domain/observability-api-service.ts">
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { PostSprintSummaryResponse, MetricsSummary, QuarantinedMessagesResponse, GraphQuarantineListResponse, AuditEventsResponse, ReviewerMetricsResponse, PeriodReportResponse, ConsentsListResponse, PendingAction, PoisonPillStats, ObservabilitySystemHealth } from '../../models';

@Injectable({ providedIn: 'root' })
export class ObservabilityApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getObservabilitySystemHealth(): Observable<ObservabilitySystemHealth> {
    return this.http.get<ObservabilitySystemHealth>(this.apiContext.buildUrl(`/api/v1/observability/health/system`))
  }

getObservabilityMetricsSummary(): Observable<MetricsSummary> {
    return this.http.get<MetricsSummary>(this.apiContext.buildUrl(`/api/v1/observability/metrics/summary`))
  }

getMetricsSummary(): Observable<MetricsSummary> {
    return this.getObservabilityMetricsSummary()
  }

getQuarantinedMessages(queue?: string): Observable<QuarantinedMessagesResponse> {
    const params = queue ? `?queue=${encodeURIComponent(queue)}` : ''
    return this.http.get<QuarantinedMessagesResponse>(this.apiContext.buildUrl(`/api/v1/observability/poison-pills/quarantined${params}`))
  }

cleanupQuarantine(): Observable<{ status: string; count: number }> {
    return this.http.post<{ status: string; count: number }>(this.apiContext.buildUrl(`/api/v1/observability/poison-pills/cleanup`), {})
  }

getPoisonPillStats(queue?: string): Observable<PoisonPillStats> {
    const params = queue ? `?queue=${encodeURIComponent(queue)}` : ''
    return this.http.get<PoisonPillStats>(this.apiContext.buildUrl(`/api/v1/observability/poison-pills/stats${params}`))
  }

listGraphQuarantine(limit: number = 100, offset: number = 0, filters?: { type?: string; reason?: string; confidence_ge?: number }): Observable<GraphQuarantineListResponse> {
    const qs = new URLSearchParams()
    qs.set('limit', String(limit))
    qs.set('offset', String(offset))
    if (filters?.type) qs.set('type', filters.type)
    if (filters?.reason) qs.set('reason', filters.reason)
    if (typeof filters?.confidence_ge !== 'undefined') qs.set('confidence_ge', String(filters?.confidence_ge))
    return this.http.get<GraphQuarantineListResponse>(this.apiContext.buildUrl(`/api/v1/observability/graph/quarantine?${qs.toString()}`))
  }

promoteQuarantine(node_id: number): Observable<{ status: string; node_id: number }> {
    return this.http.post<{ status: string; node_id: number }>(this.apiContext.buildUrl(`/api/v1/observability/graph/quarantine/promote`), { node_id })
  }

rejectQuarantine(node_id: number, reason: string): Observable<{ status: string; node_id: number }> {
    return this.http.post<{ status: string; node_id: number }>(this.apiContext.buildUrl(`/api/v1/observability/graph/quarantine/reject`), { node_id, reason })
  }

registerSynonym(label: string, alias: string, canonical: string): Observable<{ status: string; synonym_id: number }> {
    return this.http.post<{ status: string; synonym_id: number }>(this.apiContext.buildUrl(`/api/v1/observability/graph/entities/synonym`), { label, alias, canonical })
  }

listAuditEvents(params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number } = {}): Observable<AuditEventsResponse> {
    const qs = new URLSearchParams()
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.tool) qs.set('tool', params.tool)
    if (params.status) qs.set('status', params.status)
    if (typeof params.start_ts !== 'undefined') qs.set('start_ts', String(params.start_ts))
    if (typeof params.end_ts !== 'undefined') qs.set('end_ts', String(params.end_ts))
    qs.set('limit', String(params.limit ?? 100))
    qs.set('offset', String(params.offset ?? 0))
    return this.http.get<AuditEventsResponse>(this.apiContext.buildUrl(`/api/v1/observability/audit/events?${qs.toString()}`))
  }

listPendingActions(params: {
    include_graph?: boolean;
    include_sql?: boolean;
    user_id?: string;
    pending_status?: string;
    limit?: number;
  } = {}): Observable<PendingAction[]> {
    const qs = new URLSearchParams()
    if (typeof params.include_graph !== 'undefined') qs.set('include_graph', String(params.include_graph))
    if (typeof params.include_sql !== 'undefined') qs.set('include_sql', String(params.include_sql))
    if (params.user_id) qs.set('user_id', params.user_id)
    if (params.pending_status) qs.set('pending_status', params.pending_status)
    if (typeof params.limit !== 'undefined') qs.set('limit', String(params.limit))
    const suffix = qs.toString() ? `?${qs.toString()}` : ''
    return this.http.get<PendingAction[]>(this.apiContext.buildUrl(`/api/v1/pending_actions/${suffix}`))
  }

approvePendingAction(action: PendingAction): Observable<PendingAction> {
    if (typeof action?.action_id === 'number') {
      return this.http.post<PendingAction>(
        this.apiContext.buildUrl(`/api/v1/pending_actions/action/${encodeURIComponent(String(action.action_id))}/approve`),
        {}
      )
    }
    if (!action?.thread_id) {
      throw new Error('Invalid pending action: missing action_id/thread_id')
    }
    return this.http.post<PendingAction>(
      this.apiContext.buildUrl(`/api/v1/pending_actions/${encodeURIComponent(action.thread_id)}/approve`),
      {}
    )
  }

rejectPendingAction(action: PendingAction): Observable<PendingAction> {
    if (typeof action?.action_id === 'number') {
      return this.http.post<PendingAction>(
        this.apiContext.buildUrl(`/api/v1/pending_actions/action/${encodeURIComponent(String(action.action_id))}/reject`),
        {}
      )
    }
    if (!action?.thread_id) {
      throw new Error('Invalid pending action: missing action_id/thread_id')
    }
    return this.http.post<PendingAction>(
      this.apiContext.buildUrl(`/api/v1/pending_actions/${encodeURIComponent(action.thread_id)}/reject`),
      {}
    )
  }

getReviewerMetrics(user_id: number, start_ts?: number, end_ts?: number): Observable<ReviewerMetricsResponse> {
    const qs = new URLSearchParams()
    qs.set('user_id', String(user_id))
    if (typeof start_ts !== 'undefined') qs.set('start_ts', String(start_ts))
    if (typeof end_ts !== 'undefined') qs.set('end_ts', String(end_ts))
    return this.http.get<ReviewerMetricsResponse>(this.apiContext.buildUrl(`/api/v1/observability/hitl/metrics/reviewer?${qs.toString()}`))
  }

getHitlReports(period: 'daily' | 'weekly' | 'monthly' = 'daily', start_ts?: number, end_ts?: number): Observable<PeriodReportResponse> {
    const qs = new URLSearchParams()
    qs.set('period', period)
    if (typeof start_ts !== 'undefined') qs.set('start_ts', String(start_ts))
    if (typeof end_ts !== 'undefined') qs.set('end_ts', String(end_ts))
    return this.http.get<PeriodReportResponse>(this.apiContext.buildUrl(`/api/v1/observability/hitl/reports?${qs.toString()}`))
  }

listConsents(user_id: number): Observable<ConsentsListResponse> {
    return this.http.get<ConsentsListResponse>(this.apiContext.buildUrl(`/api/v1/consents/?user_id=${encodeURIComponent(String(user_id))}`))
  }

grantConsent(user_id: number, scope: string, granted: boolean = true, expires_at?: string): Observable<{ status: string; scope: string }> {
    const body: Record<string, unknown> = { user_id: String(user_id), scope, granted: granted ? 'True' : 'False' }
    if (expires_at) body['expires_at'] = expires_at
    return this.http.post<{ status: string; scope: string }>(this.apiContext.buildUrl(`/api/v1/consents/`), body)
  }

revokeConsent(consent_id: number): Observable<{ status: string; consent_id: string }> {
    return this.http.post<{ status: string; consent_id: string }>(this.apiContext.buildUrl(`/api/v1/consents/${encodeURIComponent(String(consent_id))}/revoke`), {})
  }

exportAuditCSV(params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number }): Observable<string> {
    const qs = new URLSearchParams()
    if (params.user_id) qs.set('user_id', String(params.user_id))
    if (params.tool) qs.set('tool', String(params.tool))
    if (params.status) qs.set('status', String(params.status))
    if (params.start_ts != null) qs.set('start_ts', String(params.start_ts))
    if (params.end_ts != null) qs.set('end_ts', String(params.end_ts))
    if (params.limit != null) qs.set('limit', String(params.limit))
    if (params.offset != null) qs.set('offset', String(params.offset))
    return this.http.get(this.apiContext.buildUrl(`/api/v1/observability/audit/export?${qs.toString()}`), { responseType: 'text' })
  }

exportAuditEvents(
    format: 'csv' | 'json',
    params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number; fields?: string[] } = {}
  ): Observable<string> {
    const qs = new URLSearchParams()
    if (params.user_id) qs.set('user_id', String(params.user_id))
    if (params.tool) qs.set('tool', String(params.tool))
    if (params.status) qs.set('status', String(params.status))
    if (params.start_ts != null) qs.set('start_ts', String(params.start_ts))
    if (params.end_ts != null) qs.set('end_ts', String(params.end_ts))
    qs.set('limit', String(params.limit ?? 1000))
    qs.set('offset', String(params.offset ?? 0))
    qs.set('format', format)
    if (params.fields && params.fields.length) qs.set('fields', params.fields.join(','))
    return this.http.get(this.apiContext.buildUrl(`/api/v1/observability/audit/export?${qs.toString()}`), { responseType: 'text' })
  }

getReflexionSummary(limit: number = 10): Observable<PostSprintSummaryResponse> {
    const qs = new URLSearchParams({ limit: String(limit) })
    return this.http.get<PostSprintSummaryResponse>(this.apiContext.buildUrl(`/api/v1/reflexion/summary/post_sprint?${qs.toString()}`))
  }
}
</file>

<file path="app/services/domain/productivity-api-service.ts">
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { ProductivityLimitsStatusResponse, GoogleOAuthStartResponse, GoogleOAuthCallbackResponse, CalendarAddRequest, MailSendRequest, QueueAck } from '../../models';

@Injectable({ providedIn: 'root' })
export class ProductivityApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getProductivityLimitsStatus(user_id: number): Observable<ProductivityLimitsStatusResponse> {
    const headers = this.apiContext.headersFor(user_id)
    return this.http.get<ProductivityLimitsStatusResponse>(
      this.apiContext.buildUrl(`/api/v1/productivity/limits/status?user_id=${encodeURIComponent(String(user_id))}`),
      { headers }
    )
  }

getProductivityLimitsStatusSelf(): Observable<ProductivityLimitsStatusResponse> {
    return this.http.get<ProductivityLimitsStatusResponse>(
      this.apiContext.buildUrl(`/api/v1/productivity/limits/status`)
    )
  }

googleOAuthStart(user_id: number, scope: 'calendar' | 'mail' | 'notes' = 'calendar'): Observable<GoogleOAuthStartResponse> {
    const headers = this.apiContext.headersFor(user_id)
    const qs = new URLSearchParams({ user_id: String(user_id), scope })
    return this.http.get<GoogleOAuthStartResponse>(this.apiContext.buildUrl(`/api/v1/productivity/oauth/google/start?${qs.toString()}`), { headers })
  }

googleOAuthCallback(code: string, state: string): Observable<GoogleOAuthCallbackResponse> {
    return this.http.post<GoogleOAuthCallbackResponse>(this.apiContext.buildUrl(`/api/v1/productivity/oauth/google/callback`), { code, state })
  }

calendarAddEvent(req: CalendarAddRequest): Observable<QueueAck> {
    const headers = this.apiContext.headersFor(req.user_id)
    return this.http.post<QueueAck>(this.apiContext.buildUrl(`/api/v1/productivity/calendar/events/add`), req, { headers })
  }

mailSend(req: MailSendRequest): Observable<QueueAck> {
    const headers = this.apiContext.headersFor(req.user_id)
    return this.http.post<QueueAck>(this.apiContext.buildUrl(`/api/v1/productivity/mail/messages/send`), req, { headers })
  }
}
</file>

<file path="app/services/domain/system-api-service.ts">
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { SystemStatus, ServiceHealthResponse, QueueInfoResponse, SystemOverviewResponse, DbValidationResponse, WorkersStatusResponse, AutoAnalysisResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class SystemApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

health(): Observable<{ status: string }> {
    return this.http.get<{ status: string }>(this.apiContext.buildUrl(`/healthz`));
  }

getSystemStatus(): Observable<SystemStatus> {
    return this.http.get<SystemStatus>(this.apiContext.buildUrl(`/api/v1/system/status`), {
      headers: { 'ngsw-bypass': 'true' }
    });
  }

getServicesHealth(): Observable<ServiceHealthResponse> {
    return this.http.get<ServiceHealthResponse>(this.apiContext.buildUrl(`/api/v1/system/health/services`));
  }

getWorkersStatus(): Observable<WorkersStatusResponse> {
    return this.http.get<WorkersStatusResponse>(this.apiContext.buildUrl(`/api/v1/workers/status`));
  }

getQueueInfo(queueName: string): Observable<QueueInfoResponse> {
    return this.http.get<QueueInfoResponse>(
      this.apiContext.buildUrl(`/api/v1/tasks/queue/${encodeURIComponent(queueName)}`)
    );
  }

getSystemOverview(): Observable<SystemOverviewResponse> {
    return this.http.get<SystemOverviewResponse>(this.apiContext.buildUrl(`/api/v1/system/overview`), {
      headers: { 'ngsw-bypass': 'true' }
    });
  }

startAllWorkers(): Observable<{ status: string; workers: string[] }> {
    return this.http.post<{ status: string; workers: string[] }>(this.apiContext.buildUrl(`/api/v1/workers/start-all`), {});
  }

stopAllWorkers(): Observable<{ status: string; workers: string[] }> {
    return this.http.post<{ status: string; workers: string[] }>(this.apiContext.buildUrl(`/api/v1/workers/stop-all`), {});
  }

runAutoAnalysis(): Observable<AutoAnalysisResponse> {
    return this.http.get<AutoAnalysisResponse>(this.apiContext.buildUrl(`/api/v1/auto-analysis/health-check`))
  }

getSystemDbValidate(): Observable<DbValidationResponse> {
    return this.http.get<DbValidationResponse>(this.apiContext.buildUrl(`/api/v1/system/db/validate`))
  }
}
</file>

<file path="app/services/domain/tools-api-service.ts">
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { Tool, ToolListResponse, ToolStats } from '../../models';

@Injectable({ providedIn: 'root' })
export class ToolsApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getTools(category?: string, permissionLevel?: string, tags?: string): Observable<ToolListResponse> {
    const qs = new URLSearchParams()
    if (category) qs.set('category', category)
    if (permissionLevel) qs.set('permission_level', permissionLevel)
    if (tags) qs.set('tags', tags)
    return this.http.get<ToolListResponse>(this.apiContext.buildUrl(`/api/v1/tools/${qs.toString() ? '?' + qs.toString() : ''}`))
  }

getToolDetails(toolName: string): Observable<Tool> {
    return this.http.get<Tool>(this.apiContext.buildUrl(`/api/v1/tools/${encodeURIComponent(toolName)}`))
  }

getToolStats(): Observable<ToolStats> {
    return this.http.get<ToolStats>(this.apiContext.buildUrl(`/api/v1/tools/stats/usage`))
  }

getToolCategories(): Observable<{ categories: string[] }> {
    return this.http.get<{ categories: string[] }>(this.apiContext.buildUrl(`/api/v1/tools/categories/list`))
  }

getToolPermissions(): Observable<{ permission_levels: string[] }> {
    return this.http.get<{ permission_levels: string[] }>(this.apiContext.buildUrl(`/api/v1/tools/permissions/list`))
  }
}
</file>

<file path="app/services/domain/users-api-service.ts">
import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { UserRolesResponse, TokenResponse, UserStatusResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class UsersApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getUserRoles(user_id: number): Observable<UserRolesResponse> {
    return this.http.get<UserRolesResponse>(`/api/v1/users/${encodeURIComponent(String(user_id))}/roles`)
  }

issueToken(user_id: number, expires_in: number = 3600): Observable<TokenResponse> {
    const headers = this.apiContext.headersFor(user_id)
    return this.http.post<TokenResponse>(this.apiContext.buildUrl(`/api/v1/auth/token`), { user_id, expires_in }, { headers })
  }

getUserStatus(user_id: string): Observable<UserStatusResponse> {
    const qs = new URLSearchParams({ user_id })
    return this.http.get<UserStatusResponse>(this.apiContext.buildUrl(`/api/v1/system/status/user?${qs.toString()}`))
  }
}
</file>

<file path="app/services/domain/web-rtcapi-service.ts">
import { Injectable } from '@angular/core';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { JanusStatic, JanusSession, JanusPluginHandle } from '../../core/types';
declare const Janus: JanusStatic;

@Injectable({ providedIn: 'root' })
export class WebRTCApiService {
  constructor(
    private apiContext: ApiContextService
  ) {}

private _webrtcInitialized$ = new BehaviorSubject<{ status: string; error?: string } | null>(null)

private _janus?: JanusSession

private _pluginHandle?: JanusPluginHandle

private _serverUrl?: string

private _localStream$ = new BehaviorSubject<MediaStream | null>(null)

private _remoteStream$ = new BehaviorSubject<MediaStream | null>(null)

private _connectionState$ = new BehaviorSubject<string>('idle')

private _webrtcError$ = new Subject<string>()

webrtcInitialized$(): Observable<{ status: string; error?: string } | null> { return this._webrtcInitialized$.asObservable() }

localStream$(): Observable<MediaStream | null> { return this._localStream$.asObservable() }

remoteStream$(): Observable<MediaStream | null> { return this._remoteStream$.asObservable() }

connectionState$(): Observable<string> { return this._connectionState$.asObservable() }

webrtcErrors$(): Observable<string> { return this._webrtcError$.asObservable() }

initJanus(opts: { serverUrl: string; debug?: boolean }): Observable<{ status: string; error?: string }> {
    this._serverUrl = opts.serverUrl
    const out$ = new BehaviorSubject<{ status: string; error?: string }>({ status: 'initializing' })
    try {
      if (typeof Janus === 'undefined') {
        const err = 'JanusJS indisponível'
        this._webrtcInitialized$.next({ status: 'unavailable', error: err })
        out$.next({ status: 'unavailable', error: err })
        return out$.asObservable()
      }
      Janus.init({
        debug: !!opts.debug, callback: () => {
          out$.next({ status: 'initialized' })
          this._webrtcInitialized$.next({ status: 'initialized' })
          try {
            this._janus = new Janus({
              server: this._serverUrl || '',
              success: () => { this._connectionState$.next('session_ready') },
              error: (e: unknown) => { const msg = String(e); this._webrtcError$.next(msg); this._connectionState$.next('session_error'); },
              destroyed: () => { this._connectionState$.next('session_destroyed') }
            })
          } catch (e) {
            const msg = String(e)
            this._webrtcError$.next(msg)
            this._connectionState$.next('session_error')
          }
        }
      })
    } catch (e) {
      const msg = String(e)
      this._webrtcInitialized$.next({ status: 'failed', error: msg })
      out$.next({ status: 'failed', error: msg })
    }
    return out$.asObservable()
  }

attachPlugin(plugin: 'videoroom' | 'videocall', opaqueId?: string): Observable<{ status: string; error?: string }> {
    const out$ = new BehaviorSubject<{ status: string; error?: string }>({ status: 'attaching' })
    if (!this._janus) { out$.next({ status: 'failed', error: 'JanusSession ausente' }); return out$.asObservable() }
    try {
      const pluginName = plugin === 'videocall' ? 'janus.plugin.videocall' : 'janus.plugin.videoroom'
      this._janus.attach({
        plugin: pluginName,
        opaqueId,
        success: (handle: JanusPluginHandle) => {
          this._pluginHandle = handle
          out$.next({ status: 'attached' })
          this._connectionState$.next('attached')
        },
        error: (cause: unknown) => {
          const msg = String(cause)
          this._webrtcError$.next(msg)
          out$.next({ status: 'failed', error: msg })
          this._connectionState$.next('attach_error')
        },
        webrtcState: (on: boolean) => {
          this._connectionState$.next(on ? 'webrtc_up' : 'webrtc_down')
        },
        onlocalstream: (stream: MediaStream) => {
          this._localStream$.next(stream)
        },
        onremotestream: (stream: MediaStream) => {
          this._remoteStream$.next(stream)
        }
      })
    } catch (e) {
      const msg = String(e)
      this._webrtcError$.next(msg)
      out$.next({ status: 'failed', error: msg })
    }
    return out$.asObservable()
  }

createPeerConnection(iceServers?: RTCIceServer[]): RTCPeerConnection {
    const pc = new RTCPeerConnection({ iceServers })
    pc.oniceconnectionstatechange = () => { this._connectionState$.next(pc.iceConnectionState) }
    pc.ontrack = (ev) => {
      const [stream] = ev.streams
      if (stream) this._remoteStream$.next(stream)
    }
    return pc
  }

startLocalMedia(constraints: MediaStreamConstraints = { audio: true, video: true }): Promise<MediaStream> {
    return navigator.mediaDevices.getUserMedia(constraints)
      .then((stream) => { this._localStream$.next(stream); return stream })
      .catch((e) => { const msg = String(e); this._webrtcError$.next(msg); throw e })
  }

stopLocalMedia(): void {
    const s = this._localStream$.getValue()
    if (!s) return
    s.getTracks().forEach(t => t.stop())
    this._localStream$.next(null)
  }
}
</file>

<file path="app/services/api-context.service.ts">
import { Injectable } from '@angular/core';
import { API_BASE_URL } from './api.config';

@Injectable({ providedIn: 'root' })
export class ApiContextService {
  private _projectId?: string;
  private _sessionId?: string;
  private _conversationId?: string;
  private _persona?: string;
  private _role?: string;
  private _priority?: string;

  public buildUrl(path: string): string {
    const p = String(path || '');
    if (p === '/healthz') return p;
    if (p.startsWith('/api/')) return p;
    if (p.startsWith('/v1/')) return `${API_BASE_URL}${p}`;
    return `${API_BASE_URL}${p.startsWith('/') ? '' : '/'}${p}`;
  }

  private _reqId(): string {
    const s = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx';
    return s.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  private _traceparent(): string {
    const hex = (size: number) => {
      let out = '';
      for (let i = 0; i < size; i += 1) {
        out += Math.floor(Math.random() * 16).toString(16);
      }
      return out;
    };
    return `00-${hex(32)}-${hex(16)}-01`;
  }

  setProjectId(project_id?: string) { this._projectId = project_id || undefined; }
  setSessionId(session_id?: string) { this._sessionId = session_id || undefined; }
  setConversationId(conversation_id?: string) { this._conversationId = conversation_id || undefined; }
  setPersona(persona?: string) { this._persona = persona || undefined; }
  setRole(role?: string) { this._role = role || undefined; }
  setPriority(priority?: string) { this._priority = priority || undefined; }
  clearContext() { this._projectId = undefined; this._sessionId = undefined; this._conversationId = undefined; }

  public headersFor(userId?: number | string): Record<string, string> {
    const h: Record<string, string> = {
      'X-Request-ID': this._reqId(),
      traceparent: this._traceparent(),
    };
    if (typeof userId !== 'undefined') h['X-User-Id'] = String(userId);
    if (this._projectId) h['X-Project-Id'] = this._projectId;
    if (this._sessionId) h['X-Session-Id'] = this._sessionId;
    if (this._conversationId) h['X-Conversation-Id'] = this._conversationId;
    if (this._persona) h['X-Persona'] = this._persona;
    if (this._role) h['X-Role'] = this._role;
    if (this._priority) h['X-Priority'] = this._priority;
    return h;
  }
}
</file>

<file path="app/services/api.config.ts">
export const API_BASE_URL: string = import.meta.env?.VITE_API_BASE_URL ?? '/api';
export const AUTH_TOKEN_KEY: string = import.meta.env?.VITE_AUTH_TOKEN_KEY ?? 'JANUS_AUTH_TOKEN';
const env = (import.meta as unknown as { env: Record<string, string> }).env || {};
export const FEATURE_SSE: boolean = (env['VITE_FEATURE_SSE'] ?? 'true') === 'true';
export const UX_METRICS_SAMPLING: number = Number(env['VITE_UX_METRICS_SAMPLING'] ?? '0.3');
export const SSE_RETRY_MAX_SECONDS: number = Number(env['VITE_SSE_RETRY_MAX_SECONDS'] ?? '30');
export const SSE_MAX_RETRIES: number = Number(env['VITE_SSE_MAX_RETRIES'] ?? '8');
export const AUTH_OPTIONAL: boolean = (env['VITE_AUTH_OPTIONAL'] ?? 'false') === 'true';
export const VISITOR_MODE_KEY: string = env['VITE_VISITOR_MODE_KEY'] ?? 'JANUS_VISITOR_MODE';
</file>

<file path="app/services/api.service.ts">
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = this.getApiUrl();

  private getApiUrl(): string {
    // Use Tailscale URL if enabled, otherwise use default
    if (environment.tailscale?.enabled && environment.tailscale?.apiUrl) {
      return environment.tailscale.apiUrl;
    }
    return environment.apiUrl;
  }

  private buildUrl(endpoint: string): string {
    // Remove leading slash if present
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
    return `${this.apiUrl}/${cleanEndpoint}`;
  }

  get<T>(url: string, options?: object): Observable<T> {
    return this.http.get<T>(this.buildUrl(url), options);
  }

  post<T>(url: string, body: unknown, options?: object): Observable<T> {
    return this.http.post<T>(this.buildUrl(url), body, options);
  }

  put<T>(url: string, body: unknown, options?: object): Observable<T> {
    return this.http.put<T>(this.buildUrl(url), body, options);
  }

  delete<T>(url: string, options?: object): Observable<T> {
    return this.http.delete<T>(this.buildUrl(url), options);
  }

  // Exemplo: healthcheck do backend
  health(): Observable<string> {
    return this.http.get(this.buildUrl('/healthz'), { responseType: 'text' });
  }

  // Health check detalhado com informações do sistema
  detailedHealth(): Observable<any> {
    return this.http.get(this.buildUrl('/health'));
  }
}
</file>

<file path="app/services/auth.utils.ts">
import { AUTH_TOKEN_KEY } from './api.config'

export function decodeTokenUserId(token: string | null): number | null {
  if (!token) return null
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    const body = parts[0]
    const padded = body + '='.repeat((4 - (body.length % 4)) % 4)
    const jsonStr = atob(padded.replace(/-/g, '+').replace(/_/g, '/'))
    const payload = JSON.parse(jsonStr)
    const uid = Number(payload?.user_id)
    return Number.isFinite(uid) ? uid : null
  } catch {
    return null
  }
}

export function getStoredAuthToken(): string | null {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY) || sessionStorage.getItem(AUTH_TOKEN_KEY)
  } catch {
    return null
  }
}

export function storeAuthToken(token: string, rememberSession: boolean): void {
  try {
    if (rememberSession) {
      localStorage.setItem(AUTH_TOKEN_KEY, token)
      sessionStorage.removeItem(AUTH_TOKEN_KEY)
      return
    }
    sessionStorage.setItem(AUTH_TOKEN_KEY, token)
    localStorage.removeItem(AUTH_TOKEN_KEY)
  } catch {
    // no-op
  }
}

export function clearStoredAuthToken(): void {
  try {
    localStorage.removeItem(AUTH_TOKEN_KEY)
    sessionStorage.removeItem(AUTH_TOKEN_KEY)
  } catch {
    // no-op
  }
}

export function decodeTokenExp(token: string | null): number | null {
  if (!token) return null
  try {
    const parts = token.split('.')
    if (parts.length < 2) return null
    const body = parts[0]
    const padded = body + '='.repeat((4 - (body.length % 4)) % 4)
    const jsonStr = atob(padded.replace(/-/g, '+').replace(/_/g, '/'))
    const payload = JSON.parse(jsonStr)
    const exp = Number(payload?.exp)
    return Number.isFinite(exp) ? exp : null
  } catch {
    return null
  }
}
</file>

<file path="app/services/auto-analysis.service.ts">
import { Injectable } from '@angular/core'
import { HttpClient } from '@angular/common/http'
import { Observable } from 'rxjs'
import { API_BASE_URL } from './api.config'

export interface HealthInsight {
  issue: string
  severity: 'low' | 'medium' | 'high'
  suggestion: string
  estimated_impact: string
}

export interface AutoAnalysisResponse {
  timestamp: string
  overall_health: 'healthy' | 'warning' | 'critical' | 'unknown'
  insights: HealthInsight[]
  fun_fact: string
  total_memories?: number
  session_duration?: string
  efficiency_score?: number
}

@Injectable({ providedIn: 'root' })
export class AutoAnalysisService {
  constructor(private http: HttpClient) { }

  /**
   * Pergunta ao Janus: "Como você está se saindo?"
   * Retorna uma análise simples e útil sobre o próprio sistema.
   */
  getHealthCheck(): Observable<AutoAnalysisResponse> {
    return this.http.get<AutoAnalysisResponse>(
      `${API_BASE_URL}/v1/auto-analysis/health-check`
    )
  }
}
</file>

<file path="app/services/backend-api.service.ts">
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiContextService } from './api-context.service';
import { SystemApiService } from './domain/system-api-service';
import { ChatApiService } from './domain/chat-api-service';
import { KnowledgeApiService } from './domain/knowledge-api-service';
import { DocumentsApiService } from './domain/documents-api-service';
import { AutonomyApiService } from './domain/autonomy-api-service';
import { ObservabilityApiService } from './domain/observability-api-service';
import { ToolsApiService } from './domain/tools-api-service';
import { WebRTCApiService } from './domain/web-rtcapi-service';
import { LlmApiService } from './domain/llm-api-service';
import { MemoryApiService } from './domain/memory-api-service';
import { ProductivityApiService } from './domain/productivity-api-service';
import { UsersApiService } from './domain/users-api-service';
import { ContextApiService } from './domain/context-api-service';
import { ExperimentApiService } from './domain/experiment-api-service';
import { GraphApiService } from './domain/graph-api-service';
import { FeedbackApiService } from './domain/feedback-api-service';

import { MailSendRequest, Citation, MetricsSummary, Tool, KnowledgeSpaceConsolidationResponse, KnowledgeHealthDetailedResponse, AdminBacklogSprintType, ReviewerMetricsResponse, CircuitBreakerStatus, ChatMessageResponse, AdminBacklogSyncResponse, UserRolesResponse, UploadResponse, ChatStudyJobResponse, KnowledgeSpaceListResponse, FeedbackQuickRequest, AutonomyPlanResponse, ServiceHealthResponse, MetaAgentLatestReportResponse, KnowledgeHealthResponse, AssignmentResponse, TraceStep, DbValidationResponse, RagSearchResponse, RagUserChatV2Response, SelfStudyStatusResponse, KnowledgeSpace, MemoryItem, ChatMessage, RagUserChatResponse, PendingAction, AutonomyStartRequest, FeedbackSubmitResponse, WebCacheStatus, AutonomyStatusResponse, LLMCacheStatusResponse, DeploymentStageResponse, DocListResponse, KnowledgeSpaceCreateRequest, SelfStudyRun, GoogleOAuthCallbackResponse, GraphQuarantineListResponse, GPUUsageResponse, ChatStartResponse, AutoAnalysisResponse, GoogleOAuthStartResponse, ConsentsListResponse, FeedbackQuickResponse, AuditEventsResponse, DeploymentPublishResponse, ContextualGraphResponse, ObservabilitySystemHealth, PostSprintSummaryResponse, TokenResponse, AdminCodeQaResponse, PeriodReportResponse, WebSearchResult, ToolStats, GenerativeMemoryItem, QueueAck, KnowledgeStats, ContextInfo, KnowledgeSpaceAttachRequest, UserPreferenceMemoryItem, WorkersStatusResponse, KnowledgeSpaceStatus, ChatHistoryResponse, DocSearchResponse, GoalCreateRequest, AutonomyPolicyUpdateRequest, RagHybridResponse, QuarantinedMessagesResponse, UserStatusResponse, ProductivityLimitsStatusResponse, SystemStatus, ConversationsListResponse, MetaAgentHeartbeatStatus, ABExperimentSetResponse, QueueInfoResponse, Goal, ToolListResponse, PoisonPillStats, KnowledgeSpaceQueryResponse, GPUBudgetResponse, LLMProvidersResponse, SystemOverviewResponse, EntityRelationshipsResponse, ExperimentWinnerResponse, CalendarAddRequest, LLMSubsystemHealth } from '../models';
export * from '../models';

@Injectable({ providedIn: 'root' })
export class BackendApiService {
  constructor(
    private apiContext: ApiContextService,
    private systemApiService: SystemApiService,
    private chatApiService: ChatApiService,
    private knowledgeApiService: KnowledgeApiService,
    private documentsApiService: DocumentsApiService,
    private autonomyApiService: AutonomyApiService,
    private observabilityApiService: ObservabilityApiService,
    private toolsApiService: ToolsApiService,
    private webRTCApiService: WebRTCApiService,
    private llmApiService: LlmApiService,
    private memoryApiService: MemoryApiService,
    private productivityApiService: ProductivityApiService,
    private usersApiService: UsersApiService,
    private contextApiService: ContextApiService,
    private experimentApiService: ExperimentApiService,
    private graphApiService: GraphApiService,
    private feedbackApiService: FeedbackApiService
  ) {}

  buildUrl(...args: any[]): any { return (this.apiContext as any).buildUrl(...args); }
  headersFor(...args: any[]): any { return (this.apiContext as any).headersFor(...args); }
  setProjectId(...args: any[]): void { (this.apiContext as any).setProjectId(...args); }
  setSessionId(...args: any[]): void { (this.apiContext as any).setSessionId(...args); }
  setConversationId(...args: any[]): void { (this.apiContext as any).setConversationId(...args); }
  setPersona(...args: any[]): void { (this.apiContext as any).setPersona(...args); }
  setRole(...args: any[]): void { (this.apiContext as any).setRole(...args); }
  setPriority(...args: any[]): void { (this.apiContext as any).setPriority(...args); }
  clearContext(...args: any[]): void { (this.apiContext as any).clearContext(...args); }
  getConversationTrace(conversationId: string): Observable<TraceStep[]> {
    return this.chatApiService.getConversationTrace(conversationId);
  }

  getContextualGraph(query?: string, conversationId?: string, hops: number = 1): Observable<ContextualGraphResponse> {
    return this.graphApiService.getContextualGraph(query, conversationId, hops);
  }

  health(): Observable<{ status: string }> {
    return this.systemApiService.health();
  }

  getSystemStatus(): Observable<SystemStatus> {
    return this.systemApiService.getSystemStatus();
  }

  getServicesHealth(): Observable<ServiceHealthResponse> {
    return this.systemApiService.getServicesHealth();
  }

  getWorkersStatus(): Observable<WorkersStatusResponse> {
    return this.systemApiService.getWorkersStatus();
  }

  getQueueInfo(queueName: string): Observable<QueueInfoResponse> {
    return this.systemApiService.getQueueInfo(queueName);
  }

  getSystemOverview(): Observable<SystemOverviewResponse> {
    return this.systemApiService.getSystemOverview();
  }

  getMetaAgentLatestReport(): Observable<MetaAgentLatestReportResponse> {
    return this.autonomyApiService.getMetaAgentLatestReport();
  }

  getMetaAgentHeartbeatStatus(): Observable<MetaAgentHeartbeatStatus> {
    return this.autonomyApiService.getMetaAgentHeartbeatStatus();
  }

  webrtcInitialized$(): Observable<{ status: string; error?: string } | null> {
    return this.webRTCApiService.webrtcInitialized$();
  }

  localStream$(): Observable<MediaStream | null> {
    return this.webRTCApiService.localStream$();
  }

  remoteStream$(): Observable<MediaStream | null> {
    return this.webRTCApiService.remoteStream$();
  }

  connectionState$(): Observable<string> {
    return this.webRTCApiService.connectionState$();
  }

  webrtcErrors$(): Observable<string> {
    return this.webRTCApiService.webrtcErrors$();
  }

  initJanus(opts: { serverUrl: string; debug?: boolean }): Observable<{ status: string; error?: string }> {
    return this.webRTCApiService.initJanus(opts);
  }

  attachPlugin(plugin: 'videoroom' | 'videocall', opaqueId?: string): Observable<{ status: string; error?: string }> {
    return this.webRTCApiService.attachPlugin(plugin, opaqueId);
  }

  createPeerConnection(iceServers?: RTCIceServer[]): RTCPeerConnection {
    return this.webRTCApiService.createPeerConnection(iceServers);
  }

  startLocalMedia(constraints: MediaStreamConstraints = { audio: true, video: true }): Promise<MediaStream> {
    return this.webRTCApiService.startLocalMedia(constraints);
  }

  stopLocalMedia(): void {
    return this.webRTCApiService.stopLocalMedia();
  }

  startAllWorkers(): Observable<{ status: string; workers: string[] }> {
    return this.systemApiService.startAllWorkers();
  }

  stopAllWorkers(): Observable<{ status: string; workers: string[] }> {
    return this.systemApiService.stopAllWorkers();
  }

  startAutonomy(req: AutonomyStartRequest): Observable<{ status: string; interval_seconds: number }> {
    return this.autonomyApiService.startAutonomy(req);
  }

  stopAutonomy(): Observable<{ status: string }> {
    return this.autonomyApiService.stopAutonomy();
  }

  getAutonomyStatus(): Observable<AutonomyStatusResponse> {
    return this.autonomyApiService.getAutonomyStatus();
  }

  getAutonomyPlan(): Observable<AutonomyPlanResponse> {
    return this.autonomyApiService.getAutonomyPlan();
  }

  updateAutonomyPlan(plan: { tool: string; args: Record<string, unknown> }[]): Observable<{ status: string; steps_count: number }> {
    return this.autonomyApiService.updateAutonomyPlan(plan);
  }

  updateAutonomyPolicy(req: AutonomyPolicyUpdateRequest): Observable<{ status: string; policy: Record<string, unknown> }> {
    return this.autonomyApiService.updateAutonomyPolicy(req);
  }

  runAutoAnalysis(): Observable<AutoAnalysisResponse> {
    return this.systemApiService.runAutoAnalysis();
  }

  listLLMProviders(): Observable<LLMProvidersResponse> {
    return this.llmApiService.listLLMProviders();
  }

  getLLMHealth(): Observable<LLMSubsystemHealth> {
    return this.llmApiService.getLLMHealth();
  }

  getLLMCacheStatus(): Observable<LLMCacheStatusResponse> {
    return this.llmApiService.getLLMCacheStatus();
  }

  getLLMCircuitBreakers(): Observable<CircuitBreakerStatus[]> {
    return this.llmApiService.getLLMCircuitBreakers();
  }

  getObservabilitySystemHealth(): Observable<ObservabilitySystemHealth> {
    return this.observabilityApiService.getObservabilitySystemHealth();
  }

  getObservabilityMetricsSummary(): Observable<MetricsSummary> {
    return this.observabilityApiService.getObservabilityMetricsSummary();
  }

  getMetricsSummary(): Observable<MetricsSummary> {
    return this.observabilityApiService.getMetricsSummary();
  }

  getBudgetSummary(): Observable<any> {
    return this.llmApiService.getBudgetSummary();
  }

  getQuarantinedMessages(queue?: string): Observable<QuarantinedMessagesResponse> {
    return this.observabilityApiService.getQuarantinedMessages(queue);
  }

  cleanupQuarantine(): Observable<{ status: string; count: number }> {
    return this.observabilityApiService.cleanupQuarantine();
  }

  getPoisonPillStats(queue?: string): Observable<PoisonPillStats> {
    return this.observabilityApiService.getPoisonPillStats(queue);
  }

  listGraphQuarantine(limit: number = 100, offset: number = 0, filters?: { type?: string; reason?: string; confidence_ge?: number }): Observable<GraphQuarantineListResponse> {
    return this.observabilityApiService.listGraphQuarantine(limit, offset, filters);
  }

  promoteQuarantine(node_id: number): Observable<{ status: string; node_id: number }> {
    return this.observabilityApiService.promoteQuarantine(node_id);
  }

  rejectQuarantine(node_id: number, reason: string): Observable<{ status: string; node_id: number }> {
    return this.observabilityApiService.rejectQuarantine(node_id, reason);
  }

  registerSynonym(label: string, alias: string, canonical: string): Observable<{ status: string; synonym_id: number }> {
    return this.observabilityApiService.registerSynonym(label, alias, canonical);
  }

  listAuditEvents(params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number } = {}): Observable<AuditEventsResponse> {
    return this.observabilityApiService.listAuditEvents(params);
  }

  listPendingActions(params: {
    include_graph?: boolean;
    include_sql?: boolean;
    user_id?: string;
    pending_status?: string;
    limit?: number;
  } = {}): Observable<PendingAction[]> {
    return this.observabilityApiService.listPendingActions(params);
  }

  approvePendingAction(action: PendingAction): Observable<PendingAction> {
    return this.observabilityApiService.approvePendingAction(action);
  }

  rejectPendingAction(action: PendingAction): Observable<PendingAction> {
    return this.observabilityApiService.rejectPendingAction(action);
  }

  getReviewerMetrics(user_id: number, start_ts?: number, end_ts?: number): Observable<ReviewerMetricsResponse> {
    return this.observabilityApiService.getReviewerMetrics(user_id, start_ts, end_ts);
  }

  getHitlReports(period: 'daily' | 'weekly' | 'monthly' = 'daily', start_ts?: number, end_ts?: number): Observable<PeriodReportResponse> {
    return this.observabilityApiService.getHitlReports(period, start_ts, end_ts);
  }

  listConsents(user_id: number): Observable<ConsentsListResponse> {
    return this.observabilityApiService.listConsents(user_id);
  }

  grantConsent(user_id: number, scope: string, granted: boolean = true, expires_at?: string): Observable<{ status: string; scope: string }> {
    return this.observabilityApiService.grantConsent(user_id, scope, granted, expires_at);
  }

  revokeConsent(consent_id: number): Observable<{ status: string; consent_id: string }> {
    return this.observabilityApiService.revokeConsent(consent_id);
  }

  getCurrentContext(): Observable<ContextInfo> {
    return this.contextApiService.getCurrentContext();
  }

  searchWeb(query: string, max_results: number = 5, search_depth: 'basic' | 'advanced' = 'basic'): Observable<WebSearchResult> {
    return this.contextApiService.searchWeb(query, max_results, search_depth);
  }

  getWebCacheStatus(): Observable<WebCacheStatus> {
    return this.contextApiService.getWebCacheStatus();
  }

  invalidateWebCache(query?: string): Observable<Record<string, unknown>> {
    return this.contextApiService.invalidateWebCache(query);
  }

  startChat(title?: string, persona?: string, user_id?: string, project_id?: string): Observable<ChatStartResponse> {
    return this.chatApiService.startChat(title, persona, user_id, project_id);
  }

  sendChatMessage(conversation_id: string, content: string, role: string = 'orchestrator', priority: string = 'fast_and_cheap', timeout_seconds?: number, user_id?: string, project_id?: string, knowledge_space_id?: string): Observable<ChatMessageResponse & { citations?: Citation[] }> {
    return this.chatApiService.sendChatMessage(conversation_id, content, role, priority, timeout_seconds, user_id, project_id, knowledge_space_id);
  }

  getChatStudyJob(jobId: string): Observable<ChatStudyJobResponse> {
    return this.chatApiService.getChatStudyJob(jobId);
  }

  getChatHistory(conversation_id: string): Observable<ChatHistoryResponse> {
    return this.chatApiService.getChatHistory(conversation_id);
  }

  getChatHistoryPaginated(conversation_id: string, params: {
    limit?: number;
    offset?: number;
    before_ts?: number;
    after_ts?: number;
  } = {}): Observable<{
    conversation_id: string;
    messages: ChatMessage[];
    total_count: number;
    has_more: boolean;
    next_offset?: number;
    limit: number;
    offset: number;
  }> {
    return this.chatApiService.getChatHistoryPaginated(conversation_id, params);
  }

  checkChatHealth(): Observable<{ status: string, repository_accessible: boolean, total_conversations: number }> {
    return this.chatApiService.checkChatHealth();
  }

  listConversations(params: { user_id?: string; project_id?: string; limit?: number } = {}): Observable<ConversationsListResponse> {
    return this.chatApiService.listConversations(params);
  }

  renameConversation(conversation_id: string, new_title: string): Observable<{ status: string }> {
    return this.chatApiService.renameConversation(conversation_id, new_title);
  }

  deleteConversation(conversation_id: string): Observable<{ status: string }> {
    return this.chatApiService.deleteConversation(conversation_id);
  }

  normalizeChatText(value: unknown): string {
    return this.chatApiService.normalizeChatText(value);
  }

  getUserRoles(user_id: number): Observable<UserRolesResponse> {
    return this.usersApiService.getUserRoles(user_id);
  }

  issueToken(user_id: number, expires_in: number = 3600): Observable<TokenResponse> {
    return this.usersApiService.issueToken(user_id, expires_in);
  }

  getProductivityLimitsStatus(user_id: number): Observable<ProductivityLimitsStatusResponse> {
    return this.productivityApiService.getProductivityLimitsStatus(user_id);
  }

  getProductivityLimitsStatusSelf(): Observable<ProductivityLimitsStatusResponse> {
    return this.productivityApiService.getProductivityLimitsStatusSelf();
  }

  googleOAuthStart(user_id: number, scope: 'calendar' | 'mail' | 'notes' = 'calendar'): Observable<GoogleOAuthStartResponse> {
    return this.productivityApiService.googleOAuthStart(user_id, scope);
  }

  googleOAuthCallback(code: string, state: string): Observable<GoogleOAuthCallbackResponse> {
    return this.productivityApiService.googleOAuthCallback(code, state);
  }

  calendarAddEvent(req: CalendarAddRequest): Observable<QueueAck> {
    return this.productivityApiService.calendarAddEvent(req);
  }

  mailSend(req: MailSendRequest): Observable<QueueAck> {
    return this.productivityApiService.mailSend(req);
  }

  getExperimentWinner(experiment_id: number, metric_name: string = 'accuracy'): Observable<ExperimentWinnerResponse> {
    return this.experimentApiService.getExperimentWinner(experiment_id, metric_name);
  }

  assignUserToExperiment(experiment_id: number, user_id: string): Observable<AssignmentResponse> {
    return this.experimentApiService.assignUserToExperiment(experiment_id, user_id);
  }

  submitExperimentFeedback(experiment_id: number, user_id: string, rating: number, notes?: string): Observable<FeedbackSubmitResponse> {
    return this.experimentApiService.submitExperimentFeedback(experiment_id, user_id, rating, notes);
  }

  getExperimentFeedbackStats(experiment_id: number): Observable<Record<string, unknown>> {
    return this.experimentApiService.getExperimentFeedbackStats(experiment_id);
  }

  stageDeployment(model_id: string, rollout_percent: number): Observable<DeploymentStageResponse> {
    return this.llmApiService.stageDeployment(model_id, rollout_percent);
  }

  publishDeployment(model_id: string): Observable<DeploymentPublishResponse> {
    return this.llmApiService.publishDeployment(model_id);
  }

  rollbackDeployment(model_id: string): Observable<DeploymentPublishResponse> {
    return this.llmApiService.rollbackDeployment(model_id);
  }

  precheckDeployment(model_id: string): Observable<{ precheck_passed: boolean; bias_score: number; safety_warnings?: string | null }> {
    return this.llmApiService.precheckDeployment(model_id);
  }

  getGPUUsage(user_id: string): Observable<GPUUsageResponse> {
    return this.llmApiService.getGPUUsage(user_id);
  }

  setGPUBudget(user_id: string, budget: number): Observable<GPUBudgetResponse> {
    return this.llmApiService.setGPUBudget(user_id, budget);
  }

  setLLMABExperiment(experiment_id: number): Observable<ABExperimentSetResponse> {
    return this.llmApiService.setLLMABExperiment(experiment_id);
  }

  getUserStatus(user_id: string): Observable<UserStatusResponse> {
    return this.usersApiService.getUserStatus(user_id);
  }

  exportAuditCSV(params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number }): Observable<string> {
    return this.observabilityApiService.exportAuditCSV(params);
  }

  exportAuditEvents(format: 'csv' | 'json', params: { user_id?: string; tool?: string; status?: string; start_ts?: number; end_ts?: number; limit?: number; offset?: number; fields?: string[] } = {}): Observable<string> {
    return this.observabilityApiService.exportAuditEvents(format, params);
  }

  linkUrl(conversation_id: string, url: string, user_id?: string): Observable<UploadResponse> {
    return this.documentsApiService.linkUrl(conversation_id, url, user_id);
  }

  listGoals(status?: string): Observable<Goal[]> {
    return this.autonomyApiService.listGoals(status);
  }

  getGoal(goal_id: string): Observable<Goal> {
    return this.autonomyApiService.getGoal(goal_id);
  }

  createGoal(req: GoalCreateRequest): Observable<Goal> {
    return this.autonomyApiService.createGoal(req);
  }

  updateGoalStatus(goal_id: string, status: 'pending' | 'in_progress' | 'completed' | 'failed'): Observable<Goal> {
    return this.autonomyApiService.updateGoalStatus(goal_id, status);
  }

  deleteGoal(goal_id: string): Observable<{ status: string; goal_id: string }> {
    return this.autonomyApiService.deleteGoal(goal_id);
  }

  syncAutonomyAdminBacklog(): Observable<AdminBacklogSyncResponse> {
    return this.autonomyApiService.syncAutonomyAdminBacklog();
  }

  getAutonomyAdminBoard(params: { status?: string; limit?: number } = {}): Observable<{ items: AdminBacklogSprintType[] }> {
    return this.autonomyApiService.getAutonomyAdminBoard(params);
  }

  runAutonomyAdminSelfStudy(req: { mode: 'incremental' | 'full'; reason?: string }): Observable<{ status: string; run_id: number }> {
    return this.autonomyApiService.runAutonomyAdminSelfStudy(req);
  }

  getAutonomyAdminSelfStudyStatus(): Observable<SelfStudyStatusResponse> {
    return this.autonomyApiService.getAutonomyAdminSelfStudyStatus();
  }

  listAutonomyAdminSelfStudyRuns(limit: number = 20): Observable<{ items: SelfStudyRun[] }> {
    return this.autonomyApiService.listAutonomyAdminSelfStudyRuns(limit);
  }

  askAutonomyAdminCodeQa(req: { question: string; limit?: number; citation_limit?: number }): Observable<AdminCodeQaResponse> {
    return this.autonomyApiService.askAutonomyAdminCodeQa(req);
  }

  getTools(category?: string, permissionLevel?: string, tags?: string): Observable<ToolListResponse> {
    return this.toolsApiService.getTools(category, permissionLevel, tags);
  }

  getToolDetails(toolName: string): Observable<Tool> {
    return this.toolsApiService.getToolDetails(toolName);
  }

  getToolStats(): Observable<ToolStats> {
    return this.toolsApiService.getToolStats();
  }

  getToolCategories(): Observable<{ categories: string[] }> {
    return this.toolsApiService.getToolCategories();
  }

  getToolPermissions(): Observable<{ permission_levels: string[] }> {
    return this.toolsApiService.getToolPermissions();
  }

  getMemoryTimeline(params: {
    start_date?: string
    end_date?: string
    query?: string
    limit?: number
    min_score?: number
    user_id?: string
    conversation_id?: string
  } = {}): Observable<MemoryItem[]> {
    return this.memoryApiService.getMemoryTimeline(params);
  }

  getGenerativeMemories(query: string, limit: number = 10, filters: { type?: string; userId?: string; conversationId?: string } = {}): Observable<GenerativeMemoryItem[]> {
    return this.memoryApiService.getGenerativeMemories(query, limit, filters);
  }

  addGenerativeMemory(content: string, opts: { importance?: number; type?: string; userId?: string; conversationId?: string; sessionId?: string } = {}): Observable<GenerativeMemoryItem> {
    return this.memoryApiService.addGenerativeMemory(content, opts);
  }

  getUserPreferences(params: {
    userId?: string
    conversationId?: string
    query?: string
    limit?: number
    activeOnly?: boolean
  } = {}): Observable<UserPreferenceMemoryItem[]> {
    return this.memoryApiService.getUserPreferences(params);
  }

  listDocuments(conversationId?: string, userId?: string): Observable<DocListResponse> {
    return this.documentsApiService.listDocuments(conversationId, userId);
  }

  uploadDocument(file: File, conversationId?: string, userId?: string): Observable<{ progress?: number; response?: UploadResponse }> {
    return this.documentsApiService.uploadDocument(file, conversationId, userId);
  }

  searchDocuments(query: string, minScore?: number, docId?: string, userId?: string): Observable<DocSearchResponse> {
    return this.documentsApiService.searchDocuments(query, minScore, docId, userId);
  }

  deleteDocument(docId: string, userId?: string): Observable<{ status: string; doc_id: string }> {
    return this.documentsApiService.deleteDocument(docId, userId);
  }

  createKnowledgeSpace(payload: KnowledgeSpaceCreateRequest): Observable<KnowledgeSpace> {
    return this.knowledgeApiService.createKnowledgeSpace(payload);
  }

  listKnowledgeSpaces(userId?: string, limit: number = 100): Observable<KnowledgeSpaceListResponse> {
    return this.knowledgeApiService.listKnowledgeSpaces(userId, limit);
  }

  getKnowledgeSpaceStatus(knowledgeSpaceId: string, userId?: string): Observable<KnowledgeSpaceStatus> {
    return this.knowledgeApiService.getKnowledgeSpaceStatus(knowledgeSpaceId, userId);
  }

  attachDocumentToKnowledgeSpace(knowledgeSpaceId: string, docId: string, payload: KnowledgeSpaceAttachRequest = {}): Observable<{ status: string; document: Record<string, unknown> }> {
    return this.knowledgeApiService.attachDocumentToKnowledgeSpace(knowledgeSpaceId, docId, payload);
  }

  consolidateKnowledgeSpace(knowledgeSpaceId: string, payload: { user_id?: string; limit_docs?: number } = {}): Observable<KnowledgeSpaceConsolidationResponse> {
    return this.knowledgeApiService.consolidateKnowledgeSpace(knowledgeSpaceId, payload);
  }

  queryKnowledgeSpace(knowledgeSpaceId: string, payload: { user_id?: string; question: string; mode?: string; limit?: number }): Observable<KnowledgeSpaceQueryResponse> {
    return this.knowledgeApiService.queryKnowledgeSpace(knowledgeSpaceId, payload);
  }

  ragSearch(params: {
    query: string
    type?: string
    origin?: string
    doc_id?: string
    file_path?: string
    limit?: number
    min_score?: number
  }): Observable<RagSearchResponse> {
    return this.knowledgeApiService.ragSearch(params);
  }

  ragUserChat(params: {
    query: string
    user_id: string
    session_id?: string
    role?: string
    limit?: number
    min_score?: number
  }): Observable<RagUserChatResponse> {
    return this.knowledgeApiService.ragUserChat(params);
  }

  ragUserChatV2(params: {
    query: string
    user_id?: string
    session_id?: string
    start_ts_ms?: number
    end_ts_ms?: number
    limit?: number
    min_score?: number
  }): Observable<RagUserChatV2Response> {
    return this.knowledgeApiService.ragUserChatV2(params);
  }

  ragHybridSearch(params: {
    query: string
    user_id?: string
    limit?: number
    min_score?: number
  }): Observable<RagHybridResponse> {
    return this.knowledgeApiService.ragHybridSearch(params);
  }

  ragProductivitySearch(params: {
    query: string
    user_id: string
    limit?: number
    min_score?: number
  }): Observable<RagSearchResponse> {
    return this.knowledgeApiService.ragProductivitySearch(params);
  }

  thumbsUpFeedback(req: FeedbackQuickRequest): Observable<FeedbackQuickResponse> {
    return this.feedbackApiService.thumbsUpFeedback(req);
  }

  thumbsDownFeedback(req: FeedbackQuickRequest): Observable<FeedbackQuickResponse> {
    return this.feedbackApiService.thumbsDownFeedback(req);
  }

  getKnowledgeStats(): Observable<KnowledgeStats> {
    return this.knowledgeApiService.getKnowledgeStats();
  }

  getEntityRelationships(entityName: string): Observable<EntityRelationshipsResponse> {
    return this.knowledgeApiService.getEntityRelationships(entityName);
  }

  getReflexionSummary(limit: number = 10): Observable<PostSprintSummaryResponse> {
    return this.observabilityApiService.getReflexionSummary(limit);
  }

  getSystemDbValidate(): Observable<DbValidationResponse> {
    return this.systemApiService.getSystemDbValidate();
  }

  getKnowledgeHealth(): Observable<KnowledgeHealthResponse> {
    return this.knowledgeApiService.getKnowledgeHealth();
  }

  getKnowledgeHealthDetailed(): Observable<KnowledgeHealthDetailedResponse> {
    return this.knowledgeApiService.getKnowledgeHealthDetailed();
  }

  resetKnowledgeCircuitBreaker(): Observable<{ message: string }> {
    return this.knowledgeApiService.resetKnowledgeCircuitBreaker();
  }

}
</file>

<file path="app/services/chat-auth-headers.util.spec.ts">
import { AUTH_TOKEN_KEY } from './api.config'
import { buildChatStreamAuthHeaders } from './chat-auth-headers.util'

describe('buildChatStreamAuthHeaders', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  afterEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  it('deve montar headers com bearer, x-user-id e x-project-id', () => {
    const payload = btoa(JSON.stringify({ user_id: 42 }))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/g, '')
    const fakeToken = `${payload}.ignored.signature`
    localStorage.setItem(AUTH_TOKEN_KEY, fakeToken)

    const headers = buildChatStreamAuthHeaders({ projectId: 'p-1' })

    expect(headers.get('Authorization')).toBe(`Bearer ${fakeToken}`)
    expect(headers.get('X-User-Id')).toBe('42')
    expect(headers.get('X-Project-Id')).toBe('p-1')
    expect(headers.get('X-Request-ID')).toBeTruthy()
    expect(headers.get('traceparent')).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/)
  })

  it('deve retornar headers de rastreio mesmo sem token', () => {
    const headers = buildChatStreamAuthHeaders()
    expect(headers.get('Authorization')).toBeNull()
    expect(headers.get('X-User-Id')).toBeNull()
    expect(headers.get('X-Request-ID')).toBeTruthy()
    expect(headers.get('traceparent')).toMatch(/^00-[0-9a-f]{32}-[0-9a-f]{16}-01$/)
  })

  it('deve usar token de sessionStorage quando localStorage estiver vazio', () => {
    const payload = btoa(JSON.stringify({ user_id: 7 }))
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/g, '')
    const fakeToken = `${payload}.ignored.signature`
    sessionStorage.setItem(AUTH_TOKEN_KEY, fakeToken)

    const headers = buildChatStreamAuthHeaders()

    expect(headers.get('Authorization')).toBe(`Bearer ${fakeToken}`)
    expect(headers.get('X-User-Id')).toBe('7')
  })
})
</file>

<file path="app/services/chat-auth-headers.util.ts">
import { decodeTokenUserId, getStoredAuthToken } from './auth.utils'

export interface ChatStreamAuthHeadersOptions {
  projectId?: string | null
  requestId?: string
  traceparent?: string
  tracestate?: string
}

function randomHex(size: number): string {
  let output = ''
  for (let i = 0; i < size; i += 1) {
    output += Math.floor(Math.random() * 16).toString(16)
  }
  return output
}

export function generateRequestId(): string {
  const s = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'
  return s.replace(/[xy]/g, c => {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}

export function generateTraceparent(): string {
  const traceId = randomHex(32)
  const spanId = randomHex(16)
  return `00-${traceId}-${spanId}-01`
}

export function buildChatStreamAuthHeaders(
  options: ChatStreamAuthHeadersOptions = {},
): Headers {
  const headers = new Headers()
  const requestId = options.requestId || generateRequestId()
  headers.set('X-Request-ID', requestId)
  headers.set('traceparent', options.traceparent || generateTraceparent())
  if (options.tracestate) {
    headers.set('tracestate', options.tracestate)
  }
  try {
    const token = getStoredAuthToken()
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
      const uid = decodeTokenUserId(token)
      if (uid !== null) {
        headers.set('X-User-Id', String(uid))
      }
    }
  } catch {
    /* noop */
  }

  if (options.projectId) {
    headers.set('X-Project-Id', String(options.projectId))
  }

  return headers
}
</file>

<file path="app/services/chat-stream.service.ts">
import { Injectable, inject } from '@angular/core'
import { BehaviorSubject, Observable, Subject } from 'rxjs'
import { API_BASE_URL, SSE_MAX_RETRIES, SSE_RETRY_MAX_SECONDS } from './api.config'
import { ChatAgentState, ChatConfirmationState, ChatUnderstanding, Citation, CitationStatus } from './backend-api.service'
import { AppLoggerService } from '../core/services/app-logger.service'
import { buildChatStreamAuthHeaders, generateRequestId } from './chat-auth-headers.util'

type StreamStatus = 'idle' | 'connecting' | 'open' | 'streaming' | 'retrying' | 'closed' | 'error'

export interface StreamDone {
  conversation_id?: string
  message_id?: string
  provider?: string
  model?: string
  knowledge_space_id?: string
  mode_used?: string
  base_used?: string
  estimated_wait_seconds?: number
  estimated_wait_range_seconds?: number[]
  processing_profile?: string
  processing_notice?: string | null
  source_scope?: Record<string, unknown> | null
  gaps_or_conflicts?: string[]
  citations?: Citation[]
  citation_status?: CitationStatus
  understanding?: ChatUnderstanding
  confirmation?: ChatConfirmationState
  agent_state?: ChatAgentState
}

export interface StreamError {
  error: string
  code?: string
  category?: string
  retryable?: boolean
  http_status?: number | null
  attempt: number
}

export interface StreamCognitiveStatus {
  state: string
  confidence_band?: string
  requires_confirmation?: boolean
  reason?: string
  timestamp?: number
}

export interface StreamToolStatus {
  phase?: string
  tool_name?: string
  status?: string
  pending_action_id?: number
  risk_level?: string
  message?: string
}

export interface StartParams {
  conversationId: string
  text: string
  role?: string
  priority?: string
  timeoutSeconds?: number
  projectId?: string
  knowledgeSpaceId?: string
}

interface ParsedSseEvent {
  event: string
  data: string
}

@Injectable({ providedIn: 'root' })
export class ChatStreamService {
  private readonly logger = inject(AppLoggerService)
  private abortController?: AbortController
  private streamSeq = 0
  private lastUrl?: string
  private lastProjectId?: string
  private lastRequestId?: string
  private status$ = new BehaviorSubject<StreamStatus>('idle')
  private typing$ = new BehaviorSubject<boolean>(false)
  private partials$ = new Subject<{ text: string }>()
  private done$ = new Subject<StreamDone>()
  private errors$ = new Subject<StreamError>()
  private cognitive$ = new Subject<StreamCognitiveStatus>()
  private toolStatus$ = new Subject<StreamToolStatus>()
  private attempt = 0
  private startTs = 0
  private ttftCaptured = false
  private streamMode: 'token' | 'partial' | null = null

  status(): Observable<StreamStatus> { return this.status$.asObservable() }
  typing(): Observable<boolean> { return this.typing$.asObservable() }
  partials(): Observable<{ text: string }> { return this.partials$.asObservable() }
  done(): Observable<StreamDone> { return this.done$.asObservable() }
  errors(): Observable<StreamError> { return this.errors$.asObservable() }
  cognitive(): Observable<StreamCognitiveStatus> { return this.cognitive$.asObservable() }
  toolStatus(): Observable<StreamToolStatus> { return this.toolStatus$.asObservable() }

  start(params: StartParams): void {
    this.logger.debug('[ChatStreamService] Iniciando stream', params)
    this.stop()
    this.status$.next('connecting')
    this.typing$.next(false)
    this.attempt = 0
    this.startTs = Date.now()
    this.ttftCaptured = false
    this.streamMode = null
    this.lastProjectId = params.projectId
    this.lastRequestId = generateRequestId()

    const role = params.role || 'orchestrator'
    const priority = params.priority || 'fast_and_cheap'
    const qs = new URLSearchParams({
      message: params.text,
      role,
      priority,
    })
    if (typeof params.timeoutSeconds !== 'undefined') {
      qs.set('timeout_seconds', String(params.timeoutSeconds))
    }
    if (params.knowledgeSpaceId) {
      qs.set('knowledge_space_id', params.knowledgeSpaceId)
    }
    const url = `${API_BASE_URL}/v1/chat/stream/${encodeURIComponent(params.conversationId)}?${qs.toString()}`
    this.logger.debug('[ChatStreamService] URL construída', { url })
    this.open(url, params.projectId, this.lastRequestId)
  }

  stop(): void {
    const ctrl = this.abortController
    this.abortController = undefined
    if (ctrl) {
      try {
        ctrl.abort()
      } catch {
        /* noop */
      }
    }
    this.status$.next('closed')
    this.typing$.next(false)
  }

  private open(url: string, projectId?: string, requestId?: string): void {
    this.lastUrl = url
    this.lastProjectId = projectId
    this.lastRequestId = requestId || this.lastRequestId || generateRequestId()
    const seq = ++this.streamSeq
    const controller = new AbortController()
    this.abortController = controller
    void this.consumeStream(url, controller, seq, projectId, this.lastRequestId)
  }

  private async consumeStream(
    url: string,
    controller: AbortController,
    seq: number,
    projectId?: string,
    requestId?: string,
  ): Promise<void> {
    this.logger.debug('[ChatStreamService] Abrindo fetch-SSE', { url, seq })
    try {
      const headers = buildChatStreamAuthHeaders({ projectId, requestId })
      headers.set('Accept', 'text/event-stream')

      const response = await fetch(url, {
        method: 'GET',
        headers,
        signal: controller.signal,
      })

      if (!response.ok) {
        const bodyText = await this.safeReadErrorBody(response)
        const parsedError = this.parseChatErrorBody(bodyText)
        this.logger.error('[ChatStreamService] HTTP error no stream', {
          status: response.status,
          bodyText,
        })
        const reason = parsedError.message || this.mapHttpErrorReason(response.status, bodyText)
        const retryable = typeof parsedError.retryable === 'boolean'
          ? parsedError.retryable
          : !(response.status === 401 || response.status === 403 || response.status === 404 || response.status === 413 || response.status === 422)
        this.handleError(reason, retryable, {
          code: parsedError.code,
          category: parsedError.category,
          retryable,
          http_status: response.status,
        })
        return
      }

      if (!response.body) {
        this.handleError('empty_stream_body')
        return
      }

      this.logger.info('[ChatStreamService] Stream conectado com sucesso', { seq })
      this.status$.next('open')

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      let streamOpen = true
      while (streamOpen) {
        const { value, done } = await reader.read()
        if (done) {
          streamOpen = false
          continue
        }
        buffer += decoder.decode(value, { stream: true })
        const parsed = this.extractEvents(buffer)
        buffer = parsed.remaining
        for (const evt of parsed.events) {
          this.dispatchSseEvent(evt.event, evt.data)
          if (seq !== this.streamSeq || controller.signal.aborted) return
        }
      }

      buffer += decoder.decode()
      const trailing = this.extractEvents(buffer, true)
      for (const evt of trailing.events) {
        this.dispatchSseEvent(evt.event, evt.data)
      }

      if (!controller.signal.aborted && this.status$.value !== 'closed') {
        this.handleError('stream_closed')
      }
    } catch (error) {
      if (controller.signal.aborted || seq !== this.streamSeq) {
        return
      }
      this.logger.error('[ChatStreamService] Erro em fetch-SSE', error)
      this.handleError('connection_error')
    } finally {
      if (this.abortController === controller) {
        this.abortController = undefined
      }
    }
  }

  private dispatchSseEvent(event: string, data: string): void {
    switch (event) {
      case 'start':
        this.logger.debug('[ChatStreamService] Evento start recebido')
        this.status$.next('open')
        return
      case 'protocol':
        this.logger.debug('[ChatStreamService] Evento protocol recebido', { data })
        return
      case 'heartbeat':
        this.logger.debug('[ChatStreamService] Heartbeat recebido')
        return
      case 'ack':
      case 'cognitive_status':
      case 'tool_status':
      case 'partial':
      case 'token':
      case 'done':
      case 'error':
      case 'message':
        this.handleMessage(event, data)
        return
      default:
        this.logger.debug('[ChatStreamService] Evento SSE desconhecido', { event, data })
    }
  }

  private extractEvents(input: string, flush = false): { events: ParsedSseEvent[]; remaining: string } {
    const normalized = input.replace(/\r\n/g, '\n')
    const events: ParsedSseEvent[] = []
    let cursor = 0

    let hasSeparator = true
    while (hasSeparator) {
      const sep = normalized.indexOf('\n\n', cursor)
      if (sep === -1) {
        hasSeparator = false
        continue
      }
      const block = normalized.slice(cursor, sep)
      cursor = sep + 2
      const evt = this.parseSseBlock(block)
      if (evt) events.push(evt)
    }

    let remaining = normalized.slice(cursor)
    if (flush && remaining.trim()) {
      const evt = this.parseSseBlock(remaining)
      if (evt) events.push(evt)
      remaining = ''
    }

    return { events, remaining }
  }

  private parseSseBlock(block: string): ParsedSseEvent | null {
    const lines = block.split('\n')
    let event = 'message'
    const dataLines: string[] = []

    for (const rawLine of lines) {
      const line = rawLine ?? ''
      if (!line) continue
      if (line.startsWith(':')) continue
      if (line.startsWith('event:')) {
        event = line.slice('event:'.length).trim() || 'message'
        continue
      }
      if (line.startsWith('data:')) {
        dataLines.push(line.slice('data:'.length).trimStart())
      }
    }

    if (event === 'message' && dataLines.length === 0) return null
    return { event, data: dataLines.join('\n') }
  }

  private async safeReadErrorBody(response: Response): Promise<string> {
    try {
      return (await response.text()) || ''
    } catch {
      return ''
    }
  }

  private parseChatErrorBody(bodyText: string): { code?: string; message?: string; category?: string; retryable?: boolean } {
    if (!bodyText) return {}
    try {
      const parsed = JSON.parse(bodyText) as any
      const detail = parsed?.detail ?? parsed
      const canonical = detail?.error ?? detail
      const message = typeof canonical?.message === 'string'
        ? canonical.message
        : (typeof detail === 'string' ? detail : undefined)
      return {
        code: typeof canonical?.code === 'string' ? canonical.code : undefined,
        message,
        category: typeof canonical?.category === 'string' ? canonical.category : undefined,
        retryable: typeof canonical?.retryable === 'boolean' ? canonical.retryable : undefined,
      }
    } catch {
      return {}
    }
  }

  private mapHttpErrorReason(status: number, bodyText: string): string {
    if (status === 401) return 'unauthorized'
    if (status === 403) return 'access_denied'
    if (status === 404) return 'conversation_not_found'
    if (status === 413) return 'message_too_large'
    if (status === 422) return 'invalid_request'
    if (bodyText) return `http_${status}`
    return 'http_error'
  }

  private handleMessage(kind: string, data: string): void {
    this.logger.debug('[ChatStreamService] Processando mensagem', { kind, data })
    try {
      if (kind === 'token') {
        if (this.streamMode && this.streamMode !== 'token') return
        this.streamMode = 'token'
        kind = 'partial'
      } else if (kind === 'partial') {
        if (this.streamMode && this.streamMode !== 'partial') return
        this.streamMode = 'partial'
      }
      if (kind === 'partial') {
        this.status$.next('streaming')
        this.typing$.next(true)
        const parsed = JSON.parse(data || '{}') as { text?: string }
        if (!this.ttftCaptured) {
          this.ttftCaptured = true
        }
        const rawText = parsed?.text
        let text = ''
        if (typeof rawText === 'string') {
          text = rawText
        } else if (rawText != null) {
          try {
            text = JSON.stringify(rawText, null, 2)
          } catch {
            text = String(rawText)
          }
        }
        this.partials$.next({ text })
        return
      }
      if (kind === 'done') {
        this.typing$.next(false)
        const parsed = JSON.parse(data || '{}') as StreamDone
        this.done$.next({
          conversation_id: parsed?.conversation_id,
          message_id: parsed?.message_id,
          provider: parsed?.provider,
          model: parsed?.model,
          knowledge_space_id: parsed?.knowledge_space_id,
          mode_used: parsed?.mode_used,
          base_used: parsed?.base_used,
          estimated_wait_seconds: parsed?.estimated_wait_seconds,
          estimated_wait_range_seconds: parsed?.estimated_wait_range_seconds,
          processing_profile: parsed?.processing_profile,
          processing_notice: parsed?.processing_notice,
          source_scope: parsed?.source_scope,
          gaps_or_conflicts: parsed?.gaps_or_conflicts,
          citations: parsed?.citations,
          citation_status: parsed?.citation_status,
          understanding: parsed?.understanding,
          confirmation: parsed?.confirmation,
          agent_state: parsed?.agent_state,
        })
        this.stop()
        return
      }
      if (kind === 'error') {
        const parsed = JSON.parse(data || '{}') as { error?: string; message?: string; code?: string; category?: string; retryable?: boolean; http_status?: number | null }
        this.handleError(
          String(parsed?.message || parsed?.error || 'error'),
          parsed?.retryable !== false,
          {
            code: typeof parsed?.code === 'string' ? parsed.code : undefined,
            category: typeof parsed?.category === 'string' ? parsed.category : undefined,
            http_status: typeof parsed?.http_status === 'number' ? parsed.http_status : (parsed?.http_status ?? undefined),
            retryable: parsed?.retryable,
          }
        )
        return
      }
      if (kind === 'cognitive_status') {
        const parsed = JSON.parse(data || '{}') as StreamCognitiveStatus
        this.cognitive$.next(parsed || { state: 'unknown' })
        if (parsed?.state === 'streaming_response') {
          this.status$.next('streaming')
        }
        return
      }
      if (kind === 'tool_status') {
        const parsed = JSON.parse(data || '{}') as StreamToolStatus
        this.toolStatus$.next(parsed || {})
        return
      }
      if (kind === 'ack' || kind === 'message') {
        return
      }
      this.logger.warn('[ChatStreamService] Tipo de mensagem não reconhecido', { kind })
    } catch (e) {
      this.logger.error('[ChatStreamService] Erro ao processar mensagem', e)
      this.handleError('parse_error')
    }
  }

  private handleError(
    reason: string,
    retryable = true,
    meta?: { code?: string; category?: string; retryable?: boolean; http_status?: number | null },
  ): void {
    this.attempt += 1
    this.errors$.next({
      error: reason,
      attempt: this.attempt,
      code: meta?.code,
      category: meta?.category,
      retryable: meta?.retryable,
      http_status: meta?.http_status,
    })

    if (!retryable) {
      this.status$.next('error')
      this.typing$.next(false)
      const ctrl = this.abortController
      if (ctrl) {
        try { ctrl.abort() } catch { /* noop */ }
        this.abortController = undefined
      }
      this.logger.error('[ChatStreamService] Erro não recuperável no stream', { reason })
      return
    }

    if (this.attempt >= Math.max(1, SSE_MAX_RETRIES)) {
      this.status$.next('error')
      this.typing$.next(false)
      const ctrl = this.abortController
      if (ctrl) {
        try { ctrl.abort() } catch { /* noop */ }
        this.abortController = undefined
      }
      this.logger.error('[ChatStreamService] Máximo de tentativas de reconexão atingido', { reason })
      return
    }

    this.status$.next('error')
    this.typing$.next(false)
    const max = Math.max(1, SSE_RETRY_MAX_SECONDS)
    const backoff = Math.min(max, Math.pow(2, this.attempt))
    const jitter = Math.random() * 0.5
    const wait = (backoff + jitter) * 1000
    this.status$.next('retrying')
    const ctrl = this.abortController
    if (ctrl) {
      try { ctrl.abort() } catch { /* noop */ }
      this.abortController = undefined
    }
    const url = this.lastUrl
    const projectId = this.lastProjectId
    const requestId = this.lastRequestId
    setTimeout(() => {
      if (!url) return
      this.status$.next('connecting')
      this.open(url, projectId, requestId)
    }, wait)
  }
}
</file>

<file path="app/services/conversation-refresh.service.ts">
import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';
import { AppLoggerService } from '../core/services/app-logger.service';

@Injectable({
  providedIn: 'root'
})
export class ConversationRefreshService {
  private refreshConversations$ = new Subject<void>();
  constructor(private readonly logger: AppLoggerService) {}

  // Observable para ouvir eventos de refresh
  get refreshConversations() {
    return this.refreshConversations$.asObservable();
  }

  // Emitir evento de refresh
  triggerRefresh() {
    this.logger.debug('[ConversationRefreshService] Triggering conversations refresh')
    this.refreshConversations$.next();
  }
}
</file>

<file path="app/services/graph-api.service.ts">
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_BASE_URL } from './api.config';
import { map } from 'rxjs/operators';

export interface GraphNode {
    id: string;
    label: string;
    type: string; // Concept, Technology, Tool, Pattern, etc.
    properties: Record<string, unknown>;
}

export interface GraphEdge {
    id: string;
    source: string;
    target: string;
    label: string;
    properties: Record<string, unknown>;
}

export interface GraphData {
    nodes: GraphNode[];
    edges: GraphEdge[];
}

// Cytoscape format
export interface CytoscapeElement {
    data: {
        id: string;
        label?: string;
        source?: string;
        target?: string;
        type?: string;
        [key: string]: unknown;
    };
    classes?: string;
}

@Injectable({ providedIn: 'root' })
export class GraphApiService {
    private http = inject(HttpClient);

    /**
     * Fetch full graph or subgraph from Neo4j
     */
    getGraph(params?: { limit?: number; labels?: string[] }): Observable<CytoscapeElement[]> {
        const queryParams: Record<string, string> = {};
        if (params?.limit) queryParams['limit'] = String(params.limit);
        if (params?.labels) queryParams['labels'] = params.labels.join(',');

        return this.http
            .get<GraphData>(`${API_BASE_URL}/v1/knowledge/graph`, { params: queryParams })
            .pipe(map((data) => this.transformToCytoscape(data)));
    }

    /**
     * Get neighbors of a specific node
     */
    getNeighbors(nodeId: string, depth: number = 1): Observable<CytoscapeElement[]> {
        return this.http
            .get<GraphData>(`${API_BASE_URL}/v1/knowledge/concepts/${nodeId}/neighbors`, {
                params: { depth: String(depth) },
            })
            .pipe(map((data) => this.transformToCytoscape(data)));
    }

    /**
     * Transform backend graph format to Cytoscape format
     */
    private transformToCytoscape(graph: GraphData): CytoscapeElement[] {
        const elements: CytoscapeElement[] = [];

        // Nodes
        graph.nodes.forEach((node) => {
            elements.push({
                data: {
                    id: node.id,
                    label: node.label,
                    type: node.type,
                    ...node.properties,
                },
                classes: node.type.toLowerCase(),
            });
        });

        // Edges
        graph.edges.forEach((edge) => {
            elements.push({
                data: {
                    id: edge.id,
                    source: edge.source,
                    target: edge.target,
                    label: edge.label,
                    ...edge.properties,
                },
            });
        });

        return elements;
    }
}
</file>

<file path="app/services/mock-auto-analysis.service.ts">
import { Injectable } from '@angular/core'
import { Observable, of } from 'rxjs'
import { delay } from 'rxjs/operators'
import { AutoAnalysisResponse } from './auto-analysis.service'

/**
 * Mock service para testar o componente de auto-análise sem depender do backend
 */
@Injectable({ providedIn: 'root' })
export class MockAutoAnalysisService {
  private mockResponse: AutoAnalysisResponse = {
    timestamp: new Date().toISOString(),
    overall_health: 'healthy',
    insights: [
      {
        issue: 'Gastos com APIs: $12.50',
        severity: 'low',
        suggestion: 'Considere usar mais modelos locais (Ollama) para economizar',
        estimated_impact: 'Provedores ativos: 2'
      },
      {
        issue: 'Performance de Respostas',
        severity: 'low',
        suggestion: 'Respostas estão rápidas! Continue assim',
        estimated_impact: 'Tempo médio de resposta: <2s ✅'
      },
      {
        issue: 'Qualidade das Respostas',
        severity: 'low',
        suggestion: 'Considere alternar entre modelos para melhor variedade',
        estimated_impact: 'Satisfação do usuário: Boa 📈'
      }
    ],
    fun_fact: 'Você sabia? Já processei mais de 1000 perguntas! 🤯',
    total_memories: 124,
    session_duration: '42m',
    efficiency_score: 98
  }

  getHealthCheck(): Observable<AutoAnalysisResponse> {
    // Simula delay de rede
    return of(this.mockResponse).pipe(delay(1000))
  }
}
</file>

<file path="app/services/response-time-estimator.service.ts">
import { Injectable } from '@angular/core'

export interface ResponseTimeStats {
  avgTime: number
  minTime: number
  maxTime: number
  count: number
  lastResponseTime?: number
}

export interface ComplexityFactors {
  messageLength: number
  hasCode: boolean
  hasMultipleQuestions: boolean
  hasFileReferences: boolean
  hasComplexTerms: boolean
}

@Injectable({ providedIn: 'root' })
export class ResponseTimeEstimatorService {
  private responseHistory: number[] = []
  private maxHistorySize = 50
  
  // Tempos base em milissegundos
  private readonly BASE_TIMES = {
    simple: 2000,      // 2 segundos
    medium: 5000,      // 5 segundos  
    complex: 10000,    // 10 segundos
    veryComplex: 20000 // 20 segundos
  }
  
  // Fatores de complexidade
  private readonly COMPLEXITY_FACTORS = {
    messageLength: 0.5,        // +0.5s por 100 caracteres
    hasCode: 3000,             // +3s se tiver código
    hasMultipleQuestions: 2000, // +2s se tiver múltiplas perguntas
    hasFileReferences: 4000,   // +4s se referenciar arquivos
    hasComplexTerms: 2000      // +2s se tiver termos técnicos complexos
  }

  recordResponseTime(timeMs: number): void {
    this.responseHistory.push(timeMs)
    
    // Limitar histórico
    if (this.responseHistory.length > this.maxHistorySize) {
      this.responseHistory.shift()
    }
  }

  getStats(): ResponseTimeStats {
    if (this.responseHistory.length === 0) {
      return {
        avgTime: this.BASE_TIMES.medium,
        minTime: this.BASE_TIMES.simple,
        maxTime: this.BASE_TIMES.complex,
        count: 0
      }
    }

    const sum = this.responseHistory.reduce((a, b) => a + b, 0)
    return {
      avgTime: sum / this.responseHistory.length,
      minTime: Math.min(...this.responseHistory),
      maxTime: Math.max(...this.responseHistory),
      count: this.responseHistory.length,
      lastResponseTime: this.responseHistory[this.responseHistory.length - 1]
    }
  }

  analyzeComplexity(message: string): ComplexityFactors {
    return {
      messageLength: message.length,
      hasCode: this.hasCodeBlocks(message),
      hasMultipleQuestions: this.hasMultipleQuestions(message),
      hasFileReferences: this.hasFileReferences(message),
      hasComplexTerms: this.hasComplexTerms(message)
    }
  }

  estimateResponseTime(message: string): number {
    const complexity = this.analyzeComplexity(message)
    const stats = this.getStats()
    
    // Começar com a média histórica ou tempo base
    let estimatedTime = stats.count > 0 ? stats.avgTime : this.BASE_TIMES.medium
    
    // Ajustar baseado na complexidade da mensagem
    if (complexity.messageLength > 200) {
      estimatedTime += (complexity.messageLength / 100) * this.COMPLEXITY_FACTORS.messageLength
    }
    
    if (complexity.hasCode) {
      estimatedTime += this.COMPLEXITY_FACTORS.hasCode
    }
    
    if (complexity.hasMultipleQuestions) {
      estimatedTime += this.COMPLEXITY_FACTORS.hasMultipleQuestions
    }
    
    if (complexity.hasFileReferences) {
      estimatedTime += this.COMPLEXITY_FACTORS.hasFileReferences
    }
    
    if (complexity.hasComplexTerms) {
      estimatedTime += this.COMPLEXITY_FACTORS.hasComplexTerms
    }
    
    // Limitar entre mínimo e máximo razoáveis
    const minTime = Math.max(this.BASE_TIMES.simple, stats.minTime * 0.5)
    const maxTime = Math.min(60000, Math.max(stats.maxTime * 2, this.BASE_TIMES.veryComplex)) // Máximo 60 segundos
    
    return Math.min(maxTime, Math.max(minTime, estimatedTime))
  }

  formatEstimatedTime(milliseconds: number): string {
    const seconds = Math.ceil(milliseconds / 1000)
    
    if (seconds < 5) {
      return 'alguns segundos'
    } else if (seconds < 60) {
      return `${seconds} segundos`
    } else if (seconds < 120) {
      return '1 minuto'
    } else {
      const minutes = Math.ceil(seconds / 60)
      return `${minutes} minutos`
    }
  }

  private hasCodeBlocks(message: string): boolean {
    const codeIndicators = [
      /```[\s\S]*?```/g,      // Code blocks
      /`[^`]+`/g,               // Inline code
      /function\s+\w+/g,        // Function definitions
      /const\s+\w+\s*=/g,       // Variable declarations
      /class\s+\w+/g,           // Class definitions
      /\w+\(.*\)\s*{/g          // Function calls with braces
    ]
    
    return codeIndicators.some(pattern => pattern.test(message))
  }

  private hasMultipleQuestions(message: string): boolean {
    const questionMarks = (message.match(/\?/g) || []).length
    return questionMarks > 1
  }

  private hasFileReferences(message: string): boolean {
    const filePatterns = [
      /\w+\.\w+/g,             // file.ext
      /\/[\w/.-]+/g,           // /path/to/file
      /\w+:\/\/[^\s]+/g         // URLs
    ]
    
    return filePatterns.some(pattern => pattern.test(message))
  }

  private hasComplexTerms(message: string): boolean {
    const complexTerms = [
      'arquitetura', 'implementação', 'otimização', 'performance',
      'escalabilidade', 'microserviço', 'containerização', 'devops',
      'machine learning', 'inteligência artificial', 'algoritmo',
      'complexidade', 'refatoração', 'depuração', 'análise'
    ]
    
    const lowerMessage = message.toLowerCase()
    return complexTerms.some(term => lowerMessage.includes(term))
  }
}
</file>

<file path="app/services/ux-metrics.service.ts">
import { Injectable } from '@angular/core'
import { BehaviorSubject, Observable } from 'rxjs'
import { HttpClient } from '@angular/common/http'
import { API_BASE_URL, UX_METRICS_SAMPLING } from './api.config'

export interface UxMetricItem { ttft_ms?: number; latency_ms?: number; outcome: 'success'|'error'|'cancel'; retries?: number; provider?: string; model?: string; timestamp: number }

@Injectable({ providedIn: 'root' })
export class UxMetricsService {
  private items$ = new BehaviorSubject<UxMetricItem[]>([])
  constructor(private http: HttpClient) {}

  metrics(): Observable<UxMetricItem[]> { return this.items$.asObservable() }

  record(item: UxMetricItem) {
    const arr = [item, ...this.items$.getValue()].slice(0, 500)
    this.items$.next(arr)
    if (Math.random() < UX_METRICS_SAMPLING) {
      const url = `${API_BASE_URL}/v1/observability/metrics/ux`
      this.http.post(url, item).subscribe({ next: () => {}, error: () => {} })
    }
  }

  p95Latency(): number | null {
    const xs = this.items$.getValue().map(i => i.latency_ms || 0).filter(x => x > 0).sort((a, b) => a - b)
    if (!xs.length) return null
    const idx = Math.floor(xs.length * 0.95) - 1
    return xs[Math.max(0, idx)]
  }
}
</file>

<file path="app/shared/components/confirm-dialog/confirm-dialog.component.ts">
import { Component, inject } from '@angular/core'
import { CommonModule } from '@angular/common'
import { UiButtonComponent } from '../../../shared/components/ui/button/button.component'
import { UiDialogRef } from '../ui/dialog/dialog-ref'
import { UI_DIALOG_DATA } from '../ui/dialog/dialog.tokens'

export interface ConfirmDialogData {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  confirmColor?: 'primary' | 'warn' | 'accent'
}

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule, UiButtonComponent],
  template: `
    <div class="confirm-dialog-content">
      <div class="dialog-header">
        <div class="dialog-icon">
          <span class="icon-symbol">!</span>
        </div>
        <h2 class="dialog-title">{{ data.title }}</h2>
      </div>
      <p class="dialog-message">{{ data.message }}</p>
      <div class="dialog-actions">
        <button ui-button variant="outline" size="sm" (click)="onCancel()">
          {{ data.cancelText || 'Cancelar' }}
        </button>
        <button
          ui-button
          [variant]="confirmVariant"
          size="sm"
          (click)="onConfirm()">
          {{ data.confirmText || 'Confirmar' }}
        </button>
      </div>
    </div>
  `,
  styles: [`
    .confirm-dialog-content {
      /* Removed padding/bg/shadow as container handles it, OR keep it if I want nested card look? */
      /* Actually UiDialogContainer has padding and bg. */
      /* So I should strip this down to just layout. */
      display: block;
    }

    .dialog-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
    }

    .dialog-icon {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: rgba(255, 176, 32, 0.1); /* Warning bg */
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px solid rgba(255, 176, 32, 0.3);
      flex-shrink: 0;
    }

    .icon-symbol {
      font-weight: 800;
      font-size: 18px;
      color: #ffb020; /* Warning color */
    }

    .dialog-title {
      margin: 0;
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--janus-text-primary);
    }

    .dialog-message {
      margin: 0 0 24px 0;
      font-size: 0.94rem;
      color: var(--janus-text-secondary);
      line-height: 1.6;
      white-space: pre-line;
    }

    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }
  `]
})
export class ConfirmDialogComponent {
  data = inject<ConfirmDialogData>(UI_DIALOG_DATA)
  private dialogRef = inject(UiDialogRef<boolean>)

  get confirmVariant(): 'default' | 'destructive' {
    return this.data.confirmColor === 'primary' ? 'default' : 'destructive';
  }

  onConfirm(): void {
    this.dialogRef.close(true)
  }

  onCancel(): void {
    this.dialogRef.close(false)
  }
}
</file>

<file path="app/shared/components/jarvis-avatar/jarvis-avatar.component.ts">
import { Component, HostBinding, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

type AvatarState = 'idle' | 'thinking' | 'speaking' | 'listening';

@Component({
  selector: 'app-jarvis-avatar',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="janus-sigil" [ngClass]="state">
      <svg class="sigil" viewBox="0 0 120 120" role="img" aria-label="Janus">
        <defs>
          <linearGradient id="sigilHalo" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="var(--janus-secondary)" />
            <stop offset="100%" stop-color="var(--janus-primary)" />
          </linearGradient>
          <linearGradient id="sigilHex" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="var(--janus-accent)" />
            <stop offset="100%" stop-color="var(--janus-secondary)" />
          </linearGradient>
          <radialGradient id="sigilCore" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="#ffffff" />
            <stop offset="55%" stop-color="var(--janus-secondary)" />
            <stop offset="100%" stop-color="var(--janus-primary)" />
          </radialGradient>
        </defs>

        <circle class="halo" cx="60" cy="60" r="54"></circle>
        <g class="orbit">
          <circle class="node" cx="60" cy="10" r="2.2"></circle>
          <circle class="node" cx="110" cy="60" r="2.2"></circle>
          <circle class="node" cx="60" cy="110" r="2.2"></circle>
          <circle class="node" cx="10" cy="60" r="2.2"></circle>
        </g>
        <polygon
          class="hex"
          points="60,16 94,36 94,84 60,104 26,84 26,36"
        ></polygon>
        <circle class="core-glow" cx="60" cy="60" r="26"></circle>
        <circle class="core" cx="60" cy="60" r="16"></circle>
        <circle class="pulse" cx="60" cy="60" r="20"></circle>
      </svg>

      <span class="scan-line" aria-hidden="true"></span>
    </div>
  `,
  styles: [`
    :host {
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .janus-sigil {
      position: relative;
      width: var(--avatar-size, 48px);
      height: var(--avatar-size, 48px);
      display: grid;
      place-items: center;
    }

    .sigil {
      width: 100%;
      height: 100%;
      filter: drop-shadow(0 0 10px rgba(var(--janus-secondary-rgb), 0.35));
    }

    .halo {
      fill: none;
      stroke: url(#sigilHalo);
      stroke-width: 2;
      stroke-dasharray: 6 8;
      opacity: 0.65;
      transform-origin: 50% 50%;
      animation: sigilSpin 18s linear infinite;
    }

    .orbit {
      transform-origin: 50% 50%;
      transform-box: fill-box;
      animation: sigilSpinReverse 24s linear infinite;
    }

    .node {
      fill: var(--janus-secondary);
      opacity: 0.85;
      filter: drop-shadow(0 0 6px rgba(var(--janus-secondary-rgb), 0.6));
    }

    .hex {
      fill: none;
      stroke: url(#sigilHex);
      stroke-width: 2;
      opacity: 0.9;
    }

    .core-glow {
      fill: none;
      stroke: rgba(var(--janus-secondary-rgb), 0.5);
      stroke-width: 2;
      filter: drop-shadow(0 0 12px rgba(var(--janus-secondary-rgb), 0.6));
    }

    .core {
      fill: url(#sigilCore);
    }

    .pulse {
      fill: none;
      stroke: rgba(var(--janus-primary-rgb), 0.45);
      stroke-width: 1.5;
      transform-origin: 50% 50%;
      animation: sigilPulse 2.6s ease-in-out infinite;
    }

    .scan-line {
      position: absolute;
      width: 120%;
      height: 2px;
      background: linear-gradient(90deg, transparent, rgba(var(--janus-secondary-rgb), 0.7), transparent);
      animation: scanSweep 3.8s ease-in-out infinite;
      opacity: 0.7;
    }

    @keyframes sigilSpin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }

    @keyframes sigilSpinReverse {
      from { transform: rotate(360deg); }
      to { transform: rotate(0deg); }
    }

    @keyframes sigilPulse {
      0%, 100% { transform: scale(0.92); opacity: 0.4; }
      50% { transform: scale(1.08); opacity: 0.8; }
    }

    @keyframes scanSweep {
      0%, 100% { transform: translateY(-45%); opacity: 0; }
      45% { opacity: 0.6; }
      50% { transform: translateY(45%); opacity: 0.9; }
      55% { opacity: 0.6; }
    }

    /* State: Thinking */
    .janus-sigil.thinking .halo {
      animation-duration: 8s;
      stroke: var(--janus-accent);
      opacity: 0.85;
    }

    .janus-sigil.thinking .pulse {
      stroke: rgba(var(--janus-accent-rgb), 0.6);
    }

    /* State: Speaking */
    .janus-sigil.speaking .halo {
      stroke: var(--success);
      opacity: 0.9;
    }

    .janus-sigil.speaking .pulse {
      stroke: rgba(var(--success-rgb), 0.6);
      animation-duration: 1.6s;
    }

    /* State: Listening */
    .janus-sigil.listening .halo {
      stroke: var(--error);
      opacity: 0.9;
    }

    .janus-sigil.listening .scan-line {
      background: linear-gradient(90deg, transparent, rgba(var(--error-rgb), 0.8), transparent);
    }
  `]
})
export class JarvisAvatarComponent {
  @Input() state: AvatarState = 'idle';
  @Input() size: number = 48;

  @HostBinding('style.--avatar-size.px')
  get avatarSize(): number {
    return this.size;
  }
}
</file>

<file path="app/shared/components/loading/loading.component.spec.ts">
import { Component } from '@angular/core'
import { ComponentFixture, TestBed } from '@angular/core/testing'
import { LoadingComponent } from './loading.component'
import { LoadingStateService } from '../../../core/services/loading-state.service'

class MockLoadingStateService {
  private loadingStates = new Map<string, any>()

  isKeyLoading(key: string): boolean {
    return this.loadingStates.has(key) && this.loadingStates.get(key).isLoading
  }

  getLoadingState(key: string): any {
    return this.loadingStates.get(key)
  }

  startLoading(key: string, config?: any): void {
    this.loadingStates.set(key, { isLoading: true, ...config })
  }

  stopLoading(key: string): void {
    if (this.loadingStates.has(key)) {
      this.loadingStates.get(key).isLoading = false
    }
  }
}

@Component({
  standalone: true,
  imports: [LoadingComponent],
  template: `<app-loading [isLoading]="isLoading">Projected content</app-loading>`
})
class LoadingHostComponent {
  isLoading = false
}

describe('LoadingComponent', () => {
  let component: LoadingComponent
  let fixture: ComponentFixture<LoadingComponent>
  let loadingStateService: MockLoadingStateService

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoadingComponent, LoadingHostComponent],
      providers: [
        { provide: LoadingStateService, useClass: MockLoadingStateService }
      ]
    }).compileComponents()

    fixture = TestBed.createComponent(LoadingComponent)
    component = fixture.componentInstance
    loadingStateService = TestBed.inject(LoadingStateService) as any
    fixture.detectChanges()
  })

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  describe('default values', () => {
    it('should have default isLoading as false', () => {
      expect(component.isLoading).toBe(false)
    })

    it('should have default message as empty string', () => {
      expect(component.message).toBe('')
    })

    it('should have default diameter as 40', () => {
      expect(component.diameter).toBe(40)
    })

    it('should have default color as primary', () => {
      expect(component.color).toBe('primary')
    })

    it('should have default mode as indeterminate', () => {
      expect(component.mode).toBe('indeterminate')
    })

    it('should have default overlay as false', () => {
      expect(component.overlay).toBe(false)
    })

    it('should have default showSpinner as true', () => {
      expect(component.showSpinner).toBe(true)
    })

    it('should have default showMessage as true', () => {
      expect(component.showMessage).toBe(true)
    })
  })

  describe('actualLoading', () => {
    it('should return isLoading when loadingKey is not provided', () => {
      component.isLoading = true
      expect(component.actualLoading).toBe(true)

      component.isLoading = false
      expect(component.actualLoading).toBe(false)
    })

    it('should return loading state from service when loadingKey is provided', () => {
      component.loadingKey = 'test-key'
      component.isLoading = false

      loadingStateService.startLoading('test-key')
      expect(component.actualLoading).toBe(true)

      loadingStateService.stopLoading('test-key')
      expect(component.actualLoading).toBe(false)
    })
  })

  describe('actualMessage', () => {
    it('should return message when loadingKey is not provided', () => {
      component.message = 'Test message'
      expect(component.actualMessage).toBe('Test message')
    })

    it('should return message from service when loadingKey is provided', () => {
      component.loadingKey = 'test-key'
      component.message = 'Default message'

      loadingStateService.startLoading('test-key', { message: 'Service message' })
      expect(component.actualMessage).toBe('Service message')

      loadingStateService.stopLoading('test-key')
      expect(component.actualMessage).toBe('Service message')
    })
  })

  describe('template rendering', () => {
    it('should show loading container when actualLoading is true', () => {
      fixture.componentRef.setInput('isLoading', true)
      fixture.detectChanges()

      const loadingContainer = fixture.nativeElement.querySelector('.loading-container')
      expect(loadingContainer).toBeTruthy()
    })

    it('should hide loading container when actualLoading is false', () => {
      component.isLoading = false
      fixture.detectChanges()

      const loadingContainer = fixture.nativeElement.querySelector('.loading-container')
      expect(loadingContainer).toBeFalsy()
    })

    it('should show spinner when showSpinner is true', () => {
      fixture.componentRef.setInput('isLoading', true)
      fixture.componentRef.setInput('showSpinner', true)
      fixture.detectChanges()

      const spinner = fixture.nativeElement.querySelector('ui-spinner')
      expect(spinner).toBeTruthy()
    })

    it('should hide spinner when showSpinner is false', () => {
      fixture.componentRef.setInput('isLoading', true)
      fixture.componentRef.setInput('showSpinner', false)
      fixture.detectChanges()

      const spinner = fixture.nativeElement.querySelector('ui-spinner')
      expect(spinner).toBeFalsy()
    })

    it('should show message when showMessage and actualMessage are truthy', () => {
      fixture.componentRef.setInput('isLoading', true)
      fixture.componentRef.setInput('showMessage', true)
      fixture.componentRef.setInput('message', 'Loading message')
      fixture.detectChanges()

      const messageElement = fixture.nativeElement.querySelector('.loading-message')
      expect(messageElement).toBeTruthy()
      expect(messageElement.textContent).toContain('Loading message')
    })

    it('should hide message when showMessage is false', () => {
      fixture.componentRef.setInput('isLoading', true)
      fixture.componentRef.setInput('showMessage', false)
      fixture.componentRef.setInput('message', 'Loading message')
      fixture.detectChanges()

      const messageElement = fixture.nativeElement.querySelector('.loading-message')
      expect(messageElement).toBeFalsy()
    })

    it('should apply overlay class when overlay is true', () => {
      fixture.componentRef.setInput('isLoading', true)
      fixture.componentRef.setInput('overlay', true)
      fixture.detectChanges()

      const loadingContainer = fixture.nativeElement.querySelector('.loading-container')
      expect(loadingContainer).toHaveClass('overlay')
    })

    it('should render projected content when not loading', () => {
      const hostFixture = TestBed.createComponent(LoadingHostComponent)
      hostFixture.detectChanges()

      expect(hostFixture.nativeElement.textContent).toContain('Projected content')
    })
  })
})
</file>

<file path="app/shared/components/loading/loading.component.ts">
import { Component, Input, ChangeDetectionStrategy, inject } from '@angular/core'
import { CommonModule } from '@angular/common'
import { UiSpinnerComponent } from '../ui/spinner/spinner.component'
import { LoadingStateService } from '../../../core/services/loading-state.service'

/**
 * Componente de loading reutilizável para todo o sistema
 * Uso: <app-loading [isLoading]="true" [message]="Carregando..." />
 */
@Component({
  selector: 'app-loading',
  standalone: true,
  imports: [CommonModule, UiSpinnerComponent],
  template: `
    @if (actualLoading) {
      <div class="loading-container" [class.overlay]="overlay">
        <div class="loading-content">
          @if (showSpinner) {
            <ui-spinner 
              [diameter]="diameter" 
              [color]="color">
            </ui-spinner>
          }
          @if (showMessage && actualMessage) {
            <p class="loading-message">{{ actualMessage }}</p>
          }
          @if (subMessage) {
            <p class="loading-submessage">{{ subMessage }}</p>
          }
        </div>
      </div>
    }
    @if (!actualLoading) {
      <ng-content></ng-content>
    }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    .loading-container {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;
      min-height: 200px;
    }

    .loading-container.overlay {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: rgba(255, 255, 255, 0.9);
      z-index: 1000;
      padding: 0;
    }

    .loading-content {
      text-align: center;
    }

    .loading-message {
      margin: 1rem 0 0.5rem 0;
      font-size: 1.1rem;
      font-weight: 500;
      color: #333;
    }

    .loading-submessage {
      margin: 0;
      font-size: 0.9rem;
      color: #666;
    }

    /* Animação suave de entrada/saída */
    :host {
      display: block;
      transition: opacity 0.3s ease;
    }
  `]
})
export class LoadingComponent {
  private readonly loadingStateService = inject(LoadingStateService)

  @Input() isLoading = false
  @Input() message = ''
  @Input() subMessage = ''
  @Input() diameter = 40
  @Input() color: 'primary' | 'accent' | 'warn' = 'primary'
  @Input() mode: 'determinate' | 'indeterminate' = 'indeterminate'
  @Input() overlay = false
  @Input() loadingKey?: string
  @Input() showSpinner = true
  @Input() showMessage = true

  get actualLoading(): boolean {
    if (this.loadingKey) {
      return this.loadingStateService.isKeyLoading(this.loadingKey)
    }
    return this.isLoading
  }

  get actualMessage(): string {
    if (this.loadingKey) {
      const state = this.loadingStateService.getLoadingState(this.loadingKey)
      return state?.message || this.message
    }
    return this.message
  }
}
</file>

<file path="app/shared/components/loading-dialog/loading-dialog.component.ts">
import { Component, inject } from '@angular/core'
import { CommonModule } from '@angular/common'
import { UiSpinnerComponent } from '../ui/spinner/spinner.component'
import { UI_DIALOG_DATA } from '../ui/dialog/dialog.tokens'

@Component({
  selector: 'app-loading-dialog',
  standalone: true,
  imports: [CommonModule, UiSpinnerComponent],
  template: `
    <div class="loading-dialog-content">
      <ui-spinner [size]="40"></ui-spinner>
      <p class="loading-message">{{ data.message }}</p>
    </div>
  `,
  styles: [`
    .loading-dialog-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 32px;
      gap: 20px;
      /* Background/border/shadow handled by container? No, container has p-6. 
         But loading dialog might want cleaner look. 
         Let's keep these styles as they define the inner layout. 
         But container usually has white bg.
      */
      /* background: var(--janus-bg-card); */
      /* border: 1px solid var(--janus-border); */
      /* border-radius: var(--janus-radius-lg); */
      /* box-shadow: var(--janus-shadow-glow); */
      /* Actually, since UiDialogContainer provides the card, we don't need double card. */
      /* Just layout. */
    }

    .loading-message {
      margin: 0;
      font-size: 1rem;
      font-weight: 500;
      color: var(--janus-text-primary);
      text-align: center;
      letter-spacing: 0.5px;
    }
  `]
})
export class LoadingDialogComponent {
  data = inject<{ message: string }>(UI_DIALOG_DATA)
}
</file>

<file path="app/shared/components/message-content/message-content.component.html">
<div class="message-content-container">
  @for (segment of segments; track segment) {
    @if (segment.type === 'text') {
      <div class="markdown-content" [innerHTML]="segment.content | markdown"></div>
    }
    @if (segment.type === 'dynamic') {
      <div class="dynamic-content-wrapper my-4">
        <app-dynamic-renderer [type]="segment.componentType!" [data]="segment.data"></app-dynamic-renderer>
      </div>
    }
  }
</div>
</file>

<file path="app/shared/components/skeleton/skeleton.component.spec.ts">
import { ComponentFixture, TestBed } from '@angular/core/testing'
import { SkeletonComponent } from './skeleton.component'

describe('SkeletonComponent', () => {
  let component: SkeletonComponent
  let fixture: ComponentFixture<SkeletonComponent>

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SkeletonComponent]
    }).compileComponents()

    fixture = TestBed.createComponent(SkeletonComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  })

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  describe('default values', () => {
    it('should have default variant as text', () => {
      expect(component.variant).toBe('text')
    })

    it('should have default count as 1', () => {
      expect(component.count).toBe(1)
    })

    it('should have default animated as true', () => {
      expect(component.animated).toBe(true)
    })

    it('should have default rounded as false', () => {
      expect(component.rounded).toBe(false)
    })
  })

  describe('counter', () => {
    it('should return array with correct length', () => {
      component.count = 3
      const counter = component.counter
      
      expect(counter.length).toBe(3)
      expect(counter).toEqual([0, 1, 2])
    })

    it('should return empty array when count is 0', () => {
      component.count = 0
      const counter = component.counter
      
      expect(counter.length).toBe(0)
      expect(counter).toEqual([])
    })
  })

  describe('getWidth', () => {
    it('should return pixel value for number input', () => {
      component.width = 100
      expect(component.getWidth()).toBe('100px')
    })

    it('should return string value for string input', () => {
      component.width = '50%'
      expect(component.getWidth()).toBe('50%')
    })

    it('should return auto when width is undefined', () => {
      component.width = undefined
      expect(component.getWidth()).toBe('auto')
    })
  })

  describe('getHeight', () => {
    it('should return pixel value for number input', () => {
      component.height = 50
      expect(component.getHeight()).toBe('50px')
    })

    it('should return string value for string input', () => {
      component.height = '100vh'
      expect(component.getHeight()).toBe('100vh')
    })

    it('should return auto when height is undefined', () => {
      component.height = undefined
      expect(component.getHeight()).toBe('auto')
    })
  })

  describe('CSS classes', () => {
    it('should apply correct CSS classes based on variant', () => {
      const variants = ['text', 'rect', 'circle', 'avatar', 'button', 'card', 'paragraph']
      
      variants.forEach(variant => {
        fixture.componentRef.setInput('variant', variant as any)
        fixture.detectChanges()
        
        const skeletonElement = fixture.nativeElement.querySelector('.skeleton')
        expect(skeletonElement).toHaveClass(`skeleton-${variant}`)
      })
    })

    it('should apply rounded class when rounded is true', () => {
      fixture.componentRef.setInput('rounded', true)
      fixture.detectChanges()
      
      const skeletonElement = fixture.nativeElement.querySelector('.skeleton')
      expect(skeletonElement).toHaveClass('rounded')
    })

    it('should apply animated class when animated is true', () => {
      fixture.componentRef.setInput('animated', true)
      fixture.detectChanges()
      
      const wrapperElement = fixture.nativeElement.querySelector('.skeleton-wrapper')
      expect(wrapperElement).toHaveClass('animated')
    })
  })

  describe('template rendering', () => {
    it('should render correct number of skeleton elements', () => {
      fixture.componentRef.setInput('count', 3)
      fixture.componentRef.setInput('variant', 'card')
      fixture.detectChanges()
      
      const skeletonElements = fixture.nativeElement.querySelectorAll('.skeleton')
      expect(skeletonElements.length).toBe(3)
    })

    it('should apply custom styles when width and height are provided', () => {
      fixture.componentRef.setInput('width', 200)
      fixture.componentRef.setInput('height', 100)
      fixture.detectChanges()
      
      const skeletonElement = fixture.nativeElement.querySelector('.skeleton')
      expect(skeletonElement.style.width).toBe('200px')
      expect(skeletonElement.style.height).toBe('100px')
    })
  })
})
</file>

<file path="app/shared/components/skeleton/skeleton.component.ts">
import { Component, Input, ChangeDetectionStrategy } from '@angular/core'
import { CommonModule } from '@angular/common'

export type SkeletonVariant = 'text' | 'rect' | 'circle' | 'avatar' | 'button' | 'card' | 'paragraph'

export interface SkeletonConfig {
  variant: SkeletonVariant
  width?: string | number
  height?: string | number
  count?: number
  rounded?: boolean
  animated?: boolean
}

/**
 * Componente de skeleton para estados de carregamento
 * Uso: <app-skeleton variant="card" [count]="3" />
 */
@Component({
  selector: 'app-skeleton',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="skeleton-wrapper" [class.animated]="animated">
      @for (i of counter; track i) {
        <div 
          class="skeleton"
          [class.skeleton-text]="variant === 'text'"
          [class.skeleton-rect]="variant === 'rect'"
          [class.skeleton-circle]="variant === 'circle'"
          [class.skeleton-avatar]="variant === 'avatar'"
          [class.skeleton-button]="variant === 'button'"
          [class.skeleton-card]="variant === 'card'"
          [class.skeleton-paragraph]="variant === 'paragraph'"
          [class.rounded]="rounded"
          [style.width]="getWidth()"
          [style.height]="getHeight()">
        </div>
      }
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    .skeleton-wrapper {
      display: block;
    }

    .skeleton {
      background: linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 37%, #f3f4f6 63%);
      background-size: 400% 100%;
      display: inline-block;
      vertical-align: middle;
      overflow: hidden;
      position: relative;
    }

    .skeleton.rounded {
      border-radius: 6px;
    }

    .animated .skeleton {
      animation: shimmer 1.4s ease infinite;
    }

    .skeleton-text {
      height: 1em;
      width: 100%;
      margin-bottom: 0.5em;
      border-radius: 4px;
    }

    .skeleton-rect {
      border-radius: 4px;
    }

    .skeleton-circle,
    .skeleton-avatar {
      border-radius: 50%;
      width: 40px;
      height: 40px;
    }

    .skeleton-avatar {
      width: 48px;
      height: 48px;
    }

    .skeleton-button {
      width: 64px;
      height: 36px;
      border-radius: 4px;
    }

    .skeleton-card {
      width: 100%;
      height: 120px;
      border-radius: 8px;
      margin-bottom: 12px;
    }

    .skeleton-paragraph {
      width: 100%;
      height: 12px;
      margin-bottom: 8px;
      border-radius: 4px;
    }

    .skeleton-paragraph:last-child {
      width: 80%;
    }

    @keyframes shimmer {
      0% {
        background-position: 100% 0;
      }
      100% {
        background-position: -100% 0;
      }
    }

    /* Tamanhos padrão por variante */
    .skeleton-text {
      width: 100%;
      max-width: 200px;
    }

    .skeleton-rect {
      width: 100%;
      max-width: 300px;
      height: 100px;
    }
  `]
})
export class SkeletonComponent {
  @Input() variant: SkeletonVariant = 'text'
  @Input() width?: string | number
  @Input() height?: string | number
  @Input() count = 1
  @Input() rounded = false
  @Input() animated = true

  get counter(): number[] {
    return Array(this.count).fill(0).map((_, i) => i)
  }

  getWidth(): string {
    if (this.width) {
      return typeof this.width === 'number' ? `${this.width}px` : this.width
    }
    return 'auto'
  }

  getHeight(): string {
    if (this.height) {
      return typeof this.height === 'number' ? `${this.height}px` : this.height
    }
    return 'auto'
  }
}
</file>

<file path="app/shared/components/ui/button/button.component.ts">
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export type ButtonVariant = 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
export type ButtonSize = 'default' | 'sm' | 'lg' | 'icon';

@Component({
    selector: 'button[ui-button], a[ui-button]',
    standalone: true,
    imports: [CommonModule],
    template: `<ng-content></ng-content>`,
    host: {
        '[class]': 'classes'
    }
})
export class UiButtonComponent {
    @Input() variant: ButtonVariant = 'default';
    @Input() size: ButtonSize = 'default';
    @Input('class') userClass = '';

    get classes() {
        return cn(
            'inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
            {
                'bg-primary text-primary-foreground hover:bg-primary/90': this.variant === 'default',
                'bg-destructive text-destructive-foreground hover:bg-destructive/90': this.variant === 'destructive',
                'border border-input bg-background hover:bg-accent hover:text-accent-foreground': this.variant === 'outline',
                'bg-secondary text-secondary-foreground hover:bg-secondary/80': this.variant === 'secondary',
                'hover:bg-accent hover:text-accent-foreground': this.variant === 'ghost',
                'text-primary underline-offset-4 hover:underline': this.variant === 'link',
                'h-10 px-4 py-2': this.size === 'default',
                'h-9 rounded-md px-3': this.size === 'sm',
                'h-11 rounded-md px-8': this.size === 'lg',
                'h-10 w-10': this.size === 'icon',
            },
            this.userClass
        );
    }
}
</file>

<file path="app/shared/components/ui/dialog/dialog-container.component.ts">
import { Component, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CdkPortalOutlet, PortalModule } from '@angular/cdk/portal';
import { A11yModule } from '@angular/cdk/a11y';

@Component({
    selector: 'ui-dialog-container',
    standalone: true,
    imports: [CommonModule, PortalModule, A11yModule],
    template: `
    <div 
      cdkTrapFocus
      cdkTrapFocusAutoCapture
      class="bg-white dark:bg-zinc-900 text-slate-900 dark:text-slate-50 border border-slate-200 dark:border-slate-800 rounded-lg shadow-lg w-full max-w-lg p-6 grid gap-4 animate-in fade-in-0 zoom-in-95 duration-200"
      tabindex="-1">
      <ng-template cdkPortalOutlet></ng-template>
    </div>
  `,
    // Encapsulation none so we can style from global if needed, but Tailwind classes are scoped enough usually.
    // Actually, default is Emulated which is fine.
    styles: [`
    :host {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 1rem;
        height: 100%;
        max-height: 100dvh;
        pointer-events: none; /* Let clicks pass through if we want custom backdrop handling, but here we want blocks */
    }
    
    div[cdkTrapFocus] {
        pointer-events: auto;
    }
  `]
})
export class UiDialogContainerComponent {
    @ViewChild(CdkPortalOutlet, { static: true }) portalOutlet!: CdkPortalOutlet;
}
</file>

<file path="app/shared/components/ui/dialog/dialog-ref.ts">
import { OverlayRef } from '@angular/cdk/overlay';
import { Subject, Observable } from 'rxjs';

export class UiDialogRef<R = any> {
    private _afterClosed = new Subject<R | undefined>();

    constructor(private overlayRef: OverlayRef) { }

    close(result?: R): void {
        this.overlayRef.dispose();
        this._afterClosed.next(result);
        this._afterClosed.complete();
    }

    afterClosed(): Observable<R | undefined> {
        return this._afterClosed.asObservable();
    }
}
</file>

<file path="app/shared/components/ui/dialog/dialog.service.ts">
import { Injectable, Injector } from '@angular/core';
import { Overlay, OverlayConfig } from '@angular/cdk/overlay';
import { ComponentPortal, ComponentType } from '@angular/cdk/portal';
import { UiDialogRef } from './dialog-ref';
import { UI_DIALOG_DATA } from './dialog.tokens';
import { UiDialogContainerComponent } from './dialog-container.component';

export interface DialogConfig<D = any> {
    data?: D;
    width?: string;
    disableClose?: boolean;
}

@Injectable({ providedIn: 'root' })
export class UiDialogService {
    constructor(private overlay: Overlay, private injector: Injector) { }

    open<T, D = any, R = any>(component: ComponentType<T>, config?: DialogConfig<D>): UiDialogRef<R> {
        const positionStrategy = this.overlay.position()
            .global()
            .centerHorizontally()
            .centerVertically();

        const overlayConfig = new OverlayConfig({
            hasBackdrop: true,
            backdropClass: ['bg-black/80', 'backdrop-blur-sm'],
            scrollStrategy: this.overlay.scrollStrategies.block(),
            positionStrategy,
            width: config?.width,
            panelClass: 'p-0' // Reset padding on the CDK pane itself
        });

        const overlayRef = this.overlay.create(overlayConfig);
        const dialogRef = new UiDialogRef<R>(overlayRef);

        // Create injector with data and ref
        const injector = Injector.create({
            parent: this.injector,
            providers: [
                { provide: UiDialogRef, useValue: dialogRef },
                { provide: UI_DIALOG_DATA, useValue: config?.data }
            ]
        });

        // Attach container
        const containerPortal = new ComponentPortal(UiDialogContainerComponent);
        const containerRef = overlayRef.attach(containerPortal);

        // Attach user component to container
        const userPortal = new ComponentPortal(component, null, injector);
        containerRef.instance.portalOutlet.attachComponentPortal(userPortal);

        // Close on backdrop click (if enabled)
        if (!config?.disableClose) {
            overlayRef.backdropClick().subscribe(() => dialogRef.close());
        }

        return dialogRef;
    }
}
</file>

<file path="app/shared/components/ui/dialog/dialog.tokens.ts">
import { InjectionToken } from '@angular/core';

export const UI_DIALOG_DATA = new InjectionToken<any>('UiDialogData');
</file>

<file path="app/shared/components/ui/icon/icon.component.ts">
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

@Component({
    selector: 'ui-icon',
    standalone: true,
    imports: [CommonModule],
    template: `
    <span 
      class="material-icons select-none"
      [class]="classes"
      [style.font-size.px]="size"
      aria-hidden="true">
      <ng-content></ng-content>
    </span>
  `
})
export class UiIconComponent {
    @Input() size?: number;
    @Input() class = '';

    get classes() {
        return cn(
            // Default size if not specified
            { 'text-base': !this.size },
            this.class
        );
    }
}
</file>

<file path="app/shared/components/ui/spinner/spinner.component.ts">
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

type SpinnerSize = number | 'sm' | 'md' | 'lg' | 'xl';

const SIZE_MAP: Record<'sm' | 'md' | 'lg' | 'xl', number> = {
    sm: 16,
    md: 24,
    lg: 32,
    xl: 48
};

@Component({
    selector: 'ui-spinner',
    standalone: true,
    imports: [CommonModule],
    template: `
    <div role="status" [class]="containerClasses" [style.width.px]="size" [style.height.px]="size">
        <svg
            class="animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            [class]="svgClasses"
        >
            <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
            ></circle>
            <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
        </svg>
        <span class="sr-only">Loading...</span>
    </div>
  `
})
export class UiSpinnerComponent {
    private sizePx = SIZE_MAP.md;

    @Input() set size(value: SpinnerSize) {
        this.sizePx = this.resolveSize(value);
    }

    get size(): number {
        return this.sizePx;
    }

    @Input() color: 'primary' | 'secondary' | 'accent' | 'muted' | 'white' | 'warn' = 'primary';
    @Input('class') userClass = '';

    // Adapter input for MatProgressSpinner compatibility
    @Input() set diameter(val: number) {
        if (val) this.sizePx = val;
    }

    get containerClasses() {
        return cn('inline-flex', this.userClass);
    }

    get svgClasses() {
        return cn('w-full h-full', {
            'text-primary': this.color === 'primary',
            'text-secondary': this.color === 'secondary',
            'text-accent': this.color === 'accent',
            'text-muted-foreground': this.color === 'muted',
            'text-white': this.color === 'white',
            'text-destructive': this.color === 'warn'
        });
    }

    private resolveSize(value: SpinnerSize): number {
        if (typeof value === 'number' && Number.isFinite(value)) {
            return value;
        }
        if (typeof value === 'string') {
            return SIZE_MAP[value] ?? SIZE_MAP.md;
        }
        return SIZE_MAP.md;
    }
}
</file>

<file path="app/shared/components/ui/system-hud/system-hud.html">
<div #hudRoot class="relative">
    <!-- Pulse Indicator (Always Visible) -->
    <div 
      #pulseIndicator
      (click)="toggleHud($event)"
      class="flex items-center cursor-pointer p-2 rounded-full hover:bg-white/10 transition-colors"
      title="Status do Sistema"
    >
      <div class="relative flex h-3 w-3">
        <span 
          class="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75"
          [ngClass]="(isHealthy$ | async) ? 'bg-green-400' : 'bg-red-500'"
        ></span>
        <span 
          class="relative inline-flex rounded-full h-3 w-3"
          [ngClass]="(isHealthy$ | async) ? 'bg-green-500' : 'bg-red-600'"
        ></span>
      </div>
      <span class="ml-2 text-xs font-mono text-gray-400 hidden md:block">SYSTEM</span>
    </div>
  
    <!-- HUD Panel (Dropdown) -->
    <div 
      *ngIf="isOpen" 
      #hudPanel
      (click)="$event.stopPropagation()"
      class="absolute right-0 top-full mt-2 w-80 bg-gray-900/95 backdrop-blur-md border border-gray-700 rounded-lg shadow-2xl z-50 overflow-hidden"
    >
      <!-- Header do HUD -->
      <div class="p-4 border-b border-gray-800 bg-black/40 flex justify-between items-center">
        <h3 class="text-sm font-bold text-gray-300 tracking-wider">SYSTEM MONITOR</h3>
        <span class="text-xs text-gray-500 font-mono">{{ (systemStatus$ | async)?.uptime_seconds | number:'1.0-0' }}s UPTIME</span>
      </div>
  
      <!-- Lista de Serviços -->
      <div class="p-2 space-y-1">
        <div 
          *ngFor="let service of (servicesHealth$ | async)?.services"
          class="hud-item flex items-center justify-between p-3 rounded hover:bg-white/5 transition-colors group"
        >
          <div class="flex items-center gap-3">
            <span class="text-xl filter grayscale group-hover:grayscale-0 transition-all">
              {{ getIconForService(service.key) }}
            </span>
            <div class="flex flex-col">
              <span class="text-sm font-medium text-gray-200">{{ service.name }}</span>
              <span class="text-xs text-gray-500">{{ service.metric_text }}</span>
            </div>
          </div>
          
          <div class="flex items-center gap-2">
            <span class="text-xs font-mono uppercase" [ngClass]="{
              'text-green-400': service.status === 'ok',
              'text-yellow-400': service.status === 'degraded',
              'text-red-400': service.status === 'error'
            }">{{ service.status }}</span>
            <div class="h-2 w-2 rounded-full" [ngClass]="getStatusColor(service.status)"></div>
          </div>
        </div>
      </div>
  
      <!-- Footer com Informações Técnicas -->
      <div class="p-3 bg-black/60 border-t border-gray-800 text-xs font-mono text-gray-600 flex justify-between">
        <span>v{{ (systemStatus$ | async)?.version }}</span>
        <span>{{ (systemStatus$ | async)?.environment }}</span>
      </div>
    </div>
  
  </div>
</file>

<file path="app/shared/components/ui/system-hud/system-hud.scss">

</file>

<file path="app/shared/components/ui/system-hud/system-hud.spec.ts">
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';

import { SystemHud } from './system-hud';

describe('SystemHud', () => {
  let component: SystemHud;
  let fixture: ComponentFixture<SystemHud>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SystemHud, HttpClientTestingModule]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SystemHud);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
</file>

<file path="app/shared/components/ui/system-hud/system-hud.ts">
import { Component, OnInit, ElementRef, ViewChild, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SystemStatusService, ServiceHealthResponse, SystemStatusResponse } from '../../../../core/services/system-status.service';
import { Observable } from 'rxjs';
import { gsap } from 'gsap';

@Component({
  selector: 'app-system-hud',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './system-hud.html',
  styleUrls: ['./system-hud.scss'],
})
export class SystemHud implements OnInit {
  @ViewChild('hudRoot') hudRoot?: ElementRef<HTMLElement>;
  @ViewChild('hudPanel') hudPanel?: ElementRef<HTMLElement>;
  @ViewChild('pulseIndicator') pulseIndicator?: ElementRef<HTMLElement>;

  isOpen = false;
  systemStatus$: Observable<SystemStatusResponse>;
  servicesHealth$: Observable<ServiceHealthResponse>;
  isHealthy$: Observable<boolean>;

  constructor(private statusService: SystemStatusService) {
    this.systemStatus$ = this.statusService.getSystemStatus();
    this.servicesHealth$ = this.statusService.getServicesHealth();
    this.isHealthy$ = this.statusService.isSystemHealthy$;
  }

  ngOnInit() {
    // Inicia animação de pulso contínuo
    // Nota: A animação real será feita via CSS para performance, 
    // mas usaremos GSAP para a abertura do painel.
  }

  toggleHud(event?: Event) {
    event?.stopPropagation();
    this.isOpen = !this.isOpen;
    
    if (this.isOpen) {
      this.animateOpen();
    } else {
      this.animateClose();
    }
  }

  private animateOpen() {
    // GSAP animation para entrada futurista
    setTimeout(() => {
      const panel = this.hudPanel?.nativeElement;
      if (panel) {
        gsap.fromTo(panel,
          { opacity: 0, y: -20, scale: 0.95 },
          { opacity: 1, y: 0, scale: 1, duration: 0.4, ease: 'back.out(1.7)' }
        );
        
        // Animar itens individualmente (stagger)
        const items = panel.querySelectorAll('.hud-item');
        if (items.length > 0) {
          gsap.fromTo(items,
            { opacity: 0, x: -20 },
            { opacity: 1, x: 0, duration: 0.3, stagger: 0.1, delay: 0.1 }
          );
        }
      }
    }, 0); // Tick para garantir renderização do *ngIf
  }

  private animateClose() {
    // A lógica de fechar é tratada pelo *ngIf, mas se quiséssemos animar a saída:
    // gsap.to(...) e depois setar isOpen = false no onComplete
  }

  getIconForService(key: string): string {
    switch (key) {
      case 'agent': return '🤖';
      case 'knowledge': return '📚';
      case 'memory': return '🧠';
      case 'llm': return '⚡';
      default: return '🔧';
    }
  }

  getStatusColor(status: string): string {
    switch (status) {
      case 'ok': return 'bg-green-500';
      case 'degraded': return 'bg-yellow-500';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: Event): void {
    if (!this.isOpen) return;
    const root = this.hudRoot?.nativeElement;
    const target = event.target as Node | null;
    if (root && target && !root.contains(target)) {
      this.isOpen = false;
    }
  }
}
</file>

<file path="app/shared/components/ui/toast/toast.component.ts">
import { Component, EventEmitter, Input, OnInit, Output, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastData } from './toast.types';
import { UiIconComponent } from '../icon/icon.component';
import { UiButtonComponent } from '../button/button.component';
import { animate, style, transition, trigger } from '@angular/animations';

@Component({
    selector: 'ui-toast',
    standalone: true,
    imports: [CommonModule, UiIconComponent, UiButtonComponent],
    template: `
    <div class="pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-6 pr-8 shadow-lg transition-all"
         [class]="getClasses()">
      
      <div class="flex items-center gap-3">
         @if (getIcon()) {
           <ui-icon [class]="getIconClass()">{{ getIcon() }}</ui-icon>
         }
         <div class="grid gap-1">
            <p class="text-sm font-semibold opacity-90">{{ data.message }}</p>
         </div>
      </div>

      <div class="flex items-center gap-2">
         @if (data.action) {
           <button ui-button variant="outline" size="sm" (click)="onAction()">
               {{ data.action }}
           </button>
         }
         
         <button ui-button variant="ghost" size="icon" class="h-6 w-6 text-foreground/50 hover:text-foreground" (click)="onClose()">
            <ui-icon class="scale-75">close</ui-icon>
         </button>
      </div>
    </div>
  `,
    styles: [`
    :host {
        display: block;
        width: 100%;
    }
  `],
    host: {
        '[@toastState]': 'true',
        'role': 'alert'
    },
    animations: [
        trigger('toastState', [
            transition(':enter', [
                style({ transform: 'translateX(100%)', opacity: 0 }),
                animate('150ms ease-out', style({ transform: 'translateX(0)', opacity: 1 }))
            ]),
            transition(':leave', [
                animate('150ms ease-in', style({ opacity: 0, transform: 'translateX(100%)' }))
            ])
        ])
    ]
})
export class UiToastComponent implements OnInit, OnDestroy {
    @Input({ required: true }) data!: ToastData;
    @Output() close = new EventEmitter<void>();

    private timeout: any;

    ngOnInit() {
        if (this.data.duration && this.data.duration > 0) {
            this.timeout = setTimeout(() => {
                this.onClose();
            }, this.data.duration);
        }
    }

    ngOnDestroy() {
        if (this.timeout) clearTimeout(this.timeout);
    }

    onClose() {
        this.close.emit();
    }

    onAction() {
        if (this.data.actionCallback) {
            this.data.actionCallback();
        }
        this.onClose(); // Automatically close on action? Usually yes.
    }

    getClasses(): string {
        const base = 'group pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-6 pr-8 shadow-lg transition-all';

        switch (this.data.type || 'default') {
            case 'default':
                return `${base} border bg-background text-foreground`;
            case 'destructive':
            case 'error':
                return `${base} destructive group border-destructive bg-destructive text-destructive-foreground`;
            case 'success':
                return `${base} border-green-500 bg-green-50 text-green-900 dark:bg-green-900/20 dark:text-green-100`;
            case 'warning':
                return `${base} border-yellow-500 bg-yellow-50 text-yellow-900 dark:bg-yellow-900/20 dark:text-yellow-100`;
            case 'info':
                return `${base} border-blue-500 bg-blue-50 text-blue-900 dark:bg-blue-900/20 dark:text-blue-100`;
            default:
                return `${base} border bg-background text-foreground`;
        }
    }

    getIcon(): string | null {
        switch (this.data.type) {
            case 'error': return 'error';
            case 'destructive': return 'error';
            case 'success': return 'check_circle';
            case 'warning': return 'warning';
            case 'info': return 'info';
            default: return null;
        }
    }

    getIconClass(): string {
        // styles handled by container variant mostly, but icons might need specific coloring in default mode if we want,
        // but 'default' usually has no icon or neutral.
        if (this.data.type === 'default') return '';
        return ''; // inherited from text color
    }
}
</file>

<file path="app/shared/components/ui/toast/toast.service.ts">
import { Injectable } from '@angular/core';
import { Overlay, OverlayRef } from '@angular/cdk/overlay';
import { ComponentPortal } from '@angular/cdk/portal';
import { UiToasterComponent } from './toaster.component';
import { ToastConfig } from './toast.types';

@Injectable({ providedIn: 'root' })
export class UiToastService {
    private overlayRef?: OverlayRef;
    private toaster?: UiToasterComponent;

    constructor(private overlay: Overlay) { }

    show(config: ToastConfig) {
        this.ensureToaster();
        this.toaster?.add({
            ...config,
            id: Date.now() + Math.random()
        });
    }

    success(message: string, duration = 5000) {
        this.show({ message, type: 'success', duration });
    }

    error(message: string, duration = 5000) {
        this.show({ message, type: 'error', duration });
    }

    info(message: string, duration = 5000) {
        this.show({ message, type: 'info', duration });
    }

    warning(message: string, duration = 5000) {
        this.show({ message, type: 'warning', duration });
    }

    private ensureToaster() {
        if (this.toaster) return;

        this.overlayRef = this.overlay.create({
            panelClass: 'toast-overlay-container',
            hasBackdrop: false,
            positionStrategy: this.overlay.position().global(),
            scrollStrategy: this.overlay.scrollStrategies.noop()
        });

        const portal = new ComponentPortal(UiToasterComponent);
        const ref = this.overlayRef.attach(portal);
        this.toaster = ref.instance;
    }
}
</file>

<file path="app/shared/components/ui/toast/toast.types.ts">
export type ToastType = 'default' | 'success' | 'error' | 'warning' | 'info' | 'destructive';

export interface ToastConfig {
    message: string;
    type?: ToastType;
    duration?: number;
    action?: string;
    actionCallback?: () => void;
}

export interface ToastData extends ToastConfig {
    id: number;
}
</file>

<file path="app/shared/components/ui/toast/toaster.component.ts">
import { Component, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UiToastComponent } from './toast.component';
import { ToastData } from './toast.types';

@Component({
    selector: 'ui-toaster',
    standalone: true,
    imports: [CommonModule, UiToastComponent],
    template: `
    <div class="fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]">
      @for (toast of toasts; track toast.id) {
        <ui-toast 
          [data]="toast" 
          (close)="remove(toast.id)">
        </ui-toast>
      }
    </div>
  `,
    changeDetection: ChangeDetectionStrategy.OnPush
})
export class UiToasterComponent {
    toasts: ToastData[] = [];

    constructor(private cdr: ChangeDetectorRef) { }

    add(toast: ToastData) {
        this.toasts.push(toast);
        this.cdr.markForCheck();
    }

    remove(id: number) {
        this.toasts = this.toasts.filter(t => t.id !== id);
        this.cdr.markForCheck();
    }
}
</file>

<file path="app/shared/components/ui/ui-badge/ui-badge.component.html">
<span class="badge" [ngClass]="['badge-' + variant]">
    <ng-content></ng-content>
</span>
</file>

<file path="app/shared/components/ui/ui-badge/ui-badge.component.scss">
:host {
    display: inline-flex;
}
</file>

<file path="app/shared/components/ui/ui-badge/ui-badge.component.ts">
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'ui-badge',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './ui-badge.component.html',
    styleUrls: ['./ui-badge.component.scss']
})
export class UiBadgeComponent {
    @Input() variant: 'neutral' | 'success' | 'warning' | 'error' | 'info' = 'neutral';
}
</file>

<file path="app/shared/components/ui/ui-button/ui-button.directive.ts">
import { Directive, Input, HostBinding } from '@angular/core';

@Directive({
    selector: 'button[uiButton], a[uiButton]',
    standalone: true
})
export class UiButtonDirective {
    @Input() variant: 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline' = 'primary';
    @Input() size: 'sm' | 'md' | 'lg' = 'md';
    @Input() fullWidth = false;

    @HostBinding('class.btn') baseClass = true;

    @HostBinding('class.btn-primary') get isPrimary() { return this.variant === 'primary'; }
    @HostBinding('class.btn-secondary') get isSecondary() { return this.variant === 'secondary'; }
    @HostBinding('class.btn-danger') get isDanger() { return this.variant === 'danger'; }
    @HostBinding('class.btn-ghost') get isGhost() { return this.variant === 'ghost'; }
    @HostBinding('class.btn-outline') get isOutline() { return this.variant === 'outline'; }

    @HostBinding('class.btn-sm') get isSmall() { return this.size === 'sm'; }
    @HostBinding('class.btn-lg') get isLarge() { return this.size === 'lg'; }

    @HostBinding('class.w-full') get isFullWidth() { return this.fullWidth; } // Assuming utility class exists or we style it
}
</file>

<file path="app/shared/components/ui/ui-card/ui-card.component.html">
<div class="card" [ngClass]="variant">
    <!-- Header Area (Optional) -->
    @if (title || subtitle || hasHeaderActions) {
        <div class="card-header">
            <div class="header-content">
                @if (title) {
                    <h3>{{ title }}</h3>
                }
                @if (subtitle) {
                    <p class="subtitle">{{ subtitle }}</p>
                }
            </div>
            <div class="header-actions">
                <ng-content select="[header-actions]"></ng-content>
            </div>
        </div>
    }

    <!-- Body Area -->
    <div class="card-body">
        <ng-content></ng-content>
    </div>

    <!-- Footer Area (Optional) -->
    @if (hasFooter) {
        <div class="card-footer">
            <ng-content select="[footer]"></ng-content>
        </div>
    }
</div>
</file>

<file path="app/shared/components/ui/ui-card/ui-card.component.scss">
@use 'styles/tokens' as *;
@use 'styles/mixins' as *;

:host {
  display: block;
}

.card {
  background-color: var(--janus-bg-card);
  border: 1px solid var(--janus-border);
  border-radius: var(--janus-radius-lg);
  padding: 0; // Padding handled by internal sections for flexibility
  transition: var(--janus-transition-normal);
  color: var(--janus-text-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden; // Ensure rounded corners clip content

  &.elevated {
    border-color: var(--janus-border-active);
    box-shadow: var(--janus-shadow-glow);
    transform: translateY(-2px);
  }

  &.glass {
    @include glass-panel;
  }
}

.card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--janus-spacing-md) var(--janus-spacing-lg);
    border-bottom: 1px solid var(--janus-border);
    background: rgba(255, 255, 255, 0.02);

    .header-content {
        h3 {
            margin: 0;
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--janus-text-primary);
        }

        .subtitle {
            margin: 0;
            font-size: 0.875rem;
            color: var(--janus-text-secondary);
            margin-top: 4px;
        }
    }
}

.card-body {
    flex: 1;
    padding: var(--janus-spacing-lg);
    color: var(--janus-text-secondary);
    line-height: 1.6;
}

.card-footer {
    padding: var(--janus-spacing-md) var(--janus-spacing-lg);
    border-top: 1px solid var(--janus-border);
    background: rgba(255, 255, 255, 0.02);
}
</file>

<file path="app/shared/components/ui/ui-card/ui-card.component.ts">
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'ui-card',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './ui-card.component.html',
    styleUrls: ['./ui-card.component.scss']
})
export class UiCardComponent {
    @Input() title?: string;
    @Input() subtitle?: string;
    @Input() variant: 'default' | 'elevated' = 'default';

    // Helper getters to check content projection populated (simple check, implementation detail might need ElementRef if stricter check needed)
    // For now we assume typical usage triggers layout
    get hasHeaderActions(): boolean {
        // This is a limitation of simple ng-content, can't easily detect if projected. 
        // We will assume if title/subtitle missing but header-actions present, user ensures it looks right.
        // Ideally we use ContentChild to check, but let's keep it simple for Sprint 0.
        return true;
    }

    get hasFooter(): boolean {
        return true; // Simplification, rendering empty footer wrapper if unused is minor overhead
    }
}
</file>

<file path="app/shared/components/ui/ui-table/ui-table.component.html">
<div class="table-container" [class.overflow-auto]="responsive">
    <table class="table" [class.table-striped]="striped">
        <ng-content></ng-content>
    </table>
</div>
</file>

<file path="app/shared/components/ui/ui-table/ui-table.component.scss">
:host {
    display: block;
    width: 100%;
}
</file>

<file path="app/shared/components/ui/ui-table/ui-table.component.ts">
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'ui-table',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './ui-table.component.html',
    styleUrls: ['./ui-table.component.scss']
})
export class UiTableComponent {
    @Input() striped = false;
    @Input() responsive = true;
}
</file>

<file path="app/shared/components/ui/index.ts">
export * from './ui-card/ui-card.component';
export * from './ui-badge/ui-badge.component';
export * from './ui-button/ui-button.directive';
export * from './ui-table/ui-table.component';
</file>

<file path="app/shared/icons/icons.module.ts">
import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

@NgModule({
  imports: [CommonModule],
  exports: []
})
export class IconsModule { }
</file>

<file path="app/shared/pipes/markdown.pipe.ts">
import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { MarkdownService } from '../services/markdown.service';

@Pipe({
    name: 'markdown',
    standalone: true
})
export class MarkdownPipe implements PipeTransform {

    constructor(
        private markdownService: MarkdownService,
        private sanitizer: DomSanitizer
    ) { }

    transform(value: string | object | null | undefined): SafeHtml {
        if (value === null || value === undefined) return '';

        let content = '';
        if (typeof value === 'string') {
            content = value;
        } else if (typeof value === 'object') {
            try {
                content = JSON.stringify(value, null, 2);
                content = '```json\n' + content + '\n```';
            } catch (e) {
                content = String(value);
            }
        } else {
            content = String(value);
        }

        const parsedHtml = this.markdownService.parse(content);
        // Trust the HTML because we already sanitized it with DOMPurify in the service
        return this.sanitizer.bypassSecurityTrustHtml(parsedHtml);
    }
}
</file>

<file path="app/shared/services/markdown.service.spec.ts">
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { marked } from 'marked'
import hljs from 'highlight.js'
import { MarkdownService } from './markdown.service'
import { AppLoggerService } from '../../core/services/app-logger.service'

describe('MarkdownService', () => {
  let service: MarkdownService
  const logger = {
    error: vi.fn(),
  }

  const rendererPrototype = marked.Renderer.prototype as { table: (...args: unknown[]) => string }
  const originalTable = rendererPrototype.table

  beforeEach(() => {
    vi.clearAllMocks()
    rendererPrototype.table = originalTable
    service = new MarkdownService(logger as unknown as AppLoggerService)
  })

  afterEach(() => {
    rendererPrototype.table = originalTable
    vi.restoreAllMocks()
  })

  it('renderiza tabela com assinatura atual do marked sem artefatos', () => {
    const markdown = [
      '| Coluna | Valor |',
      '| --- | --- |',
      '| status | ok |',
    ].join('\n')

    const html = service.parse(markdown)

    expect(html).toContain('table-container')
    expect(html).toContain('table table-striped')
    expect(html).not.toContain('[object Object]')
    expect(html).not.toContain('undefined')
  })

  it('faz fallback legado de tabela quando renderer nativo falha', () => {
    rendererPrototype.table = vi.fn(() => {
      throw new Error('forced-renderer-failure')
    })

    const serviceWithFallback = new MarkdownService(logger as unknown as AppLoggerService)
    const tableRenderer = ((marked as unknown as { defaults: { renderer: { table: (...args: unknown[]) => string } } }).defaults.renderer.table)
    const html = tableRenderer('<tr><th>Coluna</th></tr>', '<tr><td>ok</td></tr>')

    expect(html).toContain('table-container')
    expect(html).toContain('table table-striped')
    expect(html).not.toContain('[object Object]')
    expect(html).not.toContain('undefined')
    expect(serviceWithFallback).toBeTruthy()
  })

  it('renderiza fence code normal com lang-label coerente', () => {
    const markdown = ['```typescript', 'const x = 1', '```'].join('\n')
    const html = service.parse(markdown)

    expect(html).toContain('code-block-wrapper')
    expect(html).toContain('lang-label')
    expect(html).toContain('typescript')
    expect(html).not.toContain('[object Object]')
  })

  it('renderiza token object de code sem vazar [object Object]', () => {
    const renderer = (marked as unknown as { defaults: { renderer: { code: (code: unknown, languageHint?: string) => string } } }).defaults.renderer
    const html = renderer.code({ text: 'print("ok")', language: 'python' })

    expect(html).toContain('code-block-wrapper')
    expect(html).toContain('lang-label')
    expect(html).toContain('python')
    expect(html).not.toContain('[object Object]')
  })

  it('degrada para pre/code quando highlight falha', () => {
    vi.spyOn(hljs, 'highlight').mockImplementation(() => {
      throw new Error('highlight-failed')
    })

    const markdown = ['```invalid-lang', 'const y = 2', '```'].join('\n')
    const html = service.parse(markdown)

    expect(html).toContain('<pre><code>')
    expect(html).toContain('const y = 2')
  })
})
</file>

<file path="app/shared/services/markdown.service.ts">
import { Injectable } from '@angular/core';
import { marked } from 'marked';
import { default as DOMPurify } from 'dompurify';
import hljs from 'highlight.js';
import { AppLoggerService } from '../../core/services/app-logger.service';

@Injectable({
    providedIn: 'root'
})
export class MarkdownService {

    constructor(private readonly logger: AppLoggerService) {
        this.configureMarked();
    }

    private configureMarked(): void {
        // Custom renderer for robust code block handling
        const renderer: any = new marked.Renderer();
        const defaultRenderer: any = new marked.Renderer();

        renderer.code = (code: unknown, languageHint?: string) => {
            let text = '';
            let lang = '';

            if (typeof code === 'string') {
                text = code;
                lang = languageHint || '';
            } else if (code && typeof code === 'object') {
                const maybeToken = code as { text?: unknown; lang?: unknown; language?: unknown; raw?: unknown };
                if (typeof maybeToken.text === 'string') {
                    text = maybeToken.text;
                } else if (typeof maybeToken.raw === 'string') {
                    text = maybeToken.raw;
                } else {
                    try {
                        text = JSON.stringify(maybeToken, null, 2);
                    } catch {
                        text = String(maybeToken);
                    }
                }

                if (typeof maybeToken.lang === 'string') lang = maybeToken.lang;
                else if (typeof maybeToken.language === 'string') lang = maybeToken.language;
                else lang = languageHint || '';
            } else {
                text = String(code ?? '');
                lang = languageHint || '';
            }

            const normalizedText = String(text || '').replace(/\[\s*object\s+object\s*\]/gi, '').trimEnd();
            const validLang = lang && hljs.getLanguage(lang) ? lang : 'plaintext';
            try {
                const highlighted = hljs.highlight(normalizedText, { language: validLang }).value;
                return `<div class="code-block-wrapper">
                   <div class="code-header">
                     <span class="lang-label">${validLang}</span>
                   </div>
                   <pre><code class="hljs language-${validLang}">${highlighted}</code></pre>
                 </div>`;
            } catch (e) {
                return `<pre><code>${normalizedText}</code></pre>`;
            }
        };

        renderer.table = (...args: unknown[]) => {
            try {
                // Delegate to Marked's native renderer to stay compatible with v4/v5/v6 signatures.
                const rendered = String(defaultRenderer.table(...args) || '').trim();
                if (rendered) {
                    const withClasses = /<table[^>]*class=/i.test(rendered)
                        ? rendered
                        : rendered.replace(/<table>/i, '<table class="table table-striped">');
                    return `<div class="table-container">${withClasses}</div>`;
                }
            } catch {
                // Fallback to legacy signature handling below.
            }

            const header = typeof args[0] === 'string' ? args[0] : '';
            const body = typeof args[1] === 'string' ? args[1] : '';
            return `<div class="table-container"><table class="table table-striped">
                    <thead>${header}</thead>
                    <tbody>${body}</tbody>
                </table></div>`;
        };

        marked.setOptions({
            renderer,
            gfm: true,
            breaks: true
        });
    }

    /**
     * Parses markdown text to safe HTML
     * @param rawMarkdown The markdown string from LLM
     * @returns Sanitized HTML string
     */
    public parse(rawMarkdown: string): string {
        if (!rawMarkdown) return '';

        try {
            const html = marked.parse(rawMarkdown) as string;
            // Sanitize specifically allowing standard formatting tags and our custom code classes
            const cleanHtml = DOMPurify.sanitize(html, {
                ADD_TAGS: ['img', 'pre', 'code', 'table', 'thead', 'tbody', 'tr', 'td', 'th', 'div', 'span'],
                ADD_ATTR: ['class', 'src', 'alt', 'href', 'target']
            });

            return cleanHtml;
        } catch (error) {
            this.logger.error('[MarkdownService] Markdown parsing error', error);
            return rawMarkdown; // Fail gentle or return error message
        }
    }
}
</file>

<file path="app/shared/services/ui.service.ts">
import { Injectable } from '@angular/core'
import { FormGroup } from '@angular/forms'
import { UiToastService } from '../components/ui/toast/toast.service'
import { ToastType } from '../components/ui/toast/toast.types'
import { UiDialogService, DialogConfig } from '../components/ui/dialog/dialog.service'
import { UiDialogRef } from '../components/ui/dialog/dialog-ref'
import { Observable } from 'rxjs'
import { LoadingDialogComponent } from '../components/loading-dialog/loading-dialog.component'
import { ConfirmDialogComponent } from '../components/confirm-dialog/confirm-dialog.component'

export interface ToastConfig {
  message: string
  action?: string
  duration?: number
  panelClass?: string
  horizontalPosition?: 'start' | 'center' | 'end' | 'left' | 'right'
  verticalPosition?: 'top' | 'bottom'
}

export interface ConfirmDialogData {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  confirmColor?: 'primary' | 'warn' | 'accent'
}

export interface LoadingDialogConfig {
  message?: string
  disableClose?: boolean
}

@Injectable({
  providedIn: 'root'
})
export class UiService {
  // activeToasts managed by UiToastService
  private activeLoadingDialogs: UiDialogRef<void>[] = []

  constructor(
    private toastService: UiToastService,
    private dialogService: UiDialogService
  ) { }

  // Toast/Snackbar methods
  showToast(config: ToastConfig): void {
    let type: ToastType = 'default'

    if (config.panelClass?.includes('success')) type = 'success'
    else if (config.panelClass?.includes('error')) type = 'error'
    else if (config.panelClass?.includes('warning')) type = 'warning'
    else if (config.panelClass?.includes('info')) type = 'info'

    this.toastService.show({
      message: config.message,
      type,
      duration: config.duration || 3000,
      action: config.action
    })
  }

  showSuccess(message: string, action?: string): void {
    this.showToast({
      message,
      action,
      duration: 4000,
      panelClass: 'success-toast'
    })
  }

  showError(message: string, action?: string): void {
    this.showToast({
      message,
      action,
      duration: 6000,
      panelClass: 'error-toast'
    })
  }

  showWarning(message: string, action?: string): void {
    this.showToast({
      message,
      action,
      duration: 5000,
      panelClass: 'warning-toast'
    })
  }

  showInfo(message: string, action?: string): void {
    this.showToast({
      message,
      action,
      duration: 4000,
      panelClass: 'info-toast'
    })
  }

  // Loading dialog methods
  showLoading(config?: LoadingDialogConfig): UiDialogRef<void> {
    const dialogConfig: DialogConfig = {
      disableClose: config?.disableClose !== false,
      data: { message: config?.message || 'Carregando...' }
      // panelClass handled by service default or can add here if UiService supports it
    }

    const loadingRef = this.dialogService.open(LoadingDialogComponent, dialogConfig)
    this.activeLoadingDialogs.push(loadingRef)

    loadingRef.afterClosed().subscribe(() => {
      const index = this.activeLoadingDialogs.indexOf(loadingRef)
      if (index > -1) {
        this.activeLoadingDialogs.splice(index, 1)
      }
    })

    return loadingRef
  }

  hideLoading(): void {
    this.activeLoadingDialogs.forEach(dialog => {
      if (dialog) {
        dialog.close()
      }
    })
    this.activeLoadingDialogs = []
  }

  // Confirmation dialog
  showConfirm(data: ConfirmDialogData): Observable<boolean> {
    const dialogConfig: DialogConfig = {
      width: '400px',
      data
    }

    const dialogRef = this.dialogService.open(ConfirmDialogComponent, dialogConfig)
    return dialogRef.afterClosed() as Observable<boolean>
  }

  // Utility methods
  dismissAllToasts(): void {
    // Not implemented in UiToastService yet, strict requirement? 
    // Usually toasts auto-dismiss. 
    // We can implement clear() in UiToastService if needed.
  }

  dismissAllDialogs(): void {
    // UiDialogService doesn't have closeAll yet, but we track loading dialogs.
    // Ideally UiDialogService should track open dialogs.
    // For now, just clear loading dialogs. To fully replace MatDialog.closeAll(), 
    // we would need to implement it in UiDialogService.
    this.activeLoadingDialogs.forEach(d => d.close())
    this.activeLoadingDialogs = []
  }

  // Form validation helpers
  getFormValidationErrors(formGroup: FormGroup): string[] {
    const errors: string[] = []

    Object.keys(formGroup.controls).forEach(key => {
      const control = formGroup.get(key)
      const controlErrors = control?.errors
      if (controlErrors != null) {
        Object.keys(controlErrors).forEach(keyError => {
          errors.push(this.getValidationErrorMessage(key, keyError, controlErrors[keyError]))
        })
      }
    })

    return errors
  }

  private getValidationErrorMessage(fieldName: string, errorType: string, errorValue: unknown): string {
    const fieldNameMap: Record<string, string> = {
      'email': 'Email',
      'password': 'Senha',
      'name': 'Nome',
      'username': 'Nome de usuário',
      'phone': 'Telefone',
      'cpf': 'CPF',
      'cnpj': 'CNPJ'
    }

    const friendlyFieldName = fieldNameMap[fieldName] || fieldName
    const errObj = errorValue as { requiredLength?: number }

    switch (errorType) {
      case 'required':
        return `${friendlyFieldName} é obrigatório`
      case 'email':
        return `Por favor, insira um email válido`
      case 'minlength':
        return `${friendlyFieldName} deve ter no mínimo ${errObj.requiredLength} caracteres`
      case 'maxlength':
        return `${friendlyFieldName} deve ter no máximo ${errObj.requiredLength} caracteres`
      case 'pattern':
        return `${friendlyFieldName} está em formato inválido`
      case 'mustMatch':
        return 'As senhas não coincidem'
      default:
        return `${friendlyFieldName} é inválido`
    }
  }

  // File upload helpers
  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes'

    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))

    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  validateFile(file: File, allowedTypes: string[], maxSizeInMB: number): { valid: boolean; error?: string } {
    // Check file type
    if (allowedTypes.length > 0 && !allowedTypes.some(type =>
      file.type === type || file.name.toLowerCase().endsWith(type.toLowerCase())
    )) {
      return {
        valid: false,
        error: `Tipo de arquivo não permitido. Tipos permitidos: ${allowedTypes.join(', ')}`
      }
    }

    // Check file size
    const maxSizeInBytes = maxSizeInMB * 1024 * 1024
    if (file.size > maxSizeInBytes) {
      return {
        valid: false,
        error: `Arquivo muito grande. Tamanho máximo: ${maxSizeInMB}MB`
      }
    }

    return { valid: true }
  }

  // Date/Time helpers
  formatDate(date: Date | string, format: string = 'dd/MM/yyyy'): string {
    const dateObj = typeof date === 'string' ? new Date(date) : date

    if (isNaN(dateObj.getTime())) {
      return ''
    }

    const day = dateObj.getDate().toString().padStart(2, '0')
    const month = (dateObj.getMonth() + 1).toString().padStart(2, '0')
    const year = dateObj.getFullYear()

    switch (format) {
      case 'dd/MM/yyyy':
        return `${day}/${month}/${year}`
      case 'MM/dd/yyyy':
        return `${month}/${day}/${year}`
      case 'yyyy-MM-dd':
        return `${year}-${month}-${day}`
      default:
        return `${day}/${month}/${year}`
    }
  }

  formatCurrency(value: number, currency: string = 'BRL'): string {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: currency
    }).format(value)
  }

  // Loading state management
  createLoadingState(): {
    loading: boolean
    error: string | null
    setLoading: (loading: boolean) => void
    setError: (error: string | null) => void
    reset: () => void
  } {
    const state = {
      loading: false,
      error: null as string | null,
      setLoading: (loading: boolean) => { state.loading = loading },
      setError: (error: string | null) => { state.error = error },
      reset: () => {
        state.loading = false
        state.error = null
      }
    }
    return state
  }
}
</file>

<file path="app/shared/_index.scss">
/**
 * =============================================================================
 * JANUS DESIGN SYSTEM - Index
 * =============================================================================
 * 
 * Entry point for the Janus Design System.
 * Import this file to access all design tokens and mixins.
 * 
 * Usage in components:
 *   @use '@shared/design-system' as ds;
 *   
 *   .my-component {
 *     color: ds.$color-cyan;
 *     @include ds.glass-panel;
 *   }
 * 
 * =============================================================================
 */

// Forward new design system modules
@forward '../../../styles/tokens';
@forward '../../../styles/animations';
@forward '../../../styles/components';
</file>

<file path="app/shared/icon.component.ts">
import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ICONS, IconName } from './icons';

@Component({
  selector: 'app-icon',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span 
      class="icon-container"
      [class.spinning]="spin"
      [class.pulse]="pulse"
      [attr.aria-hidden]="ariaHidden"
      [attr.aria-label]="ariaLabel"
      [innerHTML]="iconSvg"
    ></span>
  `,
  styles: [`
    :host {
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
    
    .icon-container {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease-in-out;
    }
    
    .icon-container.spinning {
      animation: spin 1s linear infinite;
    }
    
    .icon-container.pulse {
      animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
    
    .icon-container :host-context(.button:hover) {
      transform: scale(1.1);
    }
    
    .icon-container :host-context(.button:active) {
      transform: scale(0.95);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class IconComponent {
  @Input() name!: IconName;
  @Input() size: 'xs' | 'sm' | 'md' | 'lg' | 'xl' = 'md';
  @Input() spin = false;
  @Input() pulse = false;
  @Input() ariaHidden = 'true';
  @Input() ariaLabel?: string;

  get iconSvg(): string {
    return ICONS[this.name] || '';
  }

  get iconClass(): string {
    const sizeMap = {
      xs: 'w-3 h-3',
      sm: 'w-4 h-4', 
      md: 'w-5 h-5',
      lg: 'w-6 h-6',
      xl: 'w-8 h-8'
    };
    return sizeMap[this.size];
  }
}
</file>

<file path="app/shared/icons.ts">
export const ICONS = {
  // Navigation
  arrowLeft: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
    <path stroke-linecap="round" stroke-linejoin="round" d="M15 19l-7-7 7-7" />
  </svg>`,
  
  // Actions
  send: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
    <path stroke-linecap="round" stroke-linejoin="round" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
  </svg>`,
  
  attachment: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
    <path stroke-linecap="round" stroke-linejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
  </svg>`,
  
  microphone: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
    <path stroke-linecap="round" stroke-linejoin="round" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
  </svg>`,
  
  stop: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
  </svg>`,
  
  copy: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
    <path stroke-linecap="round" stroke-linejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
  </svg>`,
  
  refresh: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
    <path stroke-linecap="round" stroke-linejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>`,
  
  settings: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
    <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
    <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
  </svg>`,
  
  close: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
    <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12" />
  </svg>`,
  
  // User Interface
  user: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
    <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
  </svg>`,
  
  // Document/Content
  document: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
    <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
  </svg>`,
  
  externalLink: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
    <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
  </svg>`,
  
  // Analytics
  chart: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
    <path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
  </svg>`,
  
  // Code
  code: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
    <path stroke-linecap="round" stroke-linejoin="round" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
  </svg>`,
  
  // Info
  info: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
    <path stroke-linecap="round" stroke-linejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>`,
  
  // Warning/Error
  error: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
    <path stroke-linecap="round" stroke-linejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>`,
  
  // Upload/Download
  upload: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-12 h-12">
    <path stroke-linecap="round" stroke-linejoin="round" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
  </svg>`,
  
  // Check/Circle
  check: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
    <path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>`,
  
  // Plus/Add
  plus: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
    <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
  </svg>`,
  
  // Trash
  trash: `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-4 h-4">
    <path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
  </svg>`
};

export type IconName = keyof typeof ICONS;
</file>

<file path="app/shared/README.md">
# Shared

Componentes, pipes e diretivas reutilizáveis.

Sugestões de conteúdo:
- Componentes UI comuns (botões, cards, tabelas)
- Pipes utilitários (formatação, máscaras)
- Diretivas reutilizáveis (focus, scroll, acessibilidade)
- Módulos compartilhados para importação em features
</file>

<file path="app/shared/shared.module.ts">
import { NgModule } from '@angular/core'
import { CommonModule } from '@angular/common'

// Services
import { UiService } from './services/ui.service'

import { ReactiveFormsModule } from '@angular/forms'

const MATERIAL_MODULES = [
  ReactiveFormsModule
]

@NgModule({
  imports: [
    CommonModule,
    ...MATERIAL_MODULES
  ],
  exports: [
    ...MATERIAL_MODULES
  ],
  providers: [
    UiService
  ]
})
export class SharedModule { }
</file>

<file path="app/app.config.ts">
import { ApplicationConfig, provideBrowserGlobalErrorListeners, provideZonelessChangeDetection, isDevMode, importProvidersFrom } from '@angular/core';
import { provideRouter, withInMemoryScrolling } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideServiceWorker } from '@angular/service-worker';
import { provideAnimations } from '@angular/platform-browser/animations';
import { TranslateModule } from '@ngx-translate/core';
import { provideTranslateHttpLoader } from '@ngx-translate/http-loader';
import { baseUrlInterceptor } from './core/interceptors/base-url.interceptor';
import { errorLoggerInterceptor } from './core/interceptors/error-logger.interceptor';
import { errorMappingInterceptor } from './core/interceptors/error-mapping.interceptor';
import { authInterceptor } from './core/interceptors/auth.interceptor';

import { routes } from './app.routes';
import { initializeApp, provideFirebaseApp } from '@angular/fire/app';
import { getDatabase, provideDatabase } from '@angular/fire/database';
import { getFirestore, provideFirestore } from '@angular/fire/firestore';
import { getAuth, provideAuth } from '@angular/fire/auth';
import { environment } from '../environments/environment';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),
    provideAnimations(),
    provideRouter(
      routes,
      withInMemoryScrolling({ scrollPositionRestoration: 'enabled' })
    ),
    provideHttpClient(withInterceptors([baseUrlInterceptor, authInterceptor, errorLoggerInterceptor, errorMappingInterceptor])),
    importProvidersFrom(
      TranslateModule.forRoot({
        fallbackLang: 'pt-BR'
      })
    ),
    provideTranslateHttpLoader({
      prefix: './assets/i18n/',
      suffix: '.json'
    }),

    // Firebase
    provideFirebaseApp(() => initializeApp(environment.firebase)),
    provideDatabase(() => getDatabase()),
    provideFirestore(() => getFirestore()),
    provideAuth(() => getAuth()),

    // Service Worker habilitado apenas em produção para evitar cache e abortos em dev
    provideServiceWorker('ngsw-worker.js', { enabled: !isDevMode(), registrationStrategy: 'registerWhenStable:30000' })
  ]
};
</file>

<file path="app/app.html">
<!-- Skip link for keyboard navigation -->
<a href="#main-content" class="skip-link">Skip to main content</a>

<!-- Ambient Background Orbs (decorative, hidden from screen readers) -->
<div class="ambient-orbs" aria-hidden="true">
    <div class="orb orb-1"></div>
    <div class="orb orb-2"></div>
    <div class="orb orb-3"></div>
</div>

<!-- Offline Banner with proper ARIA -->
@if (demoService.isOffline()) {
<div role="alert" aria-live="assertive"
    class="fixed bottom-0 left-0 w-full bg-yellow-600/90 text-white text-xs font-bold py-1 z-[9999] shadow-lg backdrop-blur-sm marquee-container border-t border-yellow-400/30">
    <div class="marquee-content">
        ⚠ JANUS OFFLINE / MODO DEMONSTRAÇÃO — BACKEND DESCONECTADO — SISTEMA OPERANDO EM ESTADO DE FUNCIONALIDADE
        REDUZIDA — ALGUNS RECURSOS PODEM ESTAR INDISPONÍVEIS ⚠
    </div>
</div>
}

<!-- Main Application with Semantic Structure -->
<main id="main-content" role="main">
    <router-outlet></router-outlet>
</main>
</file>

<file path="app/app.routes.ts">
import { Routes } from '@angular/router';
import { AuthGuard, RoleGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./features/auth/login/login').then(m => m.LoginComponent)
  },
  {
    path: 'conversations',
    loadComponent: () => import('./features/conversations/conversations').then(m => m.ConversationsComponent),
    canActivate: [AuthGuard],
    pathMatch: 'full'
  },
  {
    path: 'conversations/:conversationId',
    loadComponent: () => import('./features/conversations/conversations').then(m => m.ConversationsComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'tools',
    loadComponent: () => import('./features/tools/tools').then(m => m.ToolsComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'observability',
    loadComponent: () => import('./features/observability/observability').then(m => m.ObservabilityComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'admin/autonomia',
    loadComponent: () => import('./features/admin/autonomia/admin-autonomia').then(m => m.AdminAutonomiaComponent),
    canActivate: [AuthGuard, RoleGuard],
    data: { roles: ['admin'] }
  },
  {
    path: '',
    loadComponent: () => import('./features/home/home').then(m => m.HomeComponent),
    canActivate: [AuthGuard]
  },
  {
    path: 'home',
    redirectTo: '',
    pathMatch: 'full'
  },
  {
    path: 'registro',
    loadComponent: () => import('./features/auth/register/register').then(m => m.RegisterComponent)
  },
  {
    path: 'register',
    redirectTo: 'registro',
    pathMatch: 'full'
  },
  {
    path: '**',
    redirectTo: 'login'
  }
];
</file>

<file path="app/app.scss">
/* Existing styles preserved */

/* Skip Link for Keyboard Navigation */
.skip-link {
    position: absolute;
    top: -40px;
    left: 0;
    background: #4a90e2;
    color: white;
    padding: 8px 16px;
    text-decoration: none;
    border-radius: 0 0 4px 0;
    z-index: 100000;
    font-weight: bold;
}

.skip-link:focus {
    top: 0;
    outline: 3px solid #fff;
    outline-offset: 2px;
}

/* Animated Ambient Orbs */
.ambient-orbs {
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    overflow: hidden;
}

.ambient-orbs .orb {
    position: absolute;
    width: clamp(260px, 30vw, 520px);
    height: clamp(260px, 30vw, 520px);
    border-radius: 50%;
    filter: blur(35px);
    opacity: 0.32;
    mix-blend-mode: screen;
}

.ambient-orbs .orb-1 {
    top: -12%;
    left: -6%;
    background: radial-gradient(circle at 30% 30%, rgba(var(--janus-secondary-rgb), 0.45), transparent 65%);
    animation: orbFloatA 26s ease-in-out infinite;
}

.ambient-orbs .orb-2 {
    top: 10%;
    right: -8%;
    background: radial-gradient(circle at 40% 40%, rgba(var(--janus-accent-rgb), 0.35), transparent 70%);
    animation: orbFloatB 32s ease-in-out infinite;
}

.ambient-orbs .orb-3 {
    bottom: -18%;
    left: 20%;
    background: radial-gradient(circle at 35% 35%, rgba(var(--janus-primary-rgb), 0.3), transparent 70%);
    animation: orbFloatC 28s ease-in-out infinite;
}

@keyframes orbFloatA {
    0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
    50% { transform: translate3d(6%, 8%, 0) scale(1.05); }
}

@keyframes orbFloatB {
    0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
    50% { transform: translate3d(-8%, 6%, 0) scale(1.08); }
}

@keyframes orbFloatC {
    0%, 100% { transform: translate3d(0, 0, 0) scale(1); }
    50% { transform: translate3d(4%, -6%, 0) scale(1.04); }
}

/* Focus Visible for Keyboard Navigation */
*:focus-visible {
    outline: 2px solid #4a90e2;
    outline-offset: 2px;
}

/* Remove default outline for mouse users */
*:focus:not(:focus-visible) {
    outline: none;
}

/* Screen Reader Only Content */
.sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
}

/* High Contrast Mode Support */
@media (prefers-contrast: high) {
    * {
        border-color: currentColor !important;
    }
}

/* Reduced Motion Support */
@media (prefers-reduced-motion: reduce) {

    *,
    *::before,
    *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
}
</file>

<file path="app/app.spec.ts">
import {provideZonelessChangeDetection} from '@angular/core';
import {TestBed} from '@angular/core/testing';
import {App} from './app';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideZonelessChangeDetection()]
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should render skip link', () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    const skipLink = compiled.querySelector('a.skip-link');
    expect(skipLink).toBeTruthy();
    expect(skipLink?.getAttribute('href')).toBe('#main-content');
  });
});
</file>

<file path="app/app.ts">
import { Component, signal, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { DemoService } from './core/services/demo.service'
import { CommonModule } from '@angular/common'

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  protected readonly title = signal('janus-angular');
  public demoService = inject(DemoService);
}
</file>

<file path="environments/environment.prod.ts">
export const environment = {
  production: true,
  logging: {
    level: 'warn'
  },
  // Tailscale Funnel Configuration - Acesso público via Tailscale
  tailscale: {
    enabled: true, // Tailscale Funnel ativado para produção
    apiUrl: 'https://desktop-hjndm9g.tail041209.ts.net/api', // URL pública Tailscale Funnel
    frontendUrl: 'http://janus.arthinfo.com.br/' // URL do seu site na Locaweb
  },
  // Default API URL - Tailscale Funnel para produção
  apiUrl: 'https://desktop-hjndm9g.tail041209.ts.net/api',
  firebase: {
    apiKey: "AIzaSyBbxotMnYYpYsczUteKkx0yWiNFXf8_Y70",
    authDomain: "orbisfracta.firebaseapp.com",
    projectId: "orbisfracta",
    storageBucket: "orbisfracta.firebasestorage.app",
    messagingSenderId: "454482935240",
    appId: "1:454482935240:web:3b5c2e5d13f4c5c7c054fd",
    measurementId: "G-RHL0EHHGFV",
    databaseURL: "https://orbisfracta-default-rtdb.firebaseio.com/"
  }
};
</file>

<file path="environments/environment.ts">
export const environment = {
  production: false,
  logging: {
    level: 'debug'
  },
  // Tailscale Funnel Configuration - Acesso público via Tailscale
  tailscale: {
    enabled: true, // Tailscale Funnel ativado para acesso público
    apiUrl: '/api', // Usa o proxy local do frontend (funciona via localhost e via Tailscale IP)
    frontendUrl: 'http://localhost:4300'
  },
  // Default API URL - Tailscale Funnel para desenvolvimento
  apiUrl: '/api',
  firebase: {
    apiKey: "AIzaSyBbxotMnYYpYsczUteKkx0yWiNFXf8_Y70",
    authDomain: "orbisfracta.firebaseapp.com",
    projectId: "orbisfracta",
    storageBucket: "orbisfracta.firebasestorage.app",
    messagingSenderId: "454482935240",
    appId: "1:454482935240:web:3b5c2e5d13f4c5c7c054fd",
    measurementId: "G-RHL0EHHGFV",
    databaseURL: "https://orbisfracta-default-rtdb.firebaseio.com/"
  }
};
</file>

<file path="styles/_animations.scss">
/**
 * =============================================================================
 * JANUS ANIMATIONS - Subtle & Professional
 * =============================================================================
 *
 * Keyframe animations and transition utilities for "alive" feeling.
 * Designed to be smooth, professional, and not distracting.
 *
 * =============================================================================
 */

@use 'tokens' as *;

// =============================================================================
// KEYFRAME ANIMATIONS
// =============================================================================

// --- Pulse (for live indicators) ---
@keyframes pulse {

    0%,
    100% {
        opacity: 1;
        transform: scale(1);
    }

    50% {
        opacity: 0.7;
        transform: scale(0.95);
    }
}

// --- Fade In Up (staggered element entry) ---
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(16px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

// --- Fade In (simple) ---
@keyframes fadeIn {
    from {
        opacity: 0;
    }

    to {
        opacity: 1;
    }
}

// --- Skeleton Shimmer (loading states) ---
@keyframes shimmer {
    0% {
        background-position: -200% 0;
    }

    100% {
        background-position: 200% 0;
    }
}

// --- Spin (loading spinners) ---
@keyframes spin {
    from {
        transform: rotate(0deg);
    }

    to {
        transform: rotate(360deg);
    }
}

// --- Subtle Background Shift (ambient effect) ---
@keyframes ambientShift {

    0%,
    100% {
        background-position: 0% 50%;
    }

    50% {
        background-position: 100% 50%;
    }
}

// --- Grid Drift (background lattice) ---
@keyframes gridDrift {
    from {
        background-position: 0 0, 0 0;
    }

    to {
        background-position: 160px 160px, 160px 160px;
    }
}

// --- Plexus Float (subtle dot field) ---
@keyframes plexusFloat {

    0%,
    100% {
        opacity: 0.18;
        transform: translate3d(0, 0, 0);
    }

    50% {
        opacity: 0.28;
        transform: translate3d(0, -10px, 0);
    }
}

// --- Slide Down (dropdowns, menus) ---
@keyframes slideDown {
    from {
        opacity: 0;
        transform: translateY(-8px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

// --- Scale Up (modals) ---
@keyframes scaleUp {
    from {
        opacity: 0;
        transform: scale(0.95);
    }

    to {
        opacity: 1;
        transform: scale(1);
    }
}

// =============================================================================
// UTILITY CLASSES
// =============================================================================

// --- Pulse live indicator ---
.pulse-live {
    animation: pulse 2s ease-in-out infinite;
}

// --- Fade transitions ---
.fade-in {
    animation: fadeIn 0.3s ease-out;
}

.fade-in-up {
    animation: fadeInUp 0.5s ease-out;
}

// --- Staggered delays (for sequential animations) ---
.stagger-1 {
    animation-delay: 0.1s;
}

.stagger-2 {
    animation-delay: 0.2s;
}

.stagger-3 {
    animation-delay: 0.3s;
}

.stagger-4 {
    animation-delay: 0.4s;
}

.stagger-5 {
    animation-delay: 0.5s;
}

// --- Loading spinner ---
.spinner {
    animation: spin 1s linear infinite;
}

// =============================================================================
// MIXINS FOR COMMON ANIMATIONS
// =============================================================================

// --- Hover lift effect ---
@mixin hover-lift($distance: -2px) {
    transition: transform $transition-normal, box-shadow $transition-normal;

    &:hover:not(:disabled) {
        transform: translateY($distance);
        box-shadow: $shadow-lg;
    }
}

// --- Hover scale effect ---
@mixin hover-scale($scale: 1.02) {
    transition: transform $transition-fast;

    &:hover:not(:disabled) {
        transform: scale($scale);
    }
}

// --- Skeleton loading background ---
@mixin skeleton {
    background: linear-gradient(90deg,
            $color-bg-secondary 0%,
            $color-bg-tertiary 50%,
            $color-bg-secondary 100%);
    background-size: 200% 100%;
    animation: shimmer 1.5s ease-in-out infinite;
    border-radius: $radius-sm;
}

// --- Focus ring animation ---
@mixin focus-ring {
    transition: box-shadow $transition-fast;

    &:focus {
        outline: none;
        box-shadow: $shadow-accent;
    }
}

// =============================================================================
// BACKGROUND AMBIENT (for body/containers)
// =============================================================================

@mixin ambient-background {
    position: relative;

    &::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: -1;
        pointer-events: none;

        // Subtle radial gradients for depth
        background:
            radial-gradient(ellipse 70% 50% at 12% 20%,
                rgba(var(--janus-secondary-rgb), 0.1) 0%,
                transparent 55%),
            radial-gradient(ellipse 60% 45% at 85% 75%,
                rgba(var(--janus-accent-rgb), 0.08) 0%,
                transparent 60%),
            radial-gradient(ellipse 40% 30% at 40% 85%,
                rgba(var(--janus-primary-rgb), 0.06) 0%,
                transparent 55%);

        background-size: 200% 200%;
        animation: ambientShift 30s ease-in-out infinite;
    }
}
</file>

<file path="styles/_components.scss">
/**
 * =============================================================================
 * JANUS COMPONENTS - Clean Professional Styles
 * =============================================================================
 *
 * Base component styles (buttons, cards, inputs, tables, badges).
 * All components follow GitHub-inspired clean aesthetic.
 *
 * =============================================================================
 */

@use 'sass:map';
@use './tokens' as *;
@use './mixins' as *;

// =============================================================================
// COMPONENT STYLES
// =============================================================================

// --- Buttons ---
.btn {
    @include btn-base;
    
    // Sizes
    &.btn-sm {
        padding: 4px 8px;
        font-size: 0.75rem;
        gap: 4px;
    }

    &.btn-lg {
        padding: 12px 24px;
        font-size: 1rem;
        gap: 8px;
    }

    // Variants
    &.btn-primary {
        @include btn-primary;
    }
    
    &.btn-secondary {
        @include btn-secondary;
    }

    &.btn-outline {
        @include btn-outline;
    }

    &.btn-ghost {
        @include btn-ghost;
    }

    &.btn-danger {
        @include btn-danger;
    }
}

// --- Inputs ---
.input-group {
    display: flex;
    flex-direction: column;
    gap: var(--janus-spacing-xs);
    margin-bottom: var(--janus-spacing-md);
    
    label {
        font-size: 0.875rem;
        color: var(--janus-text-secondary);
        font-weight: 500;
    }
    
    input, textarea, select {
        background-color: var(--janus-bg-surface);
        border: 1px solid var(--janus-border);
        border-radius: var(--janus-radius-md);
        padding: var(--janus-spacing-sm) var(--janus-spacing-md);
        color: var(--janus-text-primary);
        transition: var(--janus-transition-fast);
        font-family: inherit;
        font-size: 0.875rem;
        
        &:focus {
            outline: none;
            border-color: var(--janus-primary);
            box-shadow: 0 0 0 1px var(--janus-primary);
        }
        
        &::placeholder {
            color: var(--janus-text-muted);
        }

        &:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            background-color: rgba(255,255,255,0.02);
        }
    }
}

// --- Cards ---
.card {
    background-color: var(--janus-bg-card);
    border: 1px solid var(--janus-border);
    border-radius: var(--janus-radius-lg);
    padding: var(--janus-spacing-lg);
    overflow: hidden;

    // Header/Footer sections within card
    .card-header {
        padding-bottom: var(--janus-spacing-md);
        border-bottom: 1px solid var(--janus-border);
        margin-bottom: var(--janus-spacing-md);
        display: flex;
        justify-content: space-between;
        align-items: center;

        h3 {
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--janus-text-primary);
        }
    }

    .card-footer {
        padding-top: var(--janus-spacing-md);
        border-top: 1px solid var(--janus-border);
        margin-top: var(--janus-spacing-md);
    }
}

// --- Badges ---
.badge {
    display: inline-flex;
    align-items: center;
    gap: var(--janus-spacing-xs);
    padding: 2px 8px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    line-height: 1.2;
    white-space: nowrap;
    
    &.badge-success {
        background-color: rgba(var(--success-rgb), 0.15);
        color: var(--success);
        border: 1px solid rgba(var(--success-rgb), 0.3);
    }
    
    &.badge-warning {
        background-color: rgba(var(--warning-rgb), 0.15);
        color: var(--warning);
        border: 1px solid rgba(var(--warning-rgb), 0.3);
    }
    
    &.badge-error {
        background-color: rgba(var(--error-rgb), 0.15);
        color: var(--error);
        border: 1px solid rgba(var(--error-rgb), 0.3);
    }
    
    &.badge-info {
        background-color: rgba(var(--info-rgb), 0.15);
        color: var(--info);
        border: 1px solid rgba(var(--info-rgb), 0.3);
    }

    &.badge-neutral {
        background-color: var(--janus-bg-surface);
        color: var(--janus-text-secondary);
        border: 1px solid var(--janus-border);
    }
}

// --- Tables ---
.table-container {
    width: 100%;
    overflow-x: auto;
    border: 1px solid var(--janus-border);
    border-radius: var(--janus-radius-lg);
    background-color: var(--janus-bg-card);
    
    table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        
        th {
            background-color: var(--janus-bg-surface);
            color: var(--janus-text-secondary);
            font-weight: 500;
            text-align: left;
            padding: var(--janus-spacing-md);
            border-bottom: 1px solid var(--janus-border);
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;

            &:first-child {
                border-top-left-radius: var(--janus-radius-lg); // Match container radius logic or sm
            }
        }
        
        td {
            padding: var(--janus-spacing-md);
            color: var(--janus-text-primary);
            border-bottom: 1px solid var(--janus-border);
            font-size: 0.875rem;
        }
        
        tr:last-child td {
            border-bottom: none;
        }
        
        tr:hover td {
            background-color: rgba(255, 255, 255, 0.02);
        }
    }
}
</file>

<file path="styles/_markdown.scss">
@use 'tokens' as *;

// =============================================================================
// MARKDOWN CONTENT STYLES
// =============================================================================

.markdown-content {
    color: $color-text-primary;
    line-height: $line-height-relaxed;
    font-size: $font-size-base;

    // Headers
    h1,
    h2,
    h3,
    h4,
    h5,
    h6 {
        margin-top: $spacing-6;
        margin-bottom: $spacing-3;
        font-weight: $font-weight-semibold;
        color: $color-text-primary;

        &:first-child {
            margin-top: 0;
        }
    }

    h1 {
        font-size: 1.75rem;
        border-bottom: 1px solid $color-border-muted;
        padding-bottom: $spacing-2;
    }

    h2 {
        font-size: 1.5rem;
        border-bottom: 1px solid $color-border-muted;
        padding-bottom: $spacing-2;
    }

    h3 {
        font-size: 1.25rem;
    }

    h4 {
        font-size: 1rem;
    }

    // Paragraphs
    p {
        margin-bottom: $spacing-4;

        &:last-child {
            margin-bottom: 0;
        }
    }


    // Lists
    ul,
    ol {
        margin-bottom: $spacing-4;
        padding-left: $spacing-6;

        li {
            margin-bottom: $spacing-2;

            // Handle nested lists
            ul,
            ol {
                margin-top: $spacing-2;
                margin-bottom: 0;
            }
        }
    }

    ul {
        list-style-type: disc;
    }

    ol {
        list-style-type: decimal;
    }

    // Blockquotes
    blockquote {
        border-left: 3px solid $color-accent-purple;
        margin: $spacing-4 0;
        padding: $spacing-2 $spacing-4;
        background: rgba(124, 58, 237, 0.05);
        color: $color-text-secondary;
        border-radius: 0 $radius-sm $radius-sm 0;

        p:last-child {
            margin-bottom: 0;
        }
    }

    // Inline Code
    p code,
    li code,
    td code {
        background: rgba(110, 118, 129, 0.3); // GitHub-ish code pill
        color: $color-text-primary;
        padding: 0.2em 0.4em;
        border-radius: $radius-sm;
        font-family: $font-mono;
        font-size: 85%;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    // Code Blocks
    pre {
        background: transparent !important; // Wrapper handles bg
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
    }

    // Custom Code Wrapper (from MarkdownService)
    .code-block-wrapper {
        margin: $spacing-4 0;
        border: 1px solid $color-border-default;
        border-radius: $radius-md;
        background: #0d1117; // GitHub dark code bg
        overflow: hidden;
        box-shadow: $shadow-sm;

        .code-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: $spacing-2 $spacing-4;
            background: #161b22;
            border-bottom: 1px solid $color-border-default;
            color: $color-text-secondary;
            font-size: $font-size-xs;
            font-family: $font-mono;

            .lang-badge {
                text-transform: uppercase;
                font-weight: 600;
                color: $color-text-secondary;
            }
        }

        pre {
            padding: $spacing-4 !important;
            margin: 0 !important;
            overflow-x: auto;

            code {
                font-family: 'Fira Code', $font-mono;
                font-size: $font-size-sm;
                line-height: 1.5;
                background: transparent;
                padding: 0;
                border: none;
            }
        }
    }

    // Tables
    .table-wrapper {
        margin: $spacing-4 0;
        overflow-x: auto;
        border-radius: $radius-md;
        border: 1px solid $color-border-default;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        font-size: $font-size-sm;

        th,
        td {
            padding: $spacing-3;
            border-bottom: 1px solid $color-border-default;
            text-align: left;
        }

        th {
            background: $color-bg-tertiary;
            font-weight: 600;
            color: $color-text-primary;
            white-space: nowrap;
        }

        td {
            color: $color-text-secondary;
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr:hover td {
            background: rgba(255, 255, 255, 0.02);
        }
    }

    // Links
    a {
        color: $color-accent-cyan;
        text-decoration: none;
        border-bottom: 1px solid transparent;
        transition: border-color 0.2s;

        &:hover {
            border-color: $color-accent-cyan;
        }
    }

    // Images
    img {
        max-width: 100%;
        border-radius: $radius-md;
        border: 1px solid $color-border-default;
        margin: $spacing-4 0;
    }
}
</file>

<file path="styles/_mixins.scss">
/**
 * =============================================================================
 * JANUS MIXINS
 * =============================================================================
 *
 * Reusable mixins for effects, layouts, and utilities.
 *
 * =============================================================================
 */

@use 'styles/tokens' as *;

@mixin glass-panel {
    background: rgba(var(--janus-bg-surface-rgb), 0.76);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid var(--janus-border);
    box-shadow: 0 18px 45px rgba(7, 10, 18, 0.35), 0 0 24px rgba(var(--janus-secondary-rgb), 0.08);
}

@mixin ambient-background {
    background:
        radial-gradient(circle at 15% 35%, rgba(var(--janus-secondary-rgb), 0.08), transparent 40%),
        radial-gradient(circle at 85% 25%, rgba(var(--janus-accent-rgb), 0.06), transparent 45%),
        radial-gradient(circle at 70% 85%, rgba(var(--janus-primary-rgb), 0.05), transparent 40%);
    background-attachment: fixed;
}

// Button Mixins
@mixin btn-base {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--janus-spacing-sm);
    padding: var(--janus-spacing-sm) var(--janus-spacing-md);
    border-radius: var(--janus-radius-md);
    font-weight: 500;
    transition: var(--janus-transition-fast);
    cursor: pointer;
    border: 1px solid transparent;
    font-size: 0.875rem;
    line-height: 1.25rem;

    &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        pointer-events: none;
    }
}

@mixin btn-primary {
    @include btn-base;
    background-color: var(--janus-primary);
    color: var(--janus-bg-dark);
    border-color: transparent;

    &:hover {
        background-color: var(--janus-primary-hover);
        box-shadow: var(--janus-shadow-glow);
    }
}

@mixin btn-secondary {
    @include btn-base;
    background-color: var(--janus-bg-surface);
    border-color: var(--janus-border);
    color: var(--janus-text-primary);

    &:hover {
        background-color: rgba(255, 255, 255, 0.05);
        border-color: var(--janus-text-secondary);
    }
}

@mixin btn-outline {
    @include btn-base;
    background-color: transparent;
    border-color: var(--janus-border);
    color: var(--janus-text-secondary);

    &:hover {
        border-color: var(--janus-text-primary);
        color: var(--janus-text-primary);
        background-color: rgba(255, 255, 255, 0.05);
    }
}

@mixin btn-ghost {
    @include btn-base;
    background-color: transparent;
    color: var(--janus-text-secondary);
    border-color: transparent;
    
    &:hover {
        background-color: rgba(255, 255, 255, 0.05);
        color: var(--janus-text-primary);
    }
}

@mixin btn-danger {
    @include btn-base;
    background-color: transparent;
    border-color: var(--destructive);
    color: var(--destructive);

    &:hover {
         background-color: rgba(var(--error-rgb), 0.12);
    }
}
</file>

<file path="styles/_tokens.scss">
// =============================================================================
// SCSS VARIABLES (Design Tokens)
// =============================================================================

// :root definition for CSS Variables (The Source of Truth)
:root {
  /* Colors - Login Palette */
  --janus-primary: #23d5a1;
  --janus-primary-hover: #3fe3b5;
  --janus-primary-dim: rgba(35, 213, 161, 0.15);
  --janus-primary-rgb: 35, 213, 161;
  --janus-secondary: #45c3ff;
  --janus-secondary-rgb: 69, 195, 255;
  --janus-accent: #f6b348;
  --janus-accent-rgb: 246, 179, 72;
  
  /* Backgrounds */
  --janus-bg-dark: #0a0f13;
  --janus-bg-dark-rgb: 10, 15, 19;
  --janus-bg-card: #131c25;
  --janus-bg-card-rgb: 19, 28, 37;
  --janus-bg-surface: #10161c;
  --janus-bg-surface-rgb: 16, 22, 28;
  
  /* Text */
  --janus-text-primary: #eaf2f8;
  --janus-text-secondary: #b3c1cc;
  --janus-text-muted: #8ea2b0;
  
  /* Borders & Effects */
  --janus-border: rgba(255, 255, 255, 0.08);
  --janus-border-active: rgba(35, 213, 161, 0.65);
  --janus-shadow-glow: 0 12px 30px rgba(35, 213, 161, 0.18);

  /* Status */
  --success: #23d5a1;
  --success-rgb: 35, 213, 161;
  --warning: #f6b348;
  --warning-rgb: 246, 179, 72;
  --error: #ff5b6b;
  --error-rgb: 255, 91, 107;
  --info: #45c3ff;
  --info-rgb: 69, 195, 255;

  /* Legacy aliases */
  --fg: var(--janus-text-primary);
  --muted: var(--janus-text-muted);
  --text-primary: var(--janus-text-primary);
  --text-secondary: var(--janus-text-secondary);
  --text-muted: var(--janus-text-muted);
  --cyan: var(--janus-secondary);
  --accent-cyan: var(--janus-secondary);
  --accent-cyan-rgb: var(--janus-secondary-rgb);
  --accent-purple: #4c6be0;
  --purple: var(--accent-purple);

  /* Typography */
  --janus-font-body: 'Sora', 'Space Grotesk', sans-serif;
  --janus-font-display: 'Space Grotesk', 'Sora', sans-serif;
  --janus-font-mono: 'JetBrains Mono', 'Fira Code', Consolas, 'Courier New', monospace;
  
  /* Spacing */
  --janus-spacing-xs: 4px;
  --janus-spacing-sm: 8px;
  --janus-spacing-md: 16px;
  --janus-spacing-lg: 24px;
  --janus-spacing-xl: 32px;
  
  /* Radius */
  --janus-radius-sm: 4px;
  --janus-radius-md: 8px;
  --janus-radius-lg: 16px;
  
  /* Transitions */
  --janus-transition-fast: 150ms ease;
  --janus-transition-normal: 300ms ease;

  /* Shadcn/UI Compatibility (Mapped) */
  --background: var(--janus-bg-dark);
  --foreground: var(--janus-text-primary);
  --card: var(--janus-bg-card);
  --card-foreground: var(--janus-text-primary);
  --popover: var(--janus-bg-surface);
  --popover-foreground: var(--janus-text-primary);
  --primary: var(--janus-primary);
  --primary-foreground: #061118;
  --secondary: var(--janus-secondary);
  --secondary-foreground: #0a1423;
  --muted: var(--janus-text-muted);
  --muted-foreground: var(--janus-text-secondary);
  --accent: var(--janus-bg-surface);
  --accent-foreground: var(--janus-accent);
  --destructive: var(--error);
  --destructive-foreground: #ffffff;
  --border: var(--janus-border);
  --input: var(--janus-border);
  --ring: var(--janus-primary);
}

/* Light Mode Override (Future Proofing) */
[data-theme="light"] {
  --janus-bg-dark: #f0f0f0;
  --janus-bg-card: #ffffff;
  --janus-bg-surface: #e0e0e0;
  --janus-text-primary: #121212;
  --janus-text-secondary: #505050;
  --janus-border: #cccccc;
}

// SCSS Variables (Mapped to CSS Variables for consistency)

// Colors
$color-bg-primary: var(--janus-bg-dark);
$color-bg-secondary: var(--janus-bg-surface);
$color-bg-tertiary: var(--janus-bg-card);

$color-text-primary: var(--janus-text-primary);
$color-text-secondary: var(--janus-text-secondary);
$color-text-muted: var(--janus-text-muted);
$color-text-link: var(--janus-secondary);
$color-text-tertiary: var(--janus-text-muted);
$color-text-on-emphasis: #ffffff;

$color-border-default: var(--janus-border);
$color-border-muted: var(--janus-border);
$color-border-emphasis: var(--janus-text-secondary);

$color-accent-primary: var(--janus-primary);
$color-accent-primary-hover: var(--janus-primary-hover);

$color-success: #2dd4a7;
$color-warning: #f5c26b;
$color-error: #ff5b6b;
$color-info: #5b8dff;

$color-success-bg: rgba(45, 212, 167, 0.12);
$color-warning-bg: rgba(245, 194, 107, 0.12);
$color-error-bg: rgba(255, 91, 107, 0.12);
$color-info-bg: rgba(91, 141, 255, 0.12);

// Added variables for Markdown and other components
$color-accent-purple: #4c6be0;
$color-accent-cyan: #36d1b7;

// Typography
$font-body: var(--janus-font-body);
$font-display: var(--janus-font-display);
$font-mono: var(--janus-font-mono);

$font-size-sm: 0.875rem;
$font-size-xs: 0.75rem;
$font-size-base: 1rem;
$font-size-lg: 1.125rem;
$font-size-xl: 1.25rem;
$font-size-2xl: 1.5rem;
$font-size-3xl: 1.875rem;
$font-size-4xl: 2.25rem;

$font-weight-medium: 500;
$font-weight-semibold: 600;

$line-height-normal: 1.5;
$line-height-tight: 1.25;
$line-height-relaxed: 1.625;

// Spacing (Mapped to CSS Vars)
$spacing-1: var(--janus-spacing-xs);
$spacing-2: var(--janus-spacing-sm);
$spacing-3: 12px; // No direct mapping, kept as is or could be calc
$spacing-4: var(--janus-spacing-md);
$spacing-6: var(--janus-spacing-lg);
$spacing-8: var(--janus-spacing-xl);

// Borders
$border-width-thin: 1px;
$radius-sm: var(--janus-radius-sm);
$radius-md: var(--janus-radius-md);
$radius-full: 9999px;

// Transitions
$transition-fast: var(--janus-transition-fast);

// Shadows
$shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
$shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
$shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
</file>

<file path="styles/_utilities.scss">
@use 'sass:map';
@use './tokens' as *;

// =============================================================================
// LAYOUT UTILITIES
// =============================================================================

.flex {
    display: flex;
}

.flex-col {
    flex-direction: column;
}

.flex-row {
    flex-direction: row;
}

.flex-wrap {
    flex-wrap: wrap;
}

.items-center {
    align-items: center;
}

.items-start {
    align-items: flex-start;
}

.items-end {
    align-items: flex-end;
}

.justify-center {
    justify-content: center;
}

.justify-between {
    justify-content: space-between;
}

.justify-end {
    justify-content: flex-end;
}

.justify-start {
    justify-content: flex-start;
}

.grid {
    display: grid;
}

.grid-cols-1 {
    grid-template-columns: repeat(1, minmax(0, 1fr));
}

.grid-cols-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr));
}

.grid-cols-3 {
    grid-template-columns: repeat(3, minmax(0, 1fr));
}

.grid-cols-4 {
    grid-template-columns: repeat(4, minmax(0, 1fr));
}

// Gaps
@for $i from 0 through 8 {
    .gap-#{$i} {
        gap: #{$i * 0.25}rem;
    }
}

// =============================================================================
// TYPOGRAPHY UTILITIES
// =============================================================================

.text-xs {
    font-size: 0.75rem;
}

.text-sm {
    font-size: 0.875rem;
}

.text-base {
    font-size: 1rem;
}

.text-lg {
    font-size: 1.125rem;
}

.text-xl {
    font-size: 1.25rem;
}

.text-2xl {
    font-size: 1.5rem;
}

.font-bold {
    font-weight: 700;
}

.font-semibold {
    font-weight: 600;
}

.font-medium {
    font-weight: 500;
}

.font-normal {
    font-weight: 400;
}

.font-mono {
    font-family: var(--janus-font-mono);
}

.uppercase {
    text-transform: uppercase;
}

.tracking-wider {
    letter-spacing: 0.05em;
}

.tracking-widest {
    letter-spacing: 0.1em;
}

.text-center {
    text-align: center;
}

.text-left {
    text-align: left;
}

.text-right {
    text-align: right;
}

// =============================================================================
// VISUAL UTILITIES
// =============================================================================

.opacity-0 {
    opacity: 0;
}

.opacity-25 {
    opacity: 0.25;
}

.opacity-50 {
    opacity: 0.5;
}

.opacity-60 {
    opacity: 0.6;
}

.opacity-70 {
    opacity: 0.7;
}

.opacity-80 {
    opacity: 0.8;
}

.opacity-90 {
    opacity: 0.9;
}

.opacity-100 {
    opacity: 1;
}

.cursor-pointer {
    cursor: pointer;
}

// Sizing
.w-full {
    width: 100%;
}

.h-full {
    height: 100%;
}

.w-fit {
    width: fit-content;
}

.w-2 {
    width: 0.5rem;
}

.h-2 {
    height: 0.5rem;
}

.w-3 {
    width: 0.75rem;
}

.h-3 {
    height: 0.75rem;
}

.w-4 {
    width: 1rem;
}

.h-4 {
    height: 1rem;
}

.w-6 {
    width: 1.5rem;
}

.h-6 {
    height: 1.5rem;
}

.rounded-full {
    border-radius: 9999px;
}

.rounded-sm {
    border-radius: var(--janus-radius-sm);
}

.rounded {
    border-radius: var(--janus-radius-md);
}

.rounded-lg {
    border-radius: var(--janus-radius-lg);
}

// Transitions
.transition-colors {
    transition: background-color var(--janus-transition-fast), color var(--janus-transition-fast), border-color var(--janus-transition-fast);
}

.transition-opacity {
    transition: opacity var(--janus-transition-fast);
}

.transition-transform {
    transition: transform var(--janus-transition-fast);
}

.duration-200 {
    transition-duration: 200ms;
}

// Transforms
.scale-90 {
    transform: scale(0.9);
}
</file>

<file path="env.d.ts">
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_AUTH_TOKEN_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
</file>

<file path="index.html">
<!doctype html>
<html lang="pt-BR">

<head>
  <meta charset="utf-8">
  <title>Janus AI - Architect Agent</title>
  <meta name="description"
    content="Janus: A self-evolving, autonomous AI Architect Agent for system analysis and development.">
  <base href="/">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" type="image/x-icon" href="favicon.ico">
  <link rel="apple-touch-icon" href="assets/icons/icon-192x192.png">
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <meta name="theme-color" content="#0A0F1A" media="(prefers-color-scheme: dark)">
  <meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
  <link rel="manifest" href="/manifest.webmanifest">
  <link
    href="https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap"
    rel="stylesheet" />
  <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet" />
</head>

<body>
  <app-root></app-root>
</body>

</html>
</file>

<file path="main.ts">
import {bootstrapApplication} from '@angular/platform-browser';
import {appConfig} from './app/app.config';
import {App} from './app/app';
import { Chart, registerables } from 'chart.js';
Chart.register(...registerables);

bootstrapApplication(App, appConfig)
  .catch((err) => console.error(err));
</file>

<file path="styles.scss">
/**
 * =============================================================================
 * JANUS - Main Stylesheet
 * =============================================================================
 *
 * Clean, professional design system inspired by GitHub dark mode.
 * Imports modular SCSS files for tokens, animations, and components.
 *
 * =============================================================================
 */

// =============================================================================
// 1. FOUNDATION IMPORTS
// =============================================================================

@use 'styles/tokens' as *;
@use 'styles/utilities' as *;
@use 'styles/animations' as *;
@use 'styles/components' as *;
@use 'styles/markdown' as *;
@import '@angular/cdk/overlay-prebuilt.css';

// =============================================================================
// 0. TAILWIND IMPORTS
// =============================================================================
@tailwind base;
@tailwind components;
@tailwind utilities;

// =============================================================================
// 2. GLOBAL RESETS & BASE STYLES
// =============================================================================

*,
*::before,
*::after {
  box-sizing: border-box;
}

html,
body {
  height: 100%;
  margin: 0;
  padding: 0;
}

body {
  background: $color-bg-primary;
  color: $color-text-primary;
  font-family: $font-body;
  font-size: $font-size-base;
  line-height: $line-height-normal;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow-x: hidden;

  // Subtle ambient background effect
  @include ambient-background;
}

app-root {
  display: block;
  min-height: 100%;
  position: relative;
  z-index: 1;
}

.bg-grid,
.bg-circuit,
.data-plexus {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.bg-grid {
  background-image:
    linear-gradient(rgba(var(--janus-secondary-rgb), 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(var(--janus-secondary-rgb), 0.08) 1px, transparent 1px);
  background-size: 120px 120px;
  opacity: 0.18;
  animation: gridDrift 80s linear infinite;
}

.bg-circuit {
  background-image:
    radial-gradient(circle at 20% 30%, rgba(var(--janus-primary-rgb), 0.12), transparent 45%),
    radial-gradient(circle at 80% 70%, rgba(var(--janus-accent-rgb), 0.1), transparent 50%),
    linear-gradient(90deg, rgba(var(--janus-secondary-rgb), 0.04) 1px, transparent 1px),
    linear-gradient(rgba(var(--janus-secondary-rgb), 0.04) 1px, transparent 1px);
  background-size: 100% 100%, 100% 100%, 180px 180px, 180px 180px;
  opacity: 0.3;
  mix-blend-mode: screen;
  animation: ambientShift 45s ease-in-out infinite;
}

.data-plexus {
  background-image: radial-gradient(circle, rgba(var(--janus-primary-rgb), 0.35) 1px, transparent 1px);
  background-size: 140px 140px;
  opacity: 0.18;
  animation: plexusFloat 24s ease-in-out infinite;
}

// =============================================================================
// 3. TYPOGRAPHY BASE
// =============================================================================

h1,
h2,
h3,
h4,
h5,
h6 {
  margin: 0;
  font-family: $font-display;
  font-weight: $font-weight-semibold;
  line-height: $line-height-tight;
  color: $color-text-primary;
  letter-spacing: 0.01em;
}

h1 {
  font-size: $font-size-4xl;
}

h2 {
  font-size: $font-size-3xl;
}

h3 {
  font-size: $font-size-2xl;
}

h4 {
  font-size: $font-size-xl;
}

h5 {
  font-size: $font-size-lg;
}

h6 {
  font-size: $font-size-base;
}

p {
  margin: 0;
  line-height: $line-height-relaxed;
}

a {
  color: $color-text-link;
  text-decoration: none;
  transition: color $transition-fast;

  &:hover {
    color: $color-accent-primary-hover;
    text-decoration: underline;
  }
}

code,
pre {
  font-family: $font-mono;
  font-size: $font-size-sm;
}

code {
  padding: 2px 6px;
  background: $color-bg-tertiary;
  border-radius: $radius-sm;
  color: $color-accent-primary;
}

pre {
  padding: $spacing-4;
  background: $color-bg-secondary;
  border: $border-width-thin solid $color-border-default;
  border-radius: $radius-md;
  overflow-x: auto;

  code {
    padding: 0;
    background: transparent;
    color: $color-text-primary;
  }
}

// =============================================================================
// 4. SCROLLBAR STYLING
// =============================================================================

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: $color-bg-primary;
}

::-webkit-scrollbar-thumb {
  background: $color-border-default;
  border-radius: $radius-full;
  transition: background $transition-fast;

  &:hover {
    background: $color-border-emphasis;
  }
}

// =============================================================================
// 5. SELECTION STYLING
// =============================================================================

::selection {
  background: rgba(91, 141, 255, 0.35);
  color: $color-text-on-emphasis;
}

::-moz-selection {
  background: rgba(91, 141, 255, 0.35);
  color: $color-text-on-emphasis;
}

// =============================================================================
// 6. FOCUS VISIBLE (Accessibility)
// =============================================================================

:focus-visible {
  outline: 2px solid $color-accent-primary;
  outline-offset: 2px;
}
</file>

<file path="tailwind-styles.scss">
@tailwind base;
@tailwind components;
@tailwind utilities;

/* Custom glassmorphism components */
@layer components {
  .glass {
    @apply bg-white/10 backdrop-blur-md border border-white/20 rounded-2xl shadow-xl;
  }
  
  .glass-dark {
    @apply bg-dark-800/40 backdrop-blur-md border border-white/10 rounded-2xl shadow-2xl;
  }
  
  .glass-card {
    @apply bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-sm border border-white/10 rounded-xl shadow-lg hover:shadow-xl transition-all duration-300;
  }
  
  .btn-primary {
    @apply bg-gradient-to-r from-primary-500 to-primary-600 hover:from-primary-600 hover:to-primary-700 text-white font-semibold px-6 py-3 rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105;
  }
  
  .btn-secondary {
    @apply bg-gradient-to-r from-secondary-500 to-secondary-600 hover:from-secondary-600 hover:to-secondary-700 text-white font-semibold px-6 py-3 rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 transform hover:scale-105;
  }
  
  .metric-card {
    @apply glass-card p-6 hover:scale-105 transition-transform duration-300;
  }
  
  .chart-container {
    @apply glass-card p-4 h-80;
  }
  
  .text-gradient {
    @apply bg-gradient-to-r from-primary-400 to-secondary-400 bg-clip-text text-transparent;
  }
  
  .animate-float {
    animation: float 6s ease-in-out infinite;
  }
  
  .animate-pulse-slow {
    animation: pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  @apply bg-dark-900;
}

::-webkit-scrollbar-thumb {
  @apply bg-primary-600 rounded-full;
}

::-webkit-scrollbar-thumb:hover {
  @apply bg-primary-500;
}
</file>

<file path="test-setup.ts">
import '@angular/compiler'
import '@analogjs/vitest-angular/setup-snapshots'
import { setupTestBed } from '@analogjs/vitest-angular/setup-testbed'
import '@testing-library/jest-dom/vitest'
import { vi } from 'vitest'
import { of } from 'rxjs'

vi.mock('@angular/fire/auth', () => ({
  Auth: class {},
  GoogleAuthProvider: class {},
  signInAnonymously: vi.fn(),
  signInWithPopup: vi.fn(),
  signInWithEmailAndPassword: vi.fn(),
  signOut: vi.fn()
}))

vi.mock('@angular/fire/database', () => ({
  Database: class {},
  ref: vi.fn(),
  objectVal: vi.fn(() => of({}))
}))

setupTestBed()
</file>

</files>
