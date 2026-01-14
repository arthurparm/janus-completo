import { Component, inject } from '@angular/core'
import { CommonModule } from '@angular/common'
import { MatButtonModule } from '@angular/material/button'
import { MAT_DIALOG_DATA, MatDialogRef } from '@angular/material/dialog'

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
  imports: [CommonModule, MatButtonModule],
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
        <button class="btn btn-secondary btn-sm" (click)="onCancel()">
          {{ data.cancelText || 'Cancelar' }}
        </button>
        <button
          class="btn btn-sm"
          [class.btn-danger]="data.confirmColor === 'warn' || !data.confirmColor"
          [class.btn-primary]="data.confirmColor === 'primary'"
          (click)="onConfirm()">
          {{ data.confirmText || 'Confirmar' }}
        </button>
      </div>
    </div>
  `,
  styles: [`
    .confirm-dialog-content {
      padding: 24px;
      max-width: 420px;
      background: var(--janus-bg-card);
      border-radius: var(--janus-radius-lg);
      border: 1px solid var(--janus-border);
      box-shadow: var(--janus-shadow-glow);
      color: var(--janus-text-primary);
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

    /* Inline btn styles if global styles not applied in ViewEncapsulation.Emulated (default) */
    /* But since we use simple classes, we can rely on global styles if we didn't encapsulate too strictly. */
    /* Actually, Angular component styles are encapsulated. So .btn classes from global styles MIGHT NOT apply if they are not ::ng-deep or if we don't import them. */
    /* Best practice: Import tokens and define/re-use styles or use the global class if it's available. */
    /* Since we added .btn to global styles (styles.scss), it SHOULD be available if we don't override it, BUT Angular View Encapsulation usually isolates component styles. */
    /* HOWEVER, global styles defined in styles.scss are available to all components unless shadowed. */
    /* Wait, global styles in styles.scss are NOT encapsulated, they apply globally. */
    /* So <button class="btn"> should work! */
    
    .btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 8px 16px;
        border-radius: var(--janus-radius-md);
        font-weight: 500;
        cursor: pointer;
        border: 1px solid transparent;
        transition: all 0.2s;
    }

    .btn-sm {
        padding: 6px 12px;
        font-size: 0.875rem;
    }

    .btn-secondary {
        background-color: transparent;
        border-color: var(--janus-border);
        color: var(--janus-text-primary);
    }
    .btn-secondary:hover {
        background-color: rgba(255, 255, 255, 0.05);
    }

    .btn-danger {
        background-color: rgba(255, 0, 85, 0.1);
        border-color: var(--janus-accent);
        color: var(--janus-accent);
    }
    .btn-danger:hover {
        background-color: rgba(255, 0, 85, 0.2);
        box-shadow: 0 0 10px rgba(255, 0, 85, 0.2);
    }

    .btn-primary {
        background-color: var(--janus-primary);
        color: var(--janus-bg-dark);
    }
    .btn-primary:hover {
        background-color: var(--janus-primary-hover);
    }

  `]
})
export class ConfirmDialogComponent {
  data = inject<ConfirmDialogData>(MAT_DIALOG_DATA)
  private dialogRef = inject(MatDialogRef<ConfirmDialogComponent>)

  onConfirm(): void {
    this.dialogRef.close(true)
  }

  onCancel(): void {
    this.dialogRef.close(false)
  }
}
