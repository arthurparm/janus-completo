import { Component, ViewChild, ViewEncapsulation } from '@angular/core';
import { CommonModule } from '@angular/common';
import { CdkPortalOutlet, PortalModule } from '@angular/cdk/portal';
import { A11yModule } from '@angular/cdk/a11y';

@Component({
    selector: 'ui-dialog-container',
    standalone: true,
    imports: [CommonModule, PortalModule, A11yModule],
    template: `
    <div
      cdkTrapFocus
      cdkTrapFocusAutoCapture
      class="bg-white dark:bg-zinc-900 text-slate-900 dark:text-slate-50 border border-slate-200 dark:border-slate-800 rounded-lg shadow-lg w-full max-w-lg p-6 grid gap-4 animate-in fade-in-0 zoom-in-95 duration-200"
      tabindex="-1">
      <ng-template cdkPortalOutlet></ng-template>
    </div>
  `,
    // Encapsulation none so we can style from global if needed, but Tailwind classes are scoped enough usually.
    // Actually, default is Emulated which is fine.
    styles: [`
    :host {
        display: flex;
        justify-content: center;
        align-items: center;
        padding: 1rem;
        height: 100%;
        max-height: 100dvh;
        pointer-events: none; /* Let clicks pass through if we want custom backdrop handling, but here we want blocks */
    }

    div[cdkTrapFocus] {
        pointer-events: auto;
    }
  `]
})
export class UiDialogContainerComponent {
    @ViewChild(CdkPortalOutlet, { static: true }) portalOutlet!: CdkPortalOutlet;
}
