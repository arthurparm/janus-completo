import { Injectable } from '@angular/core'
import { SupabaseService } from './supabase.service'
import { HttpClient } from '@angular/common/http'
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../../services/api.config'
import { BehaviorSubject, Observable } from 'rxjs'
import { map } from 'rxjs/operators'

export interface User {
  id: string
  email?: string
  roles?: string[]
  permissions?: string[]
  [key: string]: any
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly _isAuthenticated = new BehaviorSubject<boolean>(false)
  private readonly _user = new BehaviorSubject<User | null>(null)
  
  readonly isAuthenticated$ = this._isAuthenticated.asObservable()
  readonly user$ = this._user.asObservable()

  constructor(private supa: SupabaseService, private http: HttpClient) {
    this.initializeAuth()
  }

  private initializeAuth(): void {
    const token = localStorage.getItem(AUTH_TOKEN_KEY)
    if (token) {
      this._isAuthenticated.next(true)
      // You could decode the token to get user info here
      this._user.next({ id: 'current-user', roles: ['user'], permissions: ['read'] })
    }
  }
  async loginWithPassword(email: string, password: string, remember: boolean): Promise<boolean> {
    console.log('[AuthService] loginWithPassword:start', { emailMasked: !!email })
    const res = await this.supa.signInWithPassword(email, password)
    console.log('[AuthService] loginWithPassword:supabaseOk')
    const sess = await this.supa.getSession()
    const jwt = sess?.access_token || ''
    if (!jwt) return false
    try {
      console.log('[AuthService] exchange:start')
      const out: any = await this.http.post(`${API_BASE_URL}/v1/auth/supabase/exchange`, { token: jwt }).toPromise()
      const janus = String(out?.token || '')
      if (!janus) return false
      localStorage.setItem(AUTH_TOKEN_KEY, janus)
      
      // Update authentication state
      this._isAuthenticated.next(true)
      this._user.next({ 
        id: out.user?.id || 'current-user', 
        email: email,
        roles: out.user?.roles || ['user'], 
        permissions: out.user?.permissions || ['read'] 
      })
      
      console.log('[AuthService] exchange:ok')
      return true
    } catch {
      console.log('[AuthService] exchange:error')
      return false
    }
  }
  async loginWithProvider(provider: 'google'|'github'): Promise<boolean> {
    console.log('[AuthService] loginWithProvider:start', { provider })
    await this.supa.signInWithProviderRedirect(provider)
    console.log('[AuthService] loginWithProvider:redirected', { provider })
    return true
  }

  logout(): void {
    console.log('[AuthService] logout')
    localStorage.removeItem(AUTH_TOKEN_KEY)
    this._isAuthenticated.next(false)
    this._user.next(null)
    this.supa.signOut().catch(console.error)
  }
}