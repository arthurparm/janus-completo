import { ChangeDetectionStrategy, Component, OnInit, inject } from '@angular/core'
import { ActivatedRoute, Router } from '@angular/router'
import { firstValueFrom } from 'rxjs'

import { BackendApiService } from '../../../services/backend-api.service'

@Component({
  selector: 'app-google-oauth-callback',
  standalone: true,
  template: `
    <main class="oauth-callback" aria-live="polite">
      <h1>Concluindo integração com o Google</h1>
      <p role="status">Validando o retorno e salvando a autorização com segurança…</p>
    </main>
  `,
  styles: [`
    .oauth-callback {
      max-width: 42rem;
      margin: 10vh auto;
      padding: 2rem;
      text-align: center;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class GoogleOAuthCallbackComponent implements OnInit {
  private readonly route = inject(ActivatedRoute)
  private readonly router = inject(Router)
  private readonly api = inject(BackendApiService)

  async ngOnInit(): Promise<void> {
    const code = this.route.snapshot.queryParamMap.get('code') || ''
    const state = this.route.snapshot.queryParamMap.get('state') || ''
    const providerError = this.route.snapshot.queryParamMap.get('error') || ''

    if (providerError || !code || !state) {
      await this.finishWithError('O Google não autorizou a integração solicitada.')
      return
    }

    try {
      await firstValueFrom(this.api.productivity.googleOAuthCallback(code, state))
      await this.router.navigate(['/tools'], {
        queryParams: { google_oauth: 'connected' },
        replaceUrl: true
      })
    } catch {
      await this.finishWithError('Não foi possível concluir a integração com o Google.')
    }
  }

  private async finishWithError(message: string): Promise<void> {
    await this.router.navigate(['/tools'], {
      queryParams: { google_oauth: 'error', message },
      replaceUrl: true
    })
  }
}
