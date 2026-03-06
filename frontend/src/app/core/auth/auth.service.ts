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

  async resetPassword(token: string, password: string): Promise<boolean> {
    try {
      const out = await firstValueFrom(
        this.http.post<{ status: string }>(`${API_BASE_URL}/v1/auth/local/reset`, {
          token,
          password
        })
      )
      return out?.status === 'ok'
    } catch {
      return false
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
        return {
          ok: false,
          statusCode: 401,
          reason: 'invalid_credentials',
          error: 'Email/usuario ou senha invalidos.'
        }
      }
      if (err.status === 422) {
        return {
          ok: false,
          statusCode: 422,
          reason: 'invalid_request',
          error: 'Dados de login invalidos. Revise email e senha.'
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
}
