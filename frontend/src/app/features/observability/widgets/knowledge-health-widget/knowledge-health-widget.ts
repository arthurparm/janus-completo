import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { interval, Subscription } from 'rxjs';
import { switchMap, catchError } from 'rxjs/operators';
import { of } from 'rxjs';
import { BackendApiService, KnowledgeHealthResponse, KnowledgeHealthDetailedResponse } from '../../../../services/backend-api.service';

@Component({
    selector: 'app-knowledge-health-widget',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './knowledge-health-widget.html',
    styleUrls: ['./knowledge-health-widget.scss']
})
export class KnowledgeHealthWidgetComponent implements OnInit, OnDestroy {
    private api = inject(BackendApiService);
    private refreshSub?: Subscription;

    health = signal<KnowledgeHealthResponse | null>(null);
    detailed = signal<KnowledgeHealthDetailedResponse | null>(null);
    loading = signal(true);
    error = signal<string | null>(null);
    showDetailed = signal(false);
    resetting = signal(false);

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

        this.api.getKnowledgeHealth().pipe(
            catchError((err) => {
                this.error.set(err.message || 'Failed to load knowledge health');
                return of(null);
            })
        ).subscribe(data => {
            this.health.set(data);
            this.loading.set(false);
        });

        this.api.getKnowledgeHealthDetailed().pipe(
            catchError(() => of(null))
        ).subscribe(data => {
            this.detailed.set(data);
        });
    }

    private startAutoRefresh(): void {
        this.refreshSub = interval(5000).pipe(
            switchMap(() => this.api.getKnowledgeHealth().pipe(catchError(() => of(null))))
        ).subscribe(data => {
            if (data) this.health.set(data);
        });
    }

    resetCircuitBreaker(): void {
        if (!confirm('Are you sure you want to reset the circuit breaker?')) return;

        this.resetting.set(true);
        this.api.resetKnowledgeCircuitBreaker().pipe(
            catchError((err) => {
                alert('Failed to reset circuit breaker: ' + err.message);
                return of(null);
            })
        ).subscribe(() => {
            this.resetting.set(false);
            this.loadData(); // Refresh data after reset
        });
    }

    toggleDetailed(): void {
        this.showDetailed.update(v => !v);
    }

    getOverallStatus(): string {
        const h = this.health();
        if (!h) return 'unknown';
        if (h.circuit_breaker_open) return 'degraded';
        if (!h.neo4j_connected || !h.qdrant_connected) return 'degraded';
        return h.status?.toLowerCase() || 'unknown';
    }

    getConnectionStatus(service: 'neo4j' | 'qdrant'): string {
        const h = this.health();
        if (!h) return 'unknown';
        return service === 'neo4j' ? (h.neo4j_connected ? 'connected' : 'disconnected')
            : (h.qdrant_connected ? 'connected' : 'disconnected');
    }
}
