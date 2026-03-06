import { ChangeDetectorRef, Component, inject } from '@angular/core'
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms'
import { Router } from '@angular/router'
import { RouterLink } from '@angular/router'
import { AuthService } from '../../../core/auth/auth.service'
import { AppLoggerService } from '../../../core/services/app-logger.service'

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
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
    const email = String(this.form.value.email || '').trim()
    if (!email) {
      this.error = 'Informe seu email para recuperar o acesso.'
      return
    }
    this.loading = true
    try {
      const token = await this.auth.requestPasswordReset(email)
      if (token) {
        this.notice = `Token de reset: ${token}`
      } else {
        this.notice = 'Se o email existir, enviaremos instrucoes de recuperacao.'
      }
      this.showRecoveryHint = false
    } catch {
      this.error = 'Falha ao solicitar recuperacao.'
    } finally {
      this.loading = false
      this.cdr.markForCheck()
    }
  }
}
