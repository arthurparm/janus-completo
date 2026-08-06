import { HttpClient, HttpContext } from '@angular/common/http'
import { Injectable, computed, inject, signal } from '@angular/core'
import { toObservable } from '@angular/core/rxjs-interop'
import { firstValueFrom } from 'rxjs'
import { API_BASE_URL, PUBLIC_API_BASE_URL } from '../../services/api.config'
import { clearStoredAuthToken, getStoredAuthToken, storeAuthToken } from '../../services/auth.utils'
import { SKIP_AUTH_SESSION } from '../interceptors/auth-session.interceptor'

const PKCE_VERIFIER = 'JANUS_OIDC_PKCE_VERIFIER'
const OIDC_STATE = 'JANUS_OIDC_STATE'
const OIDC_REDIRECT = 'JANUS_OIDC_REDIRECT'

export interface User {
  id: string
  email?: string
  username?: string
  display_name?: string
  roles?: string[]
  permissions?: string[]
  [key: string]: unknown
}

interface OidcConfig {
  issuer: string
  client_id: string
  audience: string
  scopes: string[]
  authorization_endpoint: string
  response_type: 'code'
  code_challenge_method: 'S256'
}

interface OidcDiscovery { token_endpoint: string }
interface TokenResponse { access_token: string; token_type: string; expires_in?: number }

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient)
  private readonly _isAuthenticated = signal(false)
  private readonly _user = signal<User | null>(null)
  private readonly _authReady = signal(false)

  readonly isAuthenticated = this._isAuthenticated.asReadonly()
  readonly user = this._user.asReadonly()
  readonly authReady = this._authReady.asReadonly()
  readonly isAuthenticated$ = toObservable(this._isAuthenticated)
  readonly user$ = toObservable(this._user)
  readonly authReady$ = toObservable(this._authReady)
  readonly isAdmin = computed(() => this._user()?.roles?.some(role => role.toUpperCase() === 'ADMIN') ?? false)
  readonly userEmail = computed(() => this._user()?.email ?? '')

  constructor() { void this.initializeAuth() }

  get currentUserValue(): User | null { return this._user() }

  private async initializeAuth(): Promise<void> {
    if (getStoredAuthToken()) {
      try {
        await this.loadCurrentUser()
      } catch {
        this.clearSession()
      }
    }
    this._authReady.set(true)
  }

  private async loadCurrentUser(): Promise<void> {
    const user = await firstValueFrom(this.http.get<User>(`${API_BASE_URL}/v1/users/me`))
    this._user.set(user)
    this._isAuthenticated.set(true)
  }

  async beginLogin(returnUrl = '/'): Promise<void> {
    const config = await firstValueFrom(
      this.http.get<OidcConfig>(`${PUBLIC_API_BASE_URL}/api/v1/auth/oidc-config`, {
        context: new HttpContext().set(SKIP_AUTH_SESSION, true)
      })
    )
    const verifier = randomUrlSafe(64)
    const state = randomUrlSafe(32)
    const challenge = await sha256UrlSafe(verifier)
    sessionStorage.setItem(PKCE_VERIFIER, verifier)
    sessionStorage.setItem(OIDC_STATE, state)
    sessionStorage.setItem(OIDC_REDIRECT, returnUrl.startsWith('/') ? returnUrl : '/')
    const callback = `${window.location.origin}/auth/callback`
    const params = new URLSearchParams({
      client_id: config.client_id,
      response_type: 'code',
      redirect_uri: callback,
      scope: config.scopes.join(' '),
      audience: config.audience,
      state,
      code_challenge: challenge,
      code_challenge_method: 'S256'
    })
    window.location.assign(`${config.authorization_endpoint}?${params.toString()}`)
  }

  async handleCallback(code: string, state: string): Promise<string> {
    const verifier = sessionStorage.getItem(PKCE_VERIFIER)
    const expectedState = sessionStorage.getItem(OIDC_STATE)
    if (!code || !state || !verifier || state !== expectedState) {
      this.clearSession()
      throw new Error('Invalid OIDC callback state')
    }
    const config = await firstValueFrom(
      this.http.get<OidcConfig>(`${PUBLIC_API_BASE_URL}/api/v1/auth/oidc-config`, {
        context: new HttpContext().set(SKIP_AUTH_SESSION, true)
      })
    )
    const discovery = await firstValueFrom(
      this.http.get<OidcDiscovery>(`${config.issuer.replace(/\/$/, '')}/.well-known/openid-configuration`, {
        context: new HttpContext().set(SKIP_AUTH_SESSION, true)
      })
    )
    if (!discovery.token_endpoint.startsWith('https://')) throw new Error('OIDC token endpoint must use HTTPS')
    const body = new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: config.client_id,
      code,
      redirect_uri: `${window.location.origin}/auth/callback`,
      code_verifier: verifier
    }).toString()
    const result = await firstValueFrom(
      this.http.post<TokenResponse>(discovery.token_endpoint, body, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        context: new HttpContext().set(SKIP_AUTH_SESSION, true)
      })
    )
    if (!result.access_token || result.token_type.toLowerCase() !== 'bearer') throw new Error('Invalid token response')
    storeAuthToken(result.access_token)
    sessionStorage.removeItem(PKCE_VERIFIER)
    sessionStorage.removeItem(OIDC_STATE)
    await this.loadCurrentUser()
    const target = sessionStorage.getItem(OIDC_REDIRECT) || '/'
    sessionStorage.removeItem(OIDC_REDIRECT)
    return target
  }

  async logout(): Promise<void> { this.clearSession() }

  private clearSession(): void {
    clearStoredAuthToken()
    sessionStorage.removeItem(PKCE_VERIFIER)
    sessionStorage.removeItem(OIDC_STATE)
    sessionStorage.removeItem(OIDC_REDIRECT)
    this._isAuthenticated.set(false)
    this._user.set(null)
  }
}

function randomUrlSafe(bytes: number): string {
  const value = new Uint8Array(bytes)
  crypto.getRandomValues(value)
  return btoa(String.fromCharCode(...value)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

async function sha256UrlSafe(value: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))
  return btoa(String.fromCharCode(...new Uint8Array(digest))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}
