import { Component, inject } from '@angular/core'
import { CommonModule } from '@angular/common'
import { UiSpinnerComponent } from '../ui/spinner/spinner.component'
import { UI_DIALOG_DATA } from '../ui/dialog/dialog.tokens'

@Component({
  selector: 'app-loading-dialog',
  standalone: true,
  imports: [CommonModule, UiSpinnerComponent],
  template: `
    <div class="loading-dialog-content">
      <ui-spinner [size]="40"></ui-spinner>
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
      /* Background/border/shadow handled by container? No, container has p-6.
         But loading dialog might want cleaner look.
         Let's keep these styles as they define the inner layout.
         But container usually has white bg.
      */
      /* background: var(--janus-bg-card); */
      /* border: 1px solid var(--janus-border); */
      /* border-radius: var(--janus-radius-lg); */
      /* box-shadow: var(--janus-shadow-glow); */
      /* Actually, since UiDialogContainer provides the card, we don't need double card. */
      /* Just layout. */
    }

    .loading-message {
      margin: 0;
      font-size: 1rem;
      font-weight: 500;
      color: var(--janus-text-primary);
      text-align: center;
      letter-spacing: 0.5px;
    }
  `]
})
export class LoadingDialogComponent {
  data = inject<{ message: string }>(UI_DIALOG_DATA)
}
