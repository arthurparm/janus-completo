import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'ui-table',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './ui-table.component.html',
    styleUrls: ['./ui-table.component.scss']
})
export class UiTableComponent {
    @Input() striped = false;
    @Input() responsive = true;
}
