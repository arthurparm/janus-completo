import { Component, inject } from '@angular/core'
import { ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms'
import { NgIf } from '@angular/common'
import { Router } from '@angular/router'
import { RouterLink } from '@angular/router'
import { AuthService } from '../../../core/auth/auth.service'

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [ReactiveFormsModule, NgIf, RouterLink],
  templateUrl: './login.html',
  styleUrls: ['./login.scss']
})
export class LoginComponent {
  private fb = inject(FormBuilder)
  private auth = inject(AuthService)
  private router = inject(Router)
  form = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(6)]],
    remember: [true]
  })
  showPassword = false
  loading = false
  error = ''
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
    if (this.form.invalid) { this.form.markAllAsTouched(); return }
    this.loading = true
    const v = this.form.value
    try {
      console.log('[LoginComponent] Attempting login with email:', v.email)
      const ok = await this.auth.loginWithPassword(String(v.email), String(v.password), !!v.remember)
      if (ok) {
        console.log('[LoginComponent] Login successful, navigating to home')
        // Add a small delay to ensure token is properly stored
        await new Promise(resolve => setTimeout(resolve, 100))
        await this.router.navigate(['/'])
      } else {
        console.log('[LoginComponent] Login failed - invalid credentials')
        this.handleFailure()
      }
    } catch (error) {
      console.error('[LoginComponent] Login error:', error)
      this.handleFailure()
    } finally {
      this.loading = false
    }
  }

  async loginWithGoogle() {
    if (this.loading) return
    this.loading = true
    this.error = ''
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
    }
  }

  async loginWithGithub() {
    if (this.loading) return
    this.loading = true
    this.error = ''
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
    }
  }

  handleFailure() {
    this.attempts += 1
    if (this.attempts >= 5) {
      this.lockedUntil = Date.now() + 60_000
    }
    this.error = 'Falha no login. Verifique seus dados.'
  }
}
