import { Injectable } from '@angular/core'
import { SupabaseService } from './supabase.service'
import { HttpClient } from '@angular/common/http'
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../../services/api.config'
import { BehaviorSubject, Observable } from 'rxjs'
import { map } from 'rxjs/operators'
import { Auth, signInAnonymously } from '@angular/fire/auth'
import { inject } from '@angular/core'

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

  get currentUserValue(): User | null {
    return this._user.value
  }

  private auth: Auth = inject(Auth)
  // Expose firebase auth state for components that need to wait for it (like Firestore listeners)
  readonly firebaseAuthReady$ = new BehaviorSubject<boolean>(false)

  constructor(private supa: SupabaseService, private http: HttpClient) {
    this.initializeAuth()
  }

  private initializeAuth(): void {
    // BYPASS: Auto-login as Admin
    console.log('[AuthService] Auto-initializing default admin user (No Auth Mode)')

    // Ensure we have a firebase session for Firestore rules
    signInAnonymously(this.auth)
      .then(userCred => {
        console.log('[AuthService] Firebase Anonymous Auth success:', userCred.user.uid)
        this.firebaseAuthReady$.next(true)
      })
      .catch(err => {
        if (err.code === 'auth/admin-restricted-operation') {
          console.warn('[AuthService] Firebase Anonymous Auth failed with "admin-restricted-operation". This usually means Anonymous Auth is disabled in the Firebase Console. Please enable it in Authentication > Sign-in method.')
        } else {
          console.error('[AuthService] Firebase Anonymous Auth failed:', err)
        }
        // Even if failed, we might want to let components try (or handle error there)
        this.firebaseAuthReady$.next(true)
      })

    this._isAuthenticated.next(true)
    this._user.next({
      id: 'admin',
      email: 'admin@janus.ai',
      roles: ['admin', 'sysadmin'],
      permissions: ['*']
    })
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
  async loginWithProvider(provider: 'google' | 'github'): Promise<boolean> {
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