/* eslint-disable no-console */
import { Injectable, inject } from '@angular/core'
import { HttpClient } from '@angular/common/http'
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../../services/api.config'
import { BehaviorSubject, firstValueFrom } from 'rxjs'
import { Auth, signInAnonymously, signInWithPopup, GoogleAuthProvider, signInWithEmailAndPassword, signOut, User as FirebaseUser } from '@angular/fire/auth'

export interface User {
  id: string
  email?: string
  roles?: string[]
  permissions?: string[]
  [key: string]: unknown
}

export interface AuthExchangeResponse {
  token: string
  user: {
    id: string
    roles: string[]
    permissions: string[]
  }
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
  private http = inject(HttpClient)

  // Expose firebase auth state for components that need to wait for it (like Firestore listeners)
  readonly firebaseAuthReady$ = new BehaviorSubject<boolean>(false)

  constructor() {
    this.initializeAuth()
  }

  private initializeAuth(): void {
    // Listen to Firebase Auth State
    this.auth.onAuthStateChanged(async (firebaseUser) => {
      console.log('[AuthService] onAuthStateChanged:', firebaseUser?.uid)

      if (firebaseUser) {
        // User is signed in (anonymous or real)
        this.firebaseAuthReady$.next(true)

        if (!firebaseUser.isAnonymous) {
          // It's a real user, try to exchange token for Janus session
          await this.handleRealUserLogin(firebaseUser)
        } else {
          // If anonymous, we might still want to be "authenticated" as guest or admin-bypass if needed
          // For now, keeping the "Auto-login as Admin" bypass if no real user is present?
          // The original code forced admin. Let's keep the bypass behavior strictly if requested, 
          // but ideally we want real login. 
          // Logic: If NO token in localStorage, maybe default to admin for dev?
          // User said "Firebase as SSOT". So let's rely on Firebase.
          // If anonymous, we are NOT authenticated in the app sense (unless guest).
        }
      } else {
        // Signed out
        this._isAuthenticated.next(false)
        this._user.next(null)

        // Ensure anonymous session for Firestore if needed? 
        // Original code did signInAnonymously. We can keep that for "public" access if desired.
        signInAnonymously(this.auth).catch(err => console.error('Anon auth failed', err));
      }
    })

    // Check if we have a Janus token already? 
    const token = localStorage.getItem(AUTH_TOKEN_KEY)
    if (token) {
      // Validate token or just assume true for now?
      // Ideally we validate. For now, let's just set true to avoid flicker if valid.
      // But if Firebase triggers "null" user, we might log out.
      // Let's rely on Firebase auth state mainly.
    }
  }

  async loginWithPassword(email: string, password: string, _remember: boolean): Promise<boolean> {
    // eslint-disable-next-line no-console
    console.log('[AuthService] loginWithPassword:start', { emailMasked: !!email })
    try {
      await signInWithEmailAndPassword(this.auth, email, password)
      // onAuthStateChanged will handle the rest
      return true
    } catch (err) {
      console.error('[AuthService] loginWithPassword error', err)
      return false
    }
  }

  async loginWithProvider(provider: 'google' | 'github'): Promise<boolean> {
    console.log('[AuthService] loginWithProvider:start', { provider })
    try {
      if (provider === 'google') {
        await signInWithPopup(this.auth, new GoogleAuthProvider())
        return true
      }
      // Github not yet implemented in this refactor, falling back or error
      console.warn('Github auth not implemented in Firebase refactor yet')
      return false
    } catch (err) {
      console.error('[AuthService] loginWithProvider error', err)
      return false
    }
  }

  // Helper to exchange Firebase ID Token for Janus Token
  private async handleRealUserLogin(firebaseUser: FirebaseUser) {
    try {
      const token = await firebaseUser.getIdToken()
      // Reuse existing endpoint for now. Ideally should be /v1/auth/firebase/exchange
      const out = await firstValueFrom(this.http.post<AuthExchangeResponse>(`${API_BASE_URL}/v1/auth/supabase/exchange`, { token }))

      const janus = String(out?.token || '')
      if (janus) {
        localStorage.setItem(AUTH_TOKEN_KEY, janus)

        this._isAuthenticated.next(true)
        this._user.next({
          id: out.user?.id || firebaseUser.uid,
          email: firebaseUser.email || '',
          roles: out.user?.roles || ['user'],
          permissions: out.user?.permissions || ['read']
        })
        console.log('[AuthService] Janus Exchange Success')
      }
    } catch (err) {
      console.error('[AuthService] Janus Exchange Failed', err)
      this.logout()
    }
  }

  async logout(): Promise<void> {
    console.log('[AuthService] logout')
    localStorage.removeItem(AUTH_TOKEN_KEY)
    this._isAuthenticated.next(false)
    this._user.next(null)
    await signOut(this.auth)
  }
}