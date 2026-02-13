import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { interval, Subscription } from 'rxjs';
import { switchMap, catchError } from 'rxjs/operators';
import { of } from 'rxjs';
import { JanusApiService, SystemStatus, ServiceHealthItem } from '../../../../services/janus-api.service';

@Component({
    selector: 'app-system-status-widget',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './system-status-widget.html',
    styleUrls: ['./system-status-widget.scss']
})
export class SystemStatusWidgetComponent implements OnInit, OnDestroy {
    private api = inject(JanusApiService);
    private refreshSub?: Subscription;

    systemStatus = signal<SystemStatus | null>(null);
    services = signal<ServiceHealthItem[]>([]);
    loading = signal(true);
    error = signal<string | null>(null);

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

        this.api.getSystemStatus().pipe(
            catchError(() => of(null))
        ).subscribe(status => {
            this.systemStatus.set(status);
            this.loading.set(false);
        });

        this.api.getServicesHealth().pipe(
            catchError(() => of({ services: [] }))
        ).subscribe(res => {
            this.services.set(res.services);
        });
    }

    private startAutoRefresh(): void {
        this.refreshSub = interval(5000).pipe(
            switchMap(() => {
                return this.api.getSystemStatus().pipe(catchError(() => of(null)));
            })
        ).subscribe(status => {
            if (status) this.systemStatus.set(status);
        });
    }

    formatUptime(seconds?: number): string {
        if (!seconds) return 'N/A';
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const mins = Math.floor((seconds % 3600) / 60);

        if (days > 0) return `${days}d ${hours}h ${mins}m`;
        if (hours > 0) return `${hours}h ${mins}m`;
        return `${mins}m ${Math.floor(seconds % 60)}s`;
    }

    getStatusColor(status?: string): string {
        if (!status) return 'gray';
        const s = status.toUpperCase();
        if (s === 'OPERATIONAL' || s === 'HEALTHY' || s === 'OK') return 'green';
        if (s === 'DEGRADED' || s === 'WARNING') return 'yellow';
        return 'red';
    }
}
