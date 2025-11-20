import { Component, inject } from '@angular/core'
import { CommonModule } from '@angular/common'
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner'
import { MAT_DIALOG_DATA } from '@angular/material/dialog'

@Component({
  selector: 'app-loading-dialog',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule],
  template: `
    <div class="loading-dialog-content">
      <mat-spinner diameter="40"></mat-spinner>
      <p class="loading-message">{{ data.message }}</p>
    </div>
  `,
  styles: [`
    .loading-dialog-content {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px;
      gap: 16px;
    }

    .loading-message {
      margin: 0;
      font-size: 1rem;
      color: rgba(0, 0, 0, 0.87);
      text-align: center;
    }
  `]
})
export class LoadingDialogComponent {
  data = inject<{ message: string }>(MAT_DIALOG_DATA)
}