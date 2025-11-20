import { Component, inject } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormConfig, FormSubmitEvent } from '../form/form.component'
import { ModalConfig, ModalAction } from '../modal/modal.component'
import { UiService } from '../../services/ui.service'
import { LoadingComponent } from '../loading/loading.component'
import { ErrorComponent } from '../error/error.component'
import { FormComponent } from '../form/form.component'
import { ModalComponent } from '../modal/modal.component'
import { MatButtonModule } from '@angular/material/button'

@Component({
  selector: 'app-ui-components-demo',
  standalone: true,
  imports: [
    CommonModule,
    LoadingComponent,
    ErrorComponent,
    FormComponent,
    ModalComponent,
    MatButtonModule
  ],
  template: `
    <div class="demo-container">
      <h1>UI Components Demo</h1>
      <p class="subtitle">Demonstração dos componentes de UI reutilizáveis</p>

      <!-- Loading Component Demo -->
      <section class="demo-section">
        <h2>Loading Component</h2>
        <div class="demo-controls">
          <button mat-button (click)="showLoadingDemo()" [disabled]="isLoadingDemo">
            Mostrar Loading
          </button>
          <button mat-button (click)="hideLoadingDemo()" [disabled]="!isLoadingDemo">
            Esconder Loading
          </button>
        </div>
        <app-loading 
          [isLoading]="isLoadingDemo" 
          [message]="'Processando dados...'"
          [subMessage]="'Isso pode levar alguns segundos'"
          [diameter]="50"
          [overlay]="true">
          <div class="content-behind-loading">
            <p>Este conteúdo fica visível quando não está carregando</p>
          </div>
        </app-loading>
      </section>

      <!-- Error Component Demo -->
      <section class="demo-section">
        <h2>Error Component</h2>
        <div class="demo-controls">
          <button mat-button (click)="showErrorDemo()">Mostrar Erro</button>
          <button mat-button (click)="showWarningDemo()">Mostrar Aviso</button>
          <button mat-button (click)="showInfoDemo()">Mostrar Info</button>
        </div>
        <app-error
          *ngIf="currentErrorMessage"
          [message]="currentErrorMessage"
          [type]="currentErrorType"
          [actions]="errorActions"
          (actionExecuted)="handleErrorAction($event)">
        </app-error>
      </section>

      <!-- Form Component Demo -->
      <section class="demo-section">
        <h2>Form Component</h2>
        <div class="demo-controls">
          <button mat-button (click)="resetForm()">Resetar Formulário</button>
          <button mat-button (click)="fillForm()">Preencher Formulário</button>
        </div>
        <app-form
          [config]="demoFormConfig"
          [initialValues]="formInitialValues"
          [isSubmitting]="isSubmittingForm"
          [submitError]="formSubmitError"
          (submitted)="onFormSubmit($event)"
          (valueChanged)="onFormValueChange($event)">
        </app-form>
        <div class="form-result" *ngIf="lastFormResult">
          <h3>Último resultado do formulário:</h3>
          <pre>{{ lastFormResult | json }}</pre>
        </div>
      </section>

      <!-- Modal Component Demo -->
      <section class="demo-section">
        <h2>Modal Component</h2>
        <div class="demo-controls">
          <button mat-button (click)="showSmallModal()">Modal Pequeno</button>
          <button mat-button (click)="showMediumModal()">Modal Médio</button>
          <button mat-button (click)="showLargeModal()">Modal Grande</button>
          <button mat-button (click)="showFullModal()">Modal Full</button>
        </div>
        <app-modal
          [isOpen]="isModalOpen"
          [config]="modalConfig"
          [actions]="modalActions"
          (closed)="onModalClose()"
          (actionExecuted)="onModalAction($event)">
          <div class="modal-content">
            <h3>Conteúdo do Modal</h3>
            <p>Este é o conteúdo do modal. Você pode colocar qualquer coisa aqui.</p>
            <p *ngIf="modalConfig.scrollable">
              Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. 
              Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat. 
              Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. 
              Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.
              Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, 
              totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo.
            </p>
          </div>
        </app-modal>
      </section>

      <!-- Toast Demo -->
      <section class="demo-section">
        <h2>Toast Notifications</h2>
        <div class="demo-controls">
          <button mat-button (click)="showSuccessToast()">Toast Sucesso</button>
          <button mat-button (click)="showErrorToast()">Toast Erro</button>
          <button mat-button (click)="showWarningToast()">Toast Aviso</button>
          <button mat-button (click)="showInfoToast()">Toast Info</button>
        </div>
      </section>

      <!-- Confirm Dialog Demo -->
      <section class="demo-section">
        <h2>Confirm Dialog</h2>
        <button mat-button (click)="showConfirmDialog()">Mostrar Confirmação</button>
        <div class="confirm-result" *ngIf="lastConfirmResult !== null">
          <p>Resultado: {{ lastConfirmResult ? 'Confirmado' : 'Cancelado' }}</p>
        </div>
      </section>
    </div>
  `,
  styles: [`
    .demo-container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 40px 20px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    h1 {
      font-size: 2.5rem;
      font-weight: 700;
      color: #2d3748;
      margin: 0 0 8px 0;
      text-align: center;
    }

    .subtitle {
      font-size: 1.125rem;
      color: #718096;
      text-align: center;
      margin: 0 0 40px 0;
    }

    .demo-section {
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
      padding: 32px;
      margin-bottom: 32px;
    }

    .demo-section h2 {
      font-size: 1.5rem;
      font-weight: 600;
      color: #2d3748;
      margin: 0 0 24px 0;
      border-bottom: 2px solid #e2e8f0;
      padding-bottom: 12px;
    }

    .demo-controls {
      display: flex;
      gap: 12px;
      margin-bottom: 24px;
      flex-wrap: wrap;
    }

    .demo-controls button {
      padding: 8px 16px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      background: white;
      color: #4a5568;
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.2s;
    }

    .demo-controls button:hover:not(:disabled) {
      background: #f7fafc;
      border-color: #cbd5e0;
    }

    .demo-controls button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    .content-behind-loading {
      padding: 20px;
      background: #f7fafc;
      border-radius: 8px;
      text-align: center;
    }

    .form-result {
      margin-top: 24px;
      padding: 16px;
      background: #f0fff4;
      border: 1px solid #9ae6b4;
      border-radius: 8px;
    }

    .form-result h3 {
      margin: 0 0 12px 0;
      font-size: 1rem;
      color: #22543d;
    }

    .form-result pre {
      margin: 0;
      font-size: 14px;
      color: #2f855a;
      background: white;
      padding: 12px;
      border-radius: 4px;
      overflow-x: auto;
    }

    .modal-content {
      padding: 20px;
    }

    .modal-content h3 {
      margin: 0 0 16px 0;
      color: #2d3748;
    }

    .modal-content p {
      margin: 0 0 12px 0;
      color: #4a5568;
      line-height: 1.6;
    }

    .confirm-result {
      margin-top: 16px;
      padding: 12px;
      background: #ebf8ff;
      border: 1px solid #90cdf4;
      border-radius: 6px;
      color: #2b6cb0;
      font-weight: 500;
    }

    @media (max-width: 768px) {
      .demo-container {
        padding: 20px 16px;
      }

      h1 {
        font-size: 2rem;
      }

      .demo-section {
        padding: 24px;
      }

      .demo-controls {
        flex-direction: column;
      }

      .demo-controls button {
        width: 100%;
      }
    }
  `]
})
export class UiComponentsDemoComponent {
  private uiService = inject(UiService)

