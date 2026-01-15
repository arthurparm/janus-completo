import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core'
import { CommonModule } from '@angular/common'
import { UiButtonComponent } from '../ui/button/button.component'
import { UiIconComponent } from '../ui/icon/icon.component'
import { UiSpinnerComponent } from '../ui/spinner/spinner.component'

export interface ModalAction {
  label: string
  action: () => void | Promise<void>
  type?: 'primary' | 'secondary' | 'danger'
  disabled?: boolean
  loading?: boolean
}

export interface ModalConfig {
  title: string
  size?: 'small' | 'medium' | 'large' | 'full'
  closable?: boolean
  backdrop?: boolean
  centered?: boolean
  scrollable?: boolean
}

@Component({
  selector: 'app-modal',
  standalone: true,
  imports: [
    CommonModule,
    UiButtonComponent,
    UiIconComponent,
    UiSpinnerComponent
  ],
  template: `
    <div class="modal-overlay" *ngIf="isOpen" (click)="onBackdropClick($event)">
      <div class="modal-container" [class]="getModalClasses()" (click)="$event.stopPropagation()">
        <!-- Header -->
        <div class="modal-header" *ngIf="config.title">
          <h2 class="modal-title">{{ config.title }}</h2>
          <button 
            *ngIf="config.closable !== false" 
            ui-button variant="ghost" size="icon"
            (click)="close()"
            aria-label="Close modal">
            <ui-icon>close</ui-icon>
          </button>
        </div>

        <!-- Content -->
        <div class="modal-body" [class.scrollable]="config.scrollable">
          <ng-content></ng-content>
        </div>

        <!-- Footer with actions -->
        <div class="modal-footer" *ngIf="actions && actions.length > 0">
          <div class="modal-actions">
            <button
              *ngFor="let action of actions; let i = index"
              ui-button 
              [variant]="getButtonVariant(action)"
              [disabled]="action.disabled || action.loading"
              (click)="handleAction(action)"
              [attr.data-testid]="'modal-action-' + i">
              <span *ngIf="!action.loading">{{ action.label }}</span>
              <ui-spinner *ngIf="action.loading" [size]="20" color="white"></ui-spinner>
            </button>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background-color: rgba(0, 0, 0, 0.7);
      backdrop-filter: blur(4px);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      animation: fadeIn 0.2s ease-out;
    }

    .modal-container {
      background: var(--janus-bg-card);
      border: 1px solid var(--janus-border);
      border-radius: var(--janus-radius-lg);
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
      max-height: 90vh;
      max-width: 90vw;
      display: flex;
      flex-direction: column;
      animation: slideIn 0.3s ease-out;
      color: var(--janus-text-primary);
    }

    .modal-container.small { width: 400px; }
    .modal-container.medium { width: 600px; }
    .modal-container.large { width: 800px; }
    .modal-container.full { width: 95vw; height: 95vh; }
    .modal-container.centered { margin: auto; }

    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: var(--janus-spacing-md) var(--janus-spacing-lg);
      border-bottom: 1px solid var(--janus-border);
    }

    .modal-title {
      margin: 0;
      font-size: 1.25rem;
      font-weight: 600;
      color: var(--janus-text-primary);
    }

    /* Removed obsolete button styles as UiButton handles them */

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    @keyframes slideIn {
      from { transform: translateY(-20px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }

    @media (max-width: 768px) {
      .modal-container {
        width: 95vw !important;
        margin: 16px;
      }
    }
  `]
})
export class ModalComponent implements OnInit, OnDestroy {
  @Input() isOpen = false
  @Input() config: ModalConfig = {
    title: '',
    size: 'medium',
    closable: true,
    backdrop: true,
    centered: true,
    scrollable: false
  }
  @Input() actions: ModalAction[] = []

  @Output() closed = new EventEmitter<void>()
  @Output() actionExecuted = new EventEmitter<ModalAction>()


  ngOnInit() {
    if (this.isOpen) {
      this.preventBodyScroll()
    }
  }

  ngOnDestroy() {
    this.restoreBodyScroll()
  }

  private preventBodyScroll() {
    document.body.style.overflow = 'hidden'
  }

  private restoreBodyScroll() {
    document.body.style.overflow = ''
  }

  close(): void {
    this.isOpen = false
    this.closed.emit()
    this.restoreBodyScroll()
  }

  onBackdropClick(event: MouseEvent): void {
    if (this.config.backdrop !== false) {
      this.close()
    }
  }

  getModalClasses(): string {
    const classes = ['modal-container']
    if (this.config.size) {
      classes.push(this.config.size)
    }
    if (this.config.centered) {
      classes.push('centered')
    }
    return classes.join(' ')
  }

  getButtonVariant(action: ModalAction): 'default' | 'secondary' | 'destructive' | 'outline' {
    switch (action.type) {
      case 'primary': return 'default';
      case 'secondary': return 'outline'; // or secondary
      case 'danger': return 'destructive';
      default: return 'outline';
    }
  }

  async handleAction(action: ModalAction): Promise<void> {
    if (action.disabled || action.loading) {
      return
    }

    action.loading = true
    try {
      await action.action()
      this.actionExecuted.emit(action)
    } catch (error) {
      console.error('Error executing modal action:', error)
    } finally {
      action.loading = false
    }
  }
}
