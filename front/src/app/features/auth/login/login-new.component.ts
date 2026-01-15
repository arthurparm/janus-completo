import { Component, inject } from '@angular/core'
import { CommonModule } from '@angular/common'
import { Router } from '@angular/router'
import { FormConfig, FormSubmitEvent } from '../../../shared/components/form/form.component'
import { UiService } from '../../../shared/services/ui.service'
import { AuthService } from '../../../core/auth/auth.service'
import { LoadingComponent } from '../../../shared/components/loading/loading.component'
import { ErrorComponent } from '../../../shared/components/error/error.component'
import { FormComponent } from '../../../shared/components/form/form.component'
import { UiButtonComponent } from '../../../shared/components/ui/button/button.component'
import { UiIconComponent } from '../../../shared/components/ui/icon/icon.component'

@Component({
  selector: 'app-login-new',
  standalone: true,
  imports: [
    CommonModule,
    LoadingComponent,
    ErrorComponent,
    FormComponent,
    UiButtonComponent,
    UiIconComponent
  ],
  template: `
    <section class="login">
      <div class="panel">
        <div class="brand">
          <div class="logo"></div>
          <h1>Bem-vindo(a) à sua plataforma de IA</h1>
          <p class="subtitle">Arquitetura autônoma, performance superior e experiência impecável.</p>
        </div>

        <!-- Loading state -->
        <app-loading 
          *ngIf="loadingState.loading" 
          [isLoading]="true"
          [message]="'Processando login...'"
          [overlay]="true">
        </app-loading>

        <!-- Error state -->
        <app-error
          *ngIf="loadingState.error"
          [message]="loadingState.error"
          [type]="'error'"
          [actions]="errorActions"
          (actionExecuted)="handleErrorAction($event)">
        </app-error>

        <!-- Login form -->
        <app-form
          *ngIf="!loadingState.loading && !loadingState.error"
          [config]="loginFormConfig"
          [initialValues]="initialValues"
          [isSubmitting]="isSubmitting"
          [submitError]="submitError"
          (submitted)="onFormSubmit($event)"
          (cancelled)="onFormCancel()">
        </app-form>

        <!-- Alternative login methods -->
        <div class="alt-methods" *ngIf="!loadingState.loading && !loadingState.error">
          <div class="divider">
            <span>ou</span>
          </div>
          
          <div class="sso-buttons">
            <button 
              ui-button 
              variant="outline"
              class="w-full justify-center gap-2 h-10 border-gray-200 text-gray-700 hover:bg-gray-50 bg-white"
              (click)="loginWithGoogle()"
              [disabled]="isSubmitting">
              <ui-icon class="text-red-500 scale-75">login</ui-icon>
              Continuar com Google
            </button>
            
            <button 
              ui-button 
              variant="outline"
              class="w-full justify-center gap-2 h-10 border-gray-300 text-gray-800 hover:bg-gray-50 bg-white"
              (click)="loginWithGithub()"
              [disabled]="isSubmitting">
              <ui-icon class="scale-75">code</ui-icon>
              Continuar com GitHub
            </button>
          </div>
        </div>

        <!-- Account creation link -->
        <div class="account-links" *ngIf="!loadingState.loading && !loadingState.error">
          <span>Não tem conta?</span>
          <a class="link" (click)="navigateToRegister()">Criar conta</a>
        </div>

        <!-- Forgot password link -->
        <div class="forgot-password" *ngIf="!loadingState.loading && !loadingState.error">
          <a class="link" (click)="navigateToForgotPassword()">Esqueci minha senha</a>
        </div>
      </div>
    </section>
  `,
  styles: [`
    .login {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      padding: 20px;
    }

    .panel {
      background: white;
      border-radius: 12px;
      box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
      padding: 40px;
      width: 100%;
      max-width: 400px;
      text-align: center;
    }

    .brand {
      margin-bottom: 32px;
    }

    .logo {
      width: 60px;
      height: 60px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 12px;
      margin: 0 auto 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      position: relative;
    }

    .logo::before {
      content: 'J';
      color: white;
      font-size: 24px;
      font-weight: bold;
    }

    h1 {
      font-size: 24px;
      font-weight: 600;
      color: #2d3748;
      margin: 0 0 8px 0;
    }

    .subtitle {
      font-size: 14px;
      color: #718096;
      margin: 0;
    }

    .alt-methods {
      margin: 32px 0;
    }

    .divider {
      text-align: center;
      margin: 24px 0;
      position: relative;
    }

    .divider::before {
      content: '';
      position: absolute;
      top: 50%;
      left: 0;
      right: 0;
      height: 1px;
      background: #e2e8f0;
    }

    .divider span {
      background: white;
      padding: 0 16px;
      position: relative;
      color: #718096;
      font-size: 14px;
    }

    .sso-buttons {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .sso-button {
      width: 100%;
      padding: 12px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      background: white;
      color: #4a5568;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
    }

    .sso-button:hover:not(:disabled) {
      background: #f7fafc;
      border-color: #cbd5e0;
    }

    .sso-button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .sso-button.google {
      border-color: #db4437;
      color: #db4437;
    }

    .sso-button.github {
      border-color: #333;
      color: #333;
    }

    .account-links,
    .forgot-password {
      margin-top: 24px;
      font-size: 14px;
      color: #718096;
    }

    .link {
      color: #667eea;
      text-decoration: none;
      font-weight: 500;
      cursor: pointer;
      transition: color 0.2s;
    }

    .link:hover {
      color: #5a67d8;
      text-decoration: underline;
    }

    @media (max-width: 480px) {
      .panel {
        padding: 24px;
        margin: 16px;
      }

      h1 {
        font-size: 20px;
      }

      .subtitle {
        font-size: 13px;
      }
    }
  `]
})
export class LoginNewComponent {
  private router = inject(Router)
  private auth = inject(AuthService)
  private uiService = inject(UiService)

