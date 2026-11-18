import { ChangeDetectorRef, Component, DestroyRef, inject } from '@angular/core'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'
import { ActivatedRoute } from '@angular/router'
import { AuthService } from '../../../core/auth/auth.service'

@Component({
  selector: 'app-login',
  standalone: true,
  templateUrl: './login.html',
  styleUrls: ['./login.scss']
})
export class LoginComponent {
  private readonly auth = inject(AuthService)
  private readonly route = inject(ActivatedRoute)
  private readonly cdr = inject(ChangeDetectorRef)
  private readonly destroyRef = inject(DestroyRef)

  loading = false
  error = ''
  notice = ''

  constructor() {
    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(params => {
      this.notice = String(params.get('message') || '').trim()
      this.cdr.markForCheck()
    })
  }

  async beginLogin(): Promise<void> {
    if (this.loading) return
    this.loading = true
    this.error = ''
    try {
      const returnUrl = String(this.route.snapshot.queryParamMap.get('returnUrl') || '/')
      await this.auth.beginLogin(returnUrl)
    } catch {
      this.error = 'NÃ£o foi possÃ­vel iniciar a autenticaÃ§Ã£o no provedor de identidade.'
      this.loading = false
      this.cdr.markForCheck()
    }
  }
}
