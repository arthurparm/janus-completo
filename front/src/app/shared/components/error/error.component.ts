import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy } from '@angular/core'
import { CommonModule } from '@angular/common'
import { UiIconComponent } from '../ui/icon/icon.component'
import { UiButtonComponent } from '../ui/button/button.component'
import { ComponentSize, ComponentColor } from '../../../core/types'

export interface ErrorAction {
  label: string
  action: () => void
  type?: 'primary' | 'secondary' | 'danger'
  icon?: string
}

/**
 * Componente de erro reutilizável para todo o sistema
 * Uso: <app-error [message]="Erro ao carregar dados" [actions]="errorActions" />
 */
@Component({
  selector: 'app-error',
  standalone: true,
  imports: [CommonModule, UiIconComponent, UiButtonComponent],
  template: `
    <div class="error-container" [class.small]="size === 'small'">
      <div class="error-icon">
        <ui-icon [style.color]="iconColor" [size]="size === 'small' ? 24 : 48">{{ icon }}</ui-icon>
      </div>
      
      <div class="error-content">
        <h3 *ngIf="title" class="error-title">{{ title }}</h3>
        <p class="error-message">{{ message }}</p>
        <p *ngIf="subMessage" class="error-submessage">{{ subMessage }}</p>
        
        <div *ngIf="actions && actions.length > 0" class="error-actions">
          <button *ngFor="let action of actions" 
                  ui-button
                  [variant]="action.type === 'secondary' ? 'secondary' : (action.type === 'danger' ? 'destructive' : 'default')"
                  (click)="handleAction(action)">
            {{ action.label }}
          </button>
        </div>
      </div>
      
      <button *ngIf="dismissible" 
              ui-button
              variant="ghost"
              size="icon"
              class="close-button"
              (click)="dismiss.emit()">
        <ui-icon>close</ui-icon>
      </button>
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    .error-container {
      display: flex;
      align-items: center;
      justify-content: center;
      flex-direction: column;
      padding: 2rem;
      text-align: center;
      background-color: #ffebee;
      border-radius: 8px;
      border: 1px solid #ffcdd2;
      position: relative;
      min-height: 200px;
    }

    .error-container.small {
      padding: 1rem;
      min-height: auto;
      flex-direction: row;
      text-align: left;
      gap: 1rem;
    }

    .error-icon {
      margin-bottom: 1rem;
    }

    .error-container.small .error-icon {
      margin-bottom: 0;
    }

    .error-icon mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
    }

    .error-container.small .error-icon mat-icon {
      font-size: 24px;
      width: 24px;
      height: 24px;
    }

    .error-content {
      max-width: 400px;
    }

    .error-title {
      margin: 0 0 0.5rem 0;
      font-size: 1.25rem;
      font-weight: 500;
      color: #c62828;
    }

    .error-message {
      margin: 0 0 0.5rem 0;
      font-size: 1rem;
      color: #d32f2f;
      line-height: 1.5;
    }

    .error-submessage {
      margin: 0;
      font-size: 0.875rem;
      color: #f44336;
      opacity: 0.8;
    }

    .error-actions {
      margin-top: 1rem;
      display: flex;
      gap: 0.5rem;
      justify-content: center;
      flex-wrap: wrap;
    }

    .error-container.small .error-actions {
      justify-content: flex-start;
    }

    .close-button {
      position: absolute;
      top: 0.5rem;
      right: 0.5rem;
      color: #f44336;
    }

    /* Variações de tipo */
    :host(.warning) .error-container {
      background-color: #fff3e0;
      border-color: #ffe0b2;
    }

    :host(.warning) .error-title {
      color: #e65100;
    }

    :host(.warning) .error-message {
      color: #f57c00;
    }

    :host(.info) .error-container {
      background-color: #e3f2fd;
      border-color: #bbdefb;
    }

    :host(.info) .error-title {
      color: #0d47a1;
    }

    :host(.info) .error-message {
      color: #1976d2;
    }
  `]
})
export class ErrorComponent {
  @Input() message = 'Ocorreu um erro'
  @Input() title = ''
  @Input() subMessage = ''
  @Input() icon = 'error_outline'
  @Input() iconColor = '#f44336'
  @Input() type: 'error' | 'warning' | 'info' = 'error'
  @Input() size: ComponentSize = 'medium'
  @Input() actions: ErrorAction[] = []
  @Input() dismissible = false
  @Output() dismiss = new EventEmitter<void>()

  ngOnInit() {
    // Configurações automáticas baseadas no tipo
    if (this.type === 'warning') {
      this.icon = 'warning'
      this.iconColor = '#ff9800'
    } else if (this.type === 'info') {
      this.icon = 'info'
      this.iconColor = '#2196f3'
    }
  }

  getButtonColor(type?: 'primary' | 'secondary' | 'danger'): ComponentColor {
    switch (type) {
      case 'primary': return 'primary'
      case 'secondary': return 'accent'
      case 'danger': return 'warn'
      default: return 'primary'
    }
  }

  handleAction(action: ErrorAction): void {
    if (action.action) {
      action.action()
    }
  }
}
