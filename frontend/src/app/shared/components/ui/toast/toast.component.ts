import { Component, EventEmitter, Input, OnInit, Output, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastData } from './toast.types';
import { UiIconComponent } from '../icon/icon.component';
import { UiButtonComponent } from '../button/button.component';
import { animate, style, transition, trigger } from '@angular/animations';

@Component({
    selector: 'ui-toast',
    standalone: true,
    imports: [CommonModule, UiIconComponent, UiButtonComponent],
    template: `
    <div class="pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-6 pr-8 shadow-lg transition-all"
         [class]="getClasses()">
      
      <div class="flex items-center gap-3">
         @if (getIcon()) {
           <ui-icon [class]="getIconClass()">{{ getIcon() }}</ui-icon>
         }
         <div class="grid gap-1">
            <p class="text-sm font-semibold opacity-90">{{ data.message }}</p>
         </div>
      </div>

      <div class="flex items-center gap-2">
         @if (data.action) {
           <button ui-button variant="outline" size="sm" (click)="onAction()">
               {{ data.action }}
           </button>
         }
         
         <button ui-button variant="ghost" size="icon" class="h-6 w-6 text-foreground/50 hover:text-foreground" (click)="onClose()">
            <ui-icon class="scale-75">close</ui-icon>
         </button>
      </div>
    </div>
  `,
    styles: [`
    :host {
        display: block;
        width: 100%;
    }
  `],
    host: {
        '[@toastState]': 'true',
        'role': 'alert'
    },
    animations: [
        trigger('toastState', [
            transition(':enter', [
                style({ transform: 'translateX(100%)', opacity: 0 }),
                animate('150ms ease-out', style({ transform: 'translateX(0)', opacity: 1 }))
            ]),
            transition(':leave', [
                animate('150ms ease-in', style({ opacity: 0, transform: 'translateX(100%)' }))
            ])
        ])
    ]
})
export class UiToastComponent implements OnInit, OnDestroy {
    @Input({ required: true }) data!: ToastData;
    @Output() close = new EventEmitter<void>();

    private timeout: any;

    ngOnInit() {
        if (this.data.duration && this.data.duration > 0) {
            this.timeout = setTimeout(() => {
                this.onClose();
            }, this.data.duration);
        }
    }

    ngOnDestroy() {
        if (this.timeout) clearTimeout(this.timeout);
    }

    onClose() {
        this.close.emit();
    }

    onAction() {
        if (this.data.actionCallback) {
            this.data.actionCallback();
        }
        this.onClose(); // Automatically close on action? Usually yes.
    }

    getClasses(): string {
        const base = 'group pointer-events-auto relative flex w-full items-center justify-between space-x-4 overflow-hidden rounded-md border p-6 pr-8 shadow-lg transition-all';

        switch (this.data.type || 'default') {
            case 'default':
                return `${base} border bg-background text-foreground`;
            case 'destructive':
            case 'error':
                return `${base} destructive group border-destructive bg-destructive text-destructive-foreground`;
            case 'success':
                return `${base} border-green-500 bg-green-50 text-green-900 dark:bg-green-900/20 dark:text-green-100`;
            case 'warning':
                return `${base} border-yellow-500 bg-yellow-50 text-yellow-900 dark:bg-yellow-900/20 dark:text-yellow-100`;
            case 'info':
                return `${base} border-blue-500 bg-blue-50 text-blue-900 dark:bg-blue-900/20 dark:text-blue-100`;
            default:
                return `${base} border bg-background text-foreground`;
        }
    }

    getIcon(): string | null {
        switch (this.data.type) {
            case 'error': return 'error';
            case 'destructive': return 'error';
            case 'success': return 'check_circle';
            case 'warning': return 'warning';
            case 'info': return 'info';
            default: return null;
        }
    }

    getIconClass(): string {
        // styles handled by container variant mostly, but icons might need specific coloring in default mode if we want,
        // but 'default' usually has no icon or neutral.
        if (this.data.type === 'default') return '';
        return ''; // inherited from text color
    }
}
