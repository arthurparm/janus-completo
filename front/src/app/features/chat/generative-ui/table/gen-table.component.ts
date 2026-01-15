import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'app-gen-table',
    standalone: true,
    imports: [CommonModule],
    template: `
    <div class="rounded-md border border-slate-200 dark:border-slate-800 bg-card text-card-foreground shadow-sm overflow-hidden my-4">
      <div class="overflow-x-auto w-full">
        <table class="w-full caption-bottom text-sm text-left">
          <thead class="[&_tr]:border-b border-slate-200 dark:border-slate-800">
            <tr class="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
              <th *ngFor="let col of data.columns" class="h-12 px-4 text-left align-middle font-medium text-muted-foreground [&:has([role=checkbox])]:pr-0">
                {{ col.header }}
              </th>
            </tr>
          </thead>
          <tbody class="[&_tr:last-child]:border-0">
            <tr *ngFor="let row of data.rows" class="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted border-slate-200 dark:border-slate-800">
              <td *ngFor="let col of data.columns" class="p-4 align-middle [&:has([role=checkbox])]:pr-0">
                {{ row[col.key] }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  `
})
export class GenTableComponent {
    @Input() data: any; // { columns: { header: string, key: string }[], rows: any[] }
}
