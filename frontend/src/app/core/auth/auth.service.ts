import { Injectable, inject, signal, computed } from '@angular/core'
import { HttpClient, HttpErrorResponse } from '@angular/common/http'
import { API_BASE_URL, AUTH_REFRESH_TOKEN_KEY, AUTH_TOKEN_KEY, VISITOR_MODE_KEY } from '../../services/api.config'
import { firstValueFrom } from 'rxjs'
import { toObservable } from '@angular/core/rxjs-interop'
import { AppLoggerService } from '../services/app-logger.service'
import {
  clearStoredAuthToken,
  clearStoredRefreshToken,
  getStoredAuthToken,
  getStoredRefreshToken,
  storeAuthToken,
  storeRefreshToken
} from '../../services/auth.utils'

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
  refresh_token: string
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
  private readonly _isVisitor = signal<boolean>(false)
  private readonly _user = signal<User | null>(null)
  private readonly _firebaseAuthReady = signal<boolean>(false)
  private readonly _authReady = signal<boolean>(false)
  private readonly _authRateLimitUntilMs = signal<number>(0)
  private refreshPromise: Promise<boolean> | null = null

  readonly isAuthenticated = this._isAuthenticated.asReadonly()
  readonly isVisitor = this._isVisitor.asReadonly()
  readonly user = this._user.asReadonly()
  readonly firebaseAuthReady = this._firebaseAuthReady.asReadonly()
  readonly authReady = this._authReady.asReadonly()
  readonly authRateLimitUntilMs = this._authRateLimitUntilMs.asReadonly()

  readonly isAuthenticated$ = toObservable(this._isAuthenticated)
  readonly isVisitor$ = toObservable(this._isVisitor)
  readonly user$ = toObservable(this._user)
  readonly firebaseAuthReady$ = toObservable(this._firebaseAuthReady)
  readonly authReady$ = toObservable(this._authReady)

  readonly isAdmin = computed(() => this._user()?.roles?.includes('admin') ?? false)
  readonly userEmail = computed(() => this._user()?.email ?? '')

  authRateLimitRemainingSeconds(): number {
    const until = this._authRateLimitUntilMs()
    if (!until) return 0
    const delta = until - Date.now()
    if (delta <= 0) return 0
    return Math.ceil(delta / 1000)
  }

  isAuthRateLimited(): boolean {
    return this.authRateLimitRemainingSeconds() > 0
  }

  get currentUserValue(): User | null {
    return this._user()
  }

  isVisitorSession(): boolean {
    return this._isVisitor()
  }

  private http = inject(HttpClient)
  private logger = inject(AppLoggerService)

  constructor() {
    this.initializeAuth()
  }

  private async initializeAuth(): Promise<void> {
    this._authReady.set(false)
    this._firebaseAuthReady.set(true)

    if (localStorage.getItem(VISITOR_MODE_KEY) === '1') {
      this.activateVisitorSession()
      this._authReady.set(true)
      return
    }

    const token = getStoredAuthToken()
    if (token) {
      try {
        const user = await firstValueFrom(
          this.http.get<User>(`${API_BASE_URL}/v1/auth/local/me`)
        )
        this._isAuthenticated.set(true)
        this._user.set(user)
      } catch (err) {
        if (err instanceof HttpErrorResponse && err.status === 401) {
          const refreshed = await this.refreshAccessToken()
          if (refreshed) {
            try {
              const user = await firstValueFrom(
                this.http.get<User>(`${API_BASE_URL}/v1/auth/local/me`)
              )
              this._isAuthenticated.set(true)
              this._user.set(user)
              this._authReady.set(true)
              return
            } catch {
              this.clearSession()
            }
          } else {
            this.clearSession()
          }
        } else {
          this.clearSession()
        }
      }
    } else {
      this._isAuthenticated.set(false)
      this._user.set(null)
    }

    this._authReady.set(true)
  }

  enterVisitorMode(): AuthActionResult {
    clearStoredAuthToken()
    clearStoredRefreshToken()
    localStorage.setItem(VISITOR_MODE_KEY, '1')
    this.activateVisitorSession()
    return { ok: true }
  }

  async loginWithPassword(email: string, password: string, remember: boolean): Promise<LoginResult> {
    if (this.isAuthRateLimited()) {
      return {
        ok: false,
        statusCode: 429,
        reason: 'rate_limited',
        error: this.formatRateLimitMessage(this.authRateLimitRemainingSeconds())
      }
    }
    try {
      const out = await firstValueFrom(
        this.http.post<LocalAuthResponse>(`${API_BASE_URL}/v1/auth/local/login`, {
          email,
          password
        })
      )
      const token = String(out?.token || '')
      const refreshToken = String(out?.refresh_token || '')
      if (token && refreshToken) {
        storeAuthToken(token, remember)
        storeRefreshToken(refreshToken, remember)
        localStorage.removeItem(VISITOR_MODE_KEY)
        this._isVisitor.set(false)
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
      const refreshToken = String(out?.refresh_token || '')
      if (token && refreshToken) {
        storeAuthToken(token, true)
        storeRefreshToken(refreshToken, true)
        localStorage.removeItem(VISITOR_MODE_KEY)
        this._isVisitor.set(false)
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
    clearStoredRefreshToken()
    localStorage.removeItem(VISITOR_MODE_KEY)
    this._isVisitor.set(false)
    this._isAuthenticated.set(false)
    this._user.set(null)
  }

  private activateVisitorSession(): void {
    this._isVisitor.set(true)
    this._isAuthenticated.set(true)
    this._user.set({
      id: 'visitor',
      username: 'visitante',
      display_name: 'Visitante',
      roles: ['visitor'],
      permissions: ['read:public']
    })
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
        this.captureRateLimit(err, 'auth.local_login')
        this.logger.warn('[AuthService] Rate limited (login)', {
          status: err.status,
          retryAfterSeconds: this.authRateLimitRemainingSeconds(),
        })
        return {
          ok: false,
          statusCode: 429,
          reason: 'rate_limited',
          error: this.formatRateLimitMessage(this.authRateLimitRemainingSeconds())
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

  async refreshAccessToken(): Promise<boolean> {
    if (this.refreshPromise) return this.refreshPromise
    this.refreshPromise = this.refreshAccessTokenInternal()
    try {
      return await this.refreshPromise
    } finally {
      this.refreshPromise = null
    }
  }

  private async refreshAccessTokenInternal(): Promise<boolean> {
    const refreshToken = getStoredRefreshToken()
    if (!refreshToken) return false

    const remember = this.isRefreshTokenRemembered()
    try {
      const out = await firstValueFrom(
        this.http.post<LocalAuthResponse>(`${API_BASE_URL}/v1/auth/local/refresh`, {
          refresh_token: refreshToken
        })
      )
      const token = String(out?.token || '')
      const newRefreshToken = String(out?.refresh_token || '')
      if (!token || !newRefreshToken) return false
      storeAuthToken(token, remember)
      storeRefreshToken(newRefreshToken, remember)
      localStorage.removeItem(VISITOR_MODE_KEY)
      this._isVisitor.set(false)
      this._isAuthenticated.set(true)
      this._user.set(out.user)
      return true
    } catch (err) {
      if (err instanceof HttpErrorResponse) {
        if (err.status === 401 || err.status === 403) {
          this.clearSession()
          return false
        }
        if (err.status === 429) {
          this.captureRateLimit(err, 'auth.local_refresh')
          return false
        }
      }
      return false
    }
  }

  private isRefreshTokenRemembered(): boolean {
    try {
      return Boolean(localStorage.getItem(AUTH_REFRESH_TOKEN_KEY) || localStorage.getItem(AUTH_TOKEN_KEY))
    } catch {
      return false
    }
  }

  captureRateLimit(err: HttpErrorResponse, source: string): void {
    const retryAfterSeconds = this.readRetryAfterSeconds(err)
    const seconds = retryAfterSeconds ?? 60
    const until = Date.now() + Math.max(1, seconds) * 1000
    const current = this._authRateLimitUntilMs()
    if (until > current) {
      this._authRateLimitUntilMs.set(until)
      this.logger.warn('[AuthService] Rate limit captured', { source, retryAfterSeconds: seconds })
    }
  }

  private readRetryAfterSeconds(err: HttpErrorResponse): number | null {
    const value = err.headers?.get('Retry-After') ?? null
    if (!value) return null
    const asNum = Number.parseInt(value, 10)
    if (Number.isFinite(asNum) && asNum > 0) return asNum
    const asDate = Date.parse(value)
    if (!Number.isNaN(asDate)) {
      const deltaMs = asDate - Date.now()
      const seconds = Math.ceil(deltaMs / 1000)
      return seconds > 0 ? seconds : null
    }
    return null
  }

  private formatRateLimitMessage(seconds: number): string {
    const s = Math.max(1, Number(seconds) || 1)
    return `Muitas tentativas. Aguarde ${s} segundo(s) e tente novamente.`
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
