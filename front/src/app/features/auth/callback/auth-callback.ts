import { Component, inject, OnInit } from '@angular/core'
import { NgIf } from '@angular/common'
import { Router } from '@angular/router'
import { SupabaseService } from '../../../core/auth/supabase.service'
import { HttpClient } from '@angular/common/http'
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../../../services/api.config'

@Component({
  selector: 'app-auth-callback',
  standalone: true,
  imports: [NgIf],
  templateUrl: './auth-callback.html',
  styleUrls: ['./auth-callback.scss']
})
export class AuthCallbackComponent implements OnInit {
  private supa = inject(SupabaseService)
  private http = inject(HttpClient)
  private router = inject(Router)
  loading = true
  error = ''

  async ngOnInit() {
    console.log('[AuthCallback] init')
    try {
      const sess = await this.supa.getSession()
      const jwt = sess?.access_token || ''
      console.log('[AuthCallback] session', { hasToken: !!jwt })
      if (!jwt) {
        console.log('[AuthCallback] No session found, waiting for auth state change')
        // Aguarda evento de auth e tenta novamente
        this.supa.onAuthStateChange(async () => {
          console.log('[AuthCallback] authStateChange triggered')
          const s2 = await this.supa.getSession()
          const j2 = s2?.access_token || ''
          console.log('[AuthCallback] authStateChange session check', { hasToken: !!j2 })
          if (j2) {
            await this.exchange(j2)
          } else {
            console.log('[AuthCallback] Still no token after auth state change')
            this.error = 'Falha ao obter sessão do Supabase'
            this.loading = false
          }
        })
        return
      }
      console.log('[AuthCallback] Found session, proceeding with exchange')
      await this.exchange(jwt)
    } catch (error) {
      console.error('[AuthCallback] Error during initialization:', error)
      this.error = 'Falha na autenticação'
      this.loading = false
    }
  }

  private async exchange(jwt: string) {
    console.log('[AuthCallback] exchange:start')
    try {
      const out: any = await this.http.post(`${API_BASE_URL}/v1/auth/supabase/exchange`, { token: jwt }).toPromise()
      const janus = String(out?.token || '')
      if (!janus) throw new Error('Token inválido')
      localStorage.setItem(AUTH_TOKEN_KEY, janus)
      this.loading = false
      console.log('[AuthCallback] exchange:ok')
      // Add a small delay to ensure token is properly stored before navigation
      await new Promise(resolve => setTimeout(resolve, 100))
      await this.router.navigate(['/'])
    } catch (error) {
      console.error('[AuthCallback] exchange:error', error)
      this.error = 'Falha ao finalizar login'
      this.loading = false
    }
  }
}