  // Loading demo
  isLoadingDemo = false

  // Error demo
  currentErrorMessage = ''
  currentErrorType: 'error' | 'warning' | 'info' = 'error'

  // Form demo
  isSubmittingForm = false
  formSubmitError = ''
  lastFormResult: any = null
  formInitialValues = {
    name: 'João Silva',
    email: 'joao@example.com',
    phone: '(11) 98765-4321',
    message: 'Esta é uma mensagem de exemplo'
  }

  demoFormConfig: FormConfig = {
    fields: [
      {
        name: 'name',
        type: 'text',
        label: 'Nome Completo',
        placeholder: 'Seu nome completo',
        required: true,
        validation: {
          minLength: 3,
          maxLength: 100
        }
      },
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
        name: 'phone',
        type: 'tel',
        label: 'Telefone',
        placeholder: '(00) 00000-0000',
        required: false,
        validation: {
          pattern: '^\\([0-9]{2}\\) [0-9]{5}-[0-9]{4}$',
          patternMessage: 'Formato: (XX) XXXXX-XXXX'
        }
      },
      {
        name: 'message',
        type: 'text',
        label: 'Mensagem',
        placeholder: 'Sua mensagem aqui...',
        required: true,
        validation: {
          minLength: 10,
          maxLength: 500
        }
      }
    ],
    submitButtonText: 'Enviar Mensagem',
    cancelButtonText: 'Cancelar',
    showCancel: true,
    validateOnSubmit: true,
    validateOnChange: false,
    resetOnSubmit: false
  }

  // Modal demo
  isModalOpen = false
  modalConfig: ModalConfig = {
    title: 'Demo Modal',
    size: 'medium',
    closable: true,
    backdrop: true,
    centered: true,
    scrollable: false
  }

  modalActions: ModalAction[] = [
    {
      label: 'Cancelar',
      action: () => this.closeModal(),
      type: 'secondary'
    },
    {
      label: 'Confirmar',
      action: () => this.confirmModal(),
      type: 'primary'
    }
  ]

  // Confirm dialog
  lastConfirmResult: boolean | null = null

  errorActions = [
    {
      label: 'Tentar Novamente',
      action: () => this.retryAction(),
      type: 'primary' as const
    },
    {
      label: 'Ver Ajuda',
      action: () => this.showHelp(),
      type: 'secondary' as const
    }
  ]

  // Loading demo methods
  showLoadingDemo() {
    this.isLoadingDemo = true
    setTimeout(() => {
      this.isLoadingDemo = false
    }, 3000)
  }

  hideLoadingDemo() {
    this.isLoadingDemo = false
  }

  // Error demo methods
  showErrorDemo() {
    this.currentErrorMessage = 'Ocorreu um erro ao processar sua solicitação. Por favor, tente novamente.'
    this.currentErrorType = 'error'
  }

  showWarningDemo() {
    this.currentErrorMessage = 'Atenção: Esta ação não pode ser desfeita. Tem certeza que deseja continuar?'
    this.currentErrorType = 'warning'
  }

  showInfoDemo() {
    this.currentErrorMessage = 'Informação: Seu cadastro foi atualizado com sucesso!'
    this.currentErrorType = 'info'
  }

  handleErrorAction(action: any) {
    action.action()
  }

  retryAction() {
    this.uiService.showInfo('Tentando novamente...')
    this.currentErrorMessage = ''
  }

  showHelp() {
    this.uiService.showInfo('Redirecionando para página de ajuda...')
    this.currentErrorMessage = ''
  }

  // Form demo methods
  onFormSubmit(event: FormSubmitEvent) {
    if (!event.valid) {
      this.uiService.showWarning('Por favor, corrija os erros no formulário')
      return
    }

    this.isSubmittingForm = true
    this.formSubmitError = ''

    // Simulate API call
    setTimeout(() => {
      this.lastFormResult = {
        success: true,
        data: event.value,
        timestamp: new Date().toISOString()
      }
      this.isSubmittingForm = false
      this.uiService.showSuccess('Formulário enviado com sucesso!')
    }, 2000)
  }

  onFormValueChange(values: any) {
    console.log('Form values changed:', values)
  }

  resetForm() {
    this.lastFormResult = null
    this.formSubmitError = ''
  }

  fillForm() {
    this.formInitialValues = {
      name: 'Maria Santos',
      email: 'maria@example.com',
      phone: '(21) 99876-5432',
      message: 'Esta é uma mensagem preenchida automaticamente para demonstração'
    }
  }

  // Modal demo methods
  showSmallModal() {
    this.modalConfig = { ...this.modalConfig, size: 'small', title: 'Modal Pequeno' }
    this.isModalOpen = true
  }

  showMediumModal() {
    this.modalConfig = { ...this.modalConfig, size: 'medium', title: 'Modal Médio' }
    this.isModalOpen = true
  }

  showLargeModal() {
    this.modalConfig = { ...this.modalConfig, size: 'large', title: 'Modal Grande' }
    this.isModalOpen = true
  }

  showFullModal() {
    this.modalConfig = { 
      ...this.modalConfig, 
      size: 'full', 
      title: 'Modal Full Screen',
      scrollable: true 
    }
    this.isModalOpen = true
  }

  closeModal() {
    this.isModalOpen = false
  }

  confirmModal() {
    this.uiService.showSuccess('Modal confirmado!')
    this.isModalOpen = false
  }

  onModalClose() {
    this.isModalOpen = false
  }

  onModalAction(action: ModalAction) {
    console.log('Modal action executed:', action)
  }

  // Toast demo methods
  showSuccessToast() {
    this.uiService.showSuccess('Operação realizada com sucesso!')
  }

  showErrorToast() {
    this.uiService.showError('Erro ao processar a solicitação.')
  }

  showWarningToast() {
    this.uiService.showWarning('Atenção: Verifique os dados antes de continuar.')
  }

  showInfoToast() {
    this.uiService.showInfo('Informação importante: Atualização disponível.')
  }

  // Confirm dialog demo
  showConfirmDialog() {
    this.uiService.showConfirm({
      title: 'Confirmar Ação',
      message: 'Tem certeza que deseja excluir este item? Esta ação não pode ser desfeita.',
      confirmText: 'Excluir',
      cancelText: 'Cancelar',
      confirmColor: 'warn'
    }).subscribe(result => {
      this.lastConfirmResult = result
      if (result) {
        this.uiService.showSuccess('Item excluído com sucesso!')
      } else {
        this.uiService.showInfo('Ação cancelada.')
      }
    })
  }
}