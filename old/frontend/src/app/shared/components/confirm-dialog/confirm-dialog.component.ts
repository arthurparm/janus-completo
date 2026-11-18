import { Component, inject } from '@angular/core'
import { CommonModule } from '@angular/common'
import { UiButtonComponent } from '../../../shared/components/ui/button/button.component'
import { UiDialogRef } from '../ui/dialog/dialog-ref'
import { UI_DIALOG_DATA } from '../ui/dialog/dialog.tokens'

export interface ConfirmDialogData {
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  confirmColor?: 'primary' | 'warn' | 'accent'
}

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule, UiButtonComponent],
  template: `
    <div class="confirm-dialog-content">
      <div class="dialog-header">
        <div class="dialog-icon">
          <span class="icon-symbol">!</span>
        </div>
        <h2 class="dialog-title">{{ data.title }}</h2>
      </div>
      <p class="dialog-message">{{ data.message }}</p>
      <div class="dialog-actions">
        <button ui-button variant="outline" size="sm" (click)="onCancel()">
          {{ data.cancelText || 'Cancelar' }}
        </button>
        <button
          ui-button
          [variant]="confirmVariant"
          size="sm"
          (click)="onConfirm()">
          {{ data.confirmText || 'Confirmar' }}
        </button>
      </div>
    </div>
  `,
  styles: [`
    .confirm-dialog-content {
      /* Removed padding/bg/shadow as container handles it, OR keep it if I want nested card look? */
      /* Actually UiDialogContainer has padding and bg. */
      /* So I should strip this down to just layout. */
      display: block;
    }

    .dialog-header {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
    }

    .dialog-icon {
      width: 32px;
      height: 32px;
      border-radius: 50%;
      background: rgba(255, 176, 32, 0.1); /* Warning bg */
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px solid rgba(255, 176, 32, 0.3);
      flex-shrink: 0;
    }

    .icon-symbol {
      font-weight: 800;
      font-size: 18px;
      color: #ffb020; /* Warning color */
    }

    .dialog-title {
      margin: 0;
      font-size: 1.125rem;
      font-weight: 600;
      color: var(--janus-text-primary);
    }

    .dialog-message {
      margin: 0 0 24px 0;
      font-size: 0.94rem;
      color: var(--janus-text-secondary);
      line-height: 1.6;
      white-space: pre-line;
    }

    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }
  `]
})
export class ConfirmDialogComponent {
  data = inject<ConfirmDialogData>(UI_DIALOG_DATA)
  private dialogRef = inject(UiDialogRef<boolean>)

  get confirmVariant(): 'default' | 'destructive' {
    return this.data.confirmColor === 'primary' ? 'default' : 'destructive';
  }

  onConfirm(): void {
    this.dialogRef.close(true)
  }

  onCancel(): void {
    this.dialogRef.close(false)
  }
}
