import { Component, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UiToastComponent } from './toast.component';
import { ToastData } from './toast.types';

@Component({
    selector: 'ui-toaster',
    standalone: true,
    imports: [CommonModule, UiToastComponent],
    template: `
    <div class="fixed top-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col md:max-w-[420px]">
      @for (toast of toasts; track toast.id) {
        <ui-toast 
          [data]="toast" 
          (close)="remove(toast.id)">
        </ui-toast>
      }
    </div>
  `,
    changeDetection: ChangeDetectionStrategy.OnPush
})
export class UiToasterComponent {
    toasts: ToastData[] = [];

    constructor(private cdr: ChangeDetectorRef) { }

    add(toast: ToastData) {
        this.toasts.push(toast);
        this.cdr.markForCheck();
    }

    remove(id: number) {
        this.toasts = this.toasts.filter(t => t.id !== id);
        this.cdr.markForCheck();
    }
}
