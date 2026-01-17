import { Component, inject } from '@angular/core'
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms'
import { NgIf } from '@angular/common'
import { RouterLink } from '@angular/router'
import { Firestore, addDoc, collection, serverTimestamp } from '@angular/fire/firestore'
import { AuthService } from '../../../core/auth/auth.service'
import { VISITOR_MODE_KEY } from '../../../services/api.config'
import { firstValueFrom } from 'rxjs'
import { filter, take, timeout } from 'rxjs/operators'

@Component({
  selector: 'app-request-access',
  standalone: true,
  imports: [ReactiveFormsModule, NgIf, RouterLink],
  templateUrl: './request-access.html',
  styleUrls: ['./request-access.scss']
})
export class RequestAccessComponent {
  private fb = inject(FormBuilder)
  private firestore = inject(Firestore)
  private authService = inject(AuthService)

  loading = false
  error = ''
  success = ''

  form = this.fb.group({
    name: ['', [Validators.required, Validators.minLength(2)]],
    email: ['', [Validators.required, Validators.email]]
  })

  async submit() {
    if (this.loading) return
    this.error = ''
    this.success = ''
    if (this.form.invalid) {
      this.form.markAllAsTouched()
      return
    }
    this.loading = true
    const value = this.form.value
    try {
      await this.waitForFirebaseReady()
      const payload = {
        name: String(value.name || '').trim(),
        email: String(value.email || '').trim().toLowerCase(),
        access_type: 'full',
        status: 'pending',
        created_at: serverTimestamp(),
        source: 'request_access'
      }
      await addDoc(collection(this.firestore, 'access_requests'), payload)
      this.success = 'Pedido enviado. Entraremos em contato.'
      this.form.reset()
    } catch (err) {
      console.error('[RequestAccess] Failed to submit:', err)
      this.error = 'Nao foi possivel enviar agora. Tente novamente.'
    } finally {
      this.loading = false
    }
  }

  enterVisitor(): void {
    try {
      localStorage.setItem(VISITOR_MODE_KEY, '1')
      window.location.assign('/')
    } catch (err) {
      console.error('[RequestAccess] Failed to set visitor mode:', err)
      this.error = 'Nao foi possivel entrar como visitante.'
    }
  }

  private async waitForFirebaseReady(): Promise<void> {
    try {
      await firstValueFrom(
        this.authService.firebaseAuthReady$.pipe(
          filter((ready) => ready),
          take(1),
          timeout(5000)
        )
      )
    } catch {
      // If it times out, we still attempt to write (rules may allow anonymous writes).
    }
  }
}
