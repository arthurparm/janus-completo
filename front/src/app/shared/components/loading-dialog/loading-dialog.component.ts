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
      padding: 32px;
      gap: 20px;
      background: var(--janus-bg-card);
      border: 1px solid var(--janus-border);
      border-radius: var(--janus-radius-lg);
      box-shadow: var(--janus-shadow-glow);
    }

    .loading-message {
      margin: 0;
      font-size: 1rem;
      font-weight: 500;
      color: var(--janus-text-primary);
      text-align: center;
      letter-spacing: 0.5px;
    }

    /* Override spinner color via CSS variable or ::ng-deep if needed, 
       but Angular Material might use its own theming. 
       Let's try to set the theme color if possible or trust standard material theme. 
    */
    ::ng-deep .mat-mdc-progress-spinner circle, .mat-mdc-progress-spinner circle {
        stroke: var(--janus-primary) !important;
    }
  `]
})
export class LoadingDialogComponent {
  data = inject<{ message: string }>(MAT_DIALOG_DATA)
}
