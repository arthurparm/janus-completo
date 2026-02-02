import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

@Component({
    selector: 'ui-icon',
    standalone: true,
    imports: [CommonModule],
    template: `
    <span
      class="material-icons select-none"
      [class]="classes"
      [style.font-size.px]="size"
      aria-hidden="true">
      <ng-content></ng-content>
    </span>
  `
})
export class UiIconComponent {
    @Input() size?: number;
    @Input() class = '';

    get classes() {
        return cn(
            // Default size if not specified
            { 'text-base': !this.size },
            this.class
        );
    }
}
