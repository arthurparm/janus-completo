import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { interval, Subscription } from 'rxjs';
import { switchMap, catchError } from 'rxjs/operators';
import { of } from 'rxjs';
import { JanusApiService, DbValidationResponse, DbValidationCheck } from '../../../../services/janus-api.service';

@Component({
    selector: 'app-database-health-widget',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './database-health-widget.html',
    styleUrls: ['./database-health-widget.scss']
})
export class DatabaseHealthWidgetComponent implements OnInit, OnDestroy {
    private api = inject(JanusApiService);
    private refreshSub?: Subscription;

    validation = signal<DbValidationResponse | null>(null);
    loading = signal(true);
    error = signal<string | null>(null);
    filter = signal<'all' | 'exists' | 'missing'>('all');

    ngOnInit(): void {
        this.loadData();
        this.startAutoRefresh();
    }

    ngOnDestroy(): void {
        this.refreshSub?.unsubscribe();
    }

    private loadData(): void {
        this.loading.set(true);
        this.error.set(null);

        this.api.getSystemDbValidate().pipe(
            catchError((err) => {
                this.error.set(err.message || 'Failed to load DB validation');
                return of(null);
            })
        ).subscribe(data => {
            this.validation.set(data);
            this.loading.set(false);
        });
    }

    private startAutoRefresh(): void {
        this.refreshSub = interval(5000).pipe(
            switchMap(() => this.api.getSystemDbValidate().pipe(catchError(() => of(null))))
        ).subscribe(data => {
            if (data) this.validation.set(data);
        });
    }

    filteredChecks(): DbValidationCheck[] {
        const checks = this.validation()?.checks || [];
        const f = this.filter();
        if (f === 'exists') return checks.filter(c => c.exists);
        if (f === 'missing') return checks.filter(c => !c.exists);
        return checks;
    }

    exportToJSON(): void {
        const data = JSON.stringify(this.validation(), null, 2);
        const blob = new Blob([data], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `db-validation-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }

    getStatusSummary(): { exists: number; missing: number } {
        const checks = this.validation()?.checks || [];
        return {
            exists: checks.filter(c => c.exists).length,
            missing: checks.filter(c => !c.exists).length
        };
    }
}
