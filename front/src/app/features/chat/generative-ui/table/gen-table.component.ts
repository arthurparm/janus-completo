import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'app-gen-table',
    standalone: true,
    imports: [CommonModule],
    template: `
    <div class="rounded-md border border-slate-200 dark:border-slate-800 bg-card text-card-foreground shadow-sm overflow-hidden my-4">
      <div class="overflow-x-auto w-full" *ngIf="columns.length > 0; else emptyState">
        <table class="w-full caption-bottom text-sm text-left">
          <thead class="[&_tr]:border-b border-slate-200 dark:border-slate-800">
            <tr class="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
              <th *ngFor="let col of columns" class="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                {{ col.header }}
              </th>
            </tr>
          </thead>
          <tbody class="[&_tr:last-child]:border-0">
            <tr *ngFor="let row of rows" class="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted border-slate-200 dark:border-slate-800">
              <td *ngFor="let col of columns" class="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                {{ row[col.key] }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <ng-template #emptyState>
        <div class="p-4 text-sm text-muted-foreground">No table data available.</div>
      </ng-template>
    </div>
  `
})
export class GenTableComponent implements OnChanges {
    @Input() data: any; // { columns: string[] | { header: string; key: string }[], rows?: any[], data?: any[] }

    columns: Array<{ header: string; key: string }> = [];
    rows: Array<Record<string, any>> = [];

    ngOnChanges(changes: SimpleChanges): void {
        if (changes['data']) {
            this.normalizeData();
        }
    }

    private normalizeData(): void {
        const input = this.data || {};
        const rawColumns = Array.isArray(input.columns) ? input.columns : [];
        const rawRows = Array.isArray(input.rows)
            ? input.rows
            : Array.isArray(input.data)
                ? input.data
                : Array.isArray(input.items)
                    ? input.items
                    : [];

        if (rawColumns.length > 0) {
            this.columns = rawColumns.map((col: any, index: number) => {
                if (typeof col === 'string') {
                    return { header: col, key: col };
                }
                if (col && typeof col === 'object') {
                    const key = String(col.key ?? col.field ?? col.name ?? col.header ?? `col_${index}`);
                    const header = String(col.header ?? col.label ?? col.name ?? key);
                    return { header, key };
                }
                return { header: `Column ${index + 1}`, key: `col_${index}` };
            });
        } else if (rawRows.length > 0 && rawRows[0] && typeof rawRows[0] === 'object') {
            this.columns = Object.keys(rawRows[0]).map((key) => ({ header: key, key }));
        } else {
            this.columns = [];
        }

        this.rows = rawRows;
    }
}
