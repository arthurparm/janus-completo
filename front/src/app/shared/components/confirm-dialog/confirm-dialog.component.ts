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
      <h2 class="dialog-title">{{ data.title }}</h2>
      <p class="dialog-message">{{ data.message }}</p>
      <div class="dialog-actions">
        <button mat-button (click)="onCancel()">
          {{ data.cancelText || 'Cancelar' }}
        </button>
        <button 
          mat-raised-button 
          [color]="data.confirmColor || 'primary'"
          (click)="onConfirm()">
          {{ data.confirmText || 'Confirmar' }}
        </button>
      </div>
    </div>
  `,
  styles: [`
    .confirm-dialog-content {
      padding: 24px;
      max-width: 400px;
    }

    .dialog-title {
      margin: 0 0 16px 0;
      font-size: 1.25rem;
      font-weight: 500;
      color: rgba(0, 0, 0, 0.87);
    }

    .dialog-message {
      margin: 0 0 24px 0;
      font-size: 1rem;
      color: rgba(0, 0, 0, 0.6);
      line-height: 1.5;
    }

    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 8px;
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