  loadingState = this.uiService.createLoadingState()
  isSubmitting = false
  submitError = ''

  initialValues = {
    email: '',
    password: '',
    remember: true
  }

  loginFormConfig: FormConfig = {
    fields: [
      {
        name: 'email',
        type: 'email',
        label: 'Email',
        placeholder: 'seu@email.com',
        required: true,
        validation: {
          pattern: '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$',
          patternMessage: 'Por favor, insira um email válido'
        }
      },
      {
        name: 'password',
        type: 'password',
        label: 'Senha',
        placeholder: 'Sua senha',
        required: true,
        validation: {
          minLength: 6,
          patternMessage: 'A senha deve ter no mínimo 6 caracteres'
        }
      },
      {
        name: 'remember',
        type: 'text',
        label: 'Lembrar-me',
        defaultValue: true
      }
    ],
    submitButtonText: 'Entrar',
    showCancel: false,
    validateOnSubmit: true,
    resetOnSubmit: false
  }

  errorActions = [
    {
      label: 'Tentar novamente',
      action: () => this.resetForm(),
      type: 'primary' as const
    },
    {
      label: 'Recuperar senha',
      action: () => this.navigateToForgotPassword(),
      type: 'secondary' as const
    }
  ]

  async onFormSubmit(event: FormSubmitEvent) {
    if (!event.valid) {
      this.uiService.showWarning('Por favor, corrija os erros no formulário')
      return
    }

    this.isSubmitting = true
    this.submitError = ''

    try {
      const { email, password, remember } = event.value
      const ok = await this.auth.loginWithPassword(email, password, remember)

      if (ok) {
        this.uiService.showSuccess('Login realizado com sucesso!')
        await new Promise(resolve => setTimeout(resolve, 100))
        await this.router.navigate(['/'])
      } else {
        this.handleLoginFailure()
      }
    } catch (error) {
      console.error('Login error:', error)
      this.handleLoginFailure()
    } finally {
      this.isSubmitting = false
    }
  }

  onFormCancel() {
    // Navigate back or to home
    this.router.navigate(['/'])
  }

  async loginWithGoogle() {
    if (this.isSubmitting) return

    this.isSubmitting = true
    try {
      const ok = await this.auth.loginWithProvider('google')
      if (ok) {
        this.uiService.showSuccess('Login com Google realizado com sucesso!')
        await this.router.navigate(['/'])
      } else {
        this.handleLoginFailure()
      }
    } catch (error) {
      console.error('Google login error:', error)
      this.handleLoginFailure()
    } finally {
      this.isSubmitting = false
    }
  }

  async loginWithGithub() {
    if (this.isSubmitting) return

    this.isSubmitting = true
    try {
      const ok = await this.auth.loginWithProvider('github')
      if (ok) {
        this.uiService.showSuccess('Login com GitHub realizado com sucesso!')
        await this.router.navigate(['/'])
      } else {
        this.handleLoginFailure()
      }
    } catch (error) {
      console.error('GitHub login error:', error)
      this.handleLoginFailure()
    } finally {
      this.isSubmitting = false
    }
  }

  handleLoginFailure() {
    this.loadingState.setError('Credenciais inválidas. Por favor, verifique seu email e senha.')
    this.uiService.showError('Falha no login. Verifique suas credenciais.')
  }

  handleErrorAction(action: any) {
    action.action()
  }

  resetForm() {
    this.loadingState.setError(null)
    this.submitError = ''
  }

  navigateToRegister() {
    this.router.navigate(['/register'])
  }

  navigateToForgotPassword() {
    this.router.navigate(['/forgot-password'])
  }
}