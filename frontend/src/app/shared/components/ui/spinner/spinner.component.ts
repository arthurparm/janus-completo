import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

type SpinnerSize = number | 'sm' | 'md' | 'lg' | 'xl';

const SIZE_MAP: Record<'sm' | 'md' | 'lg' | 'xl', number> = {
    sm: 16,
    md: 24,
    lg: 32,
    xl: 48
};

@Component({
    selector: 'ui-spinner',
    standalone: true,
    imports: [CommonModule],
    template: `
    <div role="status" [class]="containerClasses" [style.width.px]="size" [style.height.px]="size">
        <svg
            class="animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            [class]="svgClasses"
        >
            <circle
            class="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            stroke-width="4"
            ></circle>
            <path
            class="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
        </svg>
        <span class="sr-only">Loading...</span>
    </div>
  `
})
export class UiSpinnerComponent {
    private sizePx = SIZE_MAP.md;

    @Input() set size(value: SpinnerSize) {
        this.sizePx = this.resolveSize(value);
    }

    get size(): number {
        return this.sizePx;
    }

    @Input() color: 'primary' | 'secondary' | 'accent' | 'muted' | 'white' | 'warn' = 'primary';
    @Input('class') userClass = '';

    // Adapter input for MatProgressSpinner compatibility
    @Input() set diameter(val: number) {
        if (val) this.sizePx = val;
    }

    get containerClasses() {
        return cn('inline-flex', this.userClass);
    }

    get svgClasses() {
        return cn('w-full h-full', {
            'text-primary': this.color === 'primary',
            'text-secondary': this.color === 'secondary',
            'text-accent': this.color === 'accent',
            'text-muted-foreground': this.color === 'muted',
            'text-white': this.color === 'white',
            'text-destructive': this.color === 'warn'
        });
    }

    private resolveSize(value: SpinnerSize): number {
        if (typeof value === 'number' && Number.isFinite(value)) {
            return value;
        }
        if (typeof value === 'string') {
            return SIZE_MAP[value] ?? SIZE_MAP.md;
        }
        return SIZE_MAP.md;
    }
}
