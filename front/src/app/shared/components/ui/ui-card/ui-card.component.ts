import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'ui-card',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './ui-card.component.html',
    styleUrls: ['./ui-card.component.scss']
})
export class UiCardComponent {
    @Input() title?: string;
    @Input() subtitle?: string;
    @Input() variant: 'default' | 'elevated' = 'default';

    // Helper getters to check content projection populated (simple check, implementation detail might need ElementRef if stricter check needed)
    // For now we assume typical usage triggers layout
    get hasHeaderActions(): boolean {
        // This is a limitation of simple ng-content, can't easily detect if projected.
        // We will assume if title/subtitle missing but header-actions present, user ensures it looks right.
        // Ideally we use ContentChild to check, but let's keep it simple for Sprint 0.
        return true;
    }

    get hasFooter(): boolean {
        return true; // Simplification, rendering empty footer wrapper if unused is minor overhead
    }
}
