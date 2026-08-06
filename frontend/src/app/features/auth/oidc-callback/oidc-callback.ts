import { Component, OnInit, inject } from '@angular/core'
import { ActivatedRoute, Router } from '@angular/router'
import { AuthService } from '../../../core/auth/auth.service'

@Component({
  selector: 'app-oidc-callback',
  standalone: true,
  template: '<p role="status">Concluindo autenticação segura…</p>'
})
export class OidcCallbackComponent implements OnInit {
  private readonly route = inject(ActivatedRoute)
  private readonly router = inject(Router)
  private readonly auth = inject(AuthService)

  async ngOnInit(): Promise<void> {
    const code = this.route.snapshot.queryParamMap.get('code') || ''
    const state = this.route.snapshot.queryParamMap.get('state') || ''
    try {
      const target = await this.auth.handleCallback(code, state)
      await this.router.navigateByUrl(target, { replaceUrl: true })
    } catch {
      await this.router.navigate(['/login'], {
        queryParams: { message: 'Não foi possível validar o retorno do provedor de identidade.' },
        replaceUrl: true
      })
    }
  }
}
