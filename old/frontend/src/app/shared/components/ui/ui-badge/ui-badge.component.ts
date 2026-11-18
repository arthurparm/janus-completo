import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'ui-badge',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './ui-badge.component.html',
    styleUrls: ['./ui-badge.component.scss']
})
export class UiBadgeComponent {
    @Input() variant: 'neutral' | 'success' | 'warning' | 'error' | 'info' = 'neutral';
}
