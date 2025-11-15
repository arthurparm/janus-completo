import {Component, inject} from '@angular/core'
import {FormsModule} from '@angular/forms'
import {NgIf} from '@angular/common'
import {JanusApiService, TokenResponse} from '../../../services/janus-api.service'
import {AUTH_TOKEN_KEY} from '../../../services/api.config'

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, NgIf],
  templateUrl: './login.html',
  styleUrls: ['./login.scss']
})
export class LoginComponent {
  private api = inject(JanusApiService)
  userId = 0
  expires = 3600
  message = ''

  submit() {
    this.api.issueToken(this.userId, this.expires).subscribe({
      next: (resp: TokenResponse) => {
        try {
          localStorage.setItem(AUTH_TOKEN_KEY, resp.token)
          this.message = 'Token emitido e salvo. Interceptor anexará automaticamente.'
        } catch {
          this.message = 'Token emitido. Falha ao salvar no localStorage.'
        }
      },
      error: () => {
        this.message = 'Falha ao emitir token. Verifique permissões.'
      }
    })
  }
}