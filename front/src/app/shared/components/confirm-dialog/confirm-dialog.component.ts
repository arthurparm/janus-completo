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
        <button mat-button class="btn-neutral" (click)="onCancel()">
          {{ data.cancelText || 'Cancelar' }}
        </button>
        <button
          mat-raised-button
          class="btn-danger"
          color="{{ data.confirmColor || 'warn' }}"
          (click)="onConfirm()">
          {{ data.confirmText || 'Confirmar' }}
        </button>
      </div>
    </div>
  `,
  styles: [`
    .confirm-dialog-content {
      padding: 24px 24px 20px;
      max-width: 420px;
      background: rgba(3, 7, 18, 0.96);
      border-radius: 12px;
      border: 1px solid rgba(56, 189, 248, 0.35);
      box-shadow: 0 18px 40px rgba(15, 23, 42, 0.85);
      color: #e5f4ff;
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
      border-radius: 999px;
      background: radial-gradient(circle at 30% 0%, #f97316, #b91c1c);
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 0 18px rgba(248, 113, 113, 0.6);
      flex-shrink: 0;
    }

    .icon-symbol {
      font-weight: 800;
      font-size: 18px;
      color: #fef2f2;
    }

    .dialog-title {
      margin: 0;
      font-size: 1.05rem;
      font-weight: 600;
      letter-spacing: 0.02em;
      color: #f9fafb;
    }

    .dialog-message {
      margin: 0 0 20px 0;
      font-size: 0.94rem;
      color: #9ca3af;
      line-height: 1.6;
      white-space: pre-line;
    }

    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      margin-top: 4px;
    }

    .btn-neutral {
      color: #e5e7eb;
      border-radius: 999px;
      padding-inline: 16px;
      border: 1px solid rgba(148, 163, 184, 0.4);
      background: rgba(15, 23, 42, 0.7);
      min-width: 0;
    }

    .btn-neutral:hover {
      background: rgba(31, 41, 55, 0.9);
      border-color: rgba(148, 163, 184, 0.7);
    }

    .btn-danger {
      background: linear-gradient(135deg, #f97316, #ef4444);
      color: #f9fafb;
      box-shadow: 0 0 14px rgba(248, 113, 113, 0.45);
      border-radius: 999px;
      padding-inline: 20px;
      min-width: 0;
    }

    .btn-danger:hover {
      box-shadow: 0 0 20px rgba(248, 113, 113, 0.7);
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
