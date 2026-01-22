/* eslint-disable no-console */
import { Injectable, inject, signal, computed } from '@angular/core'
import { HttpClient } from '@angular/common/http'
import { API_BASE_URL, AUTH_TOKEN_KEY, VISITOR_MODE_KEY } from '../../services/api.config'
import { firstValueFrom } from 'rxjs'
import { toObservable } from '@angular/core/rxjs-interop'

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

  constructor() {
    this.initializeAuth()
  }

  private async initializeAuth(): Promise<void> {
    this._authReady.set(false)
    this._firebaseAuthReady.set(true)

    const token = localStorage.getItem(AUTH_TOKEN_KEY)
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

  async loginWithPassword(email: string, password: string, _remember: boolean): Promise<boolean> {
    try {
      const out = await firstValueFrom(
        this.http.post<LocalAuthResponse>(`${API_BASE_URL}/v1/auth/local/login`, {
          email,
          password
        })
      )
      const token = String(out?.token || '')
      if (token) {
        localStorage.setItem(AUTH_TOKEN_KEY, token)
        localStorage.removeItem(VISITOR_MODE_KEY)
        this._isAuthenticated.set(true)
        this._user.set(out.user)
        return true
      }
      return false
    } catch {
      return false
    }
  }

  async loginWithProvider(provider: 'google' | 'github'): Promise<boolean> {
    console.warn('Login via provider not supported in local auth mode', provider)
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
  }): Promise<boolean> {
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
        localStorage.setItem(AUTH_TOKEN_KEY, token)
        localStorage.removeItem(VISITOR_MODE_KEY)
        this._isAuthenticated.set(true)
        this._user.set(out.user)
        return true
      }
      return false
    } catch {
      return false
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
    localStorage.removeItem(AUTH_TOKEN_KEY)
    localStorage.removeItem(VISITOR_MODE_KEY)
    this._isAuthenticated.set(false)
    this._user.set(null)
  }

  async logout(): Promise<void> {
    this.clearSession()
  }
}
