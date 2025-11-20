import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core'
import { CommonModule } from '@angular/common'
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog'
import { MatButtonModule } from '@angular/material/button'
import { MatIconModule } from '@angular/material/icon'
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner'

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
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule
  ],
  template: `
    <div class="modal-overlay" *ngIf="isOpen" (click)="onBackdropClick($event)">
      <div class="modal-container" [class]="getModalClasses()" (click)="$event.stopPropagation()">
        <!-- Header -->
        <div class="modal-header" *ngIf="config.title">
          <h2 class="modal-title">{{ config.title }}</h2>
          <button 
            *ngIf="config.closable !== false" 
            class="modal-close" 
            (click)="close()"
            aria-label="Close modal">
            <mat-icon>close</mat-icon>
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
              mat-button
              [class]="getActionButtonClasses(action)"
              [disabled]="action.disabled || action.loading"
              (click)="handleAction(action)"
              [attr.data-testid]="'modal-action-' + i">
              <span *ngIf="!action.loading">{{ action.label }}</span>
              <mat-spinner *ngIf="action.loading" diameter="20"></mat-spinner>
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
      background-color: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
      animation: fadeIn 0.2s ease-out;
    }

    .modal-container {
      background: white;
      border-radius: 8px;
      box-shadow: 0 11px 15px -7px rgba(0, 0, 0, 0.2), 
                  0 24px 38px 3px rgba(0, 0, 0, 0.14), 
                  0 9px 46px 8px rgba(0, 0, 0, 0.12);
      max-height: 90vh;
      max-width: 90vw;
      display: flex;
      flex-direction: column;
      animation: slideIn 0.3s ease-out;
    }

    .modal-container.small {
      width: 400px;
    }

    .modal-container.medium {
      width: 600px;
    }

    .modal-container.large {
      width: 800px;
    }

    .modal-container.full {
      width: 95vw;
      height: 95vh;
    }

    .modal-container.centered {
      margin: auto;
    }

    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 20px 24px;
      border-bottom: 1px solid #e0e0e0;
    }

    .modal-title {
      margin: 0;
      font-size: 1.25rem;
      font-weight: 500;
      color: rgba(0, 0, 0, 0.87);
    }

    .modal-close {
      background: none;
      border: none;
      padding: 8px;
      cursor: pointer;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: background-color 0.2s;
    }

    .modal-close:hover {
      background-color: rgba(0, 0, 0, 0.04);
    }

    .modal-body {
      flex: 1;
      padding: 24px;
      overflow-y: auto;
    }

    .modal-body.scrollable {
      max-height: 60vh;
    }

    .modal-footer {
      padding: 16px 24px;
      border-top: 1px solid #e0e0e0;
      display: flex;
      justify-content: flex-end;
    }

    .modal-actions {
      display: flex;
      gap: 8px;
    }

    .modal-actions button {
      min-width: 88px;
    }

    .action-primary {
      background-color: #1976d2;
      color: white;
    }

    .action-secondary {
      background-color: transparent;
      color: #1976d2;
      border: 1px solid #1976d2;
    }

    .action-danger {
      background-color: #f44336;
      color: white;
    }

    .action-primary:hover:not(:disabled) {
      background-color: #1565c0;
    }

    .action-secondary:hover:not(:disabled) {
      background-color: rgba(25, 118, 210, 0.04);
    }

    .action-danger:hover:not(:disabled) {
      background-color: #d32f2f;
    }

    button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
      }
      to {
        opacity: 1;
      }
    }

    @keyframes slideIn {
      from {
        transform: translateY(-20px);
        opacity: 0;
      }
      to {
        transform: translateY(0);
        opacity: 1;
      }
    }

    @media (max-width: 768px) {
      .modal-container {
        width: 95vw !important;
        margin: 16px;
      }

      .modal-header,
      .modal-body,
      .modal-footer {
        padding-left: 16px;
        padding-right: 16px;
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

  private dialogRef?: MatDialogRef<any>

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

  getActionButtonClasses(action: ModalAction): string {
    const type = action.type || 'secondary'
    return `action-${type}`
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