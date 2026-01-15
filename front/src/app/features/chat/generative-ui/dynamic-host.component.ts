import { Component, Input, OnChanges, SimpleChanges, Type } from '@angular/core';
import { CommonModule } from '@angular/common';
import { GenTableComponent } from './table/gen-table.component';

@Component({
    selector: 'app-dynamic-host',
    standalone: true,
    imports: [CommonModule],
    template: `
    <ng-container *ngIf="component" [ngComponentOutlet]="component" [ngComponentOutletInputs]="inputs"></ng-container>
    <div *ngIf="!component" class="p-4 rounded bg-destructive/10 text-destructive text-sm">
      Unsupported UI type: {{ type }}
    </div>
  `
})
export class DynamicHostComponent implements OnChanges {
    @Input() type!: string;
    @Input() data: any;

    component: Type<any> | null = null;
    inputs: Record<string, any> = {};

    private componentMap: Record<string, Type<any>> = {
        'table': GenTableComponent
    };

    ngOnChanges(changes: SimpleChanges): void {
        if (changes['type'] || changes['data']) {
            this.loadComponent();
        }
    }

    private loadComponent() {
        this.component = this.componentMap[this.type] || null;
        this.inputs = { data: this.data };
    }
}
