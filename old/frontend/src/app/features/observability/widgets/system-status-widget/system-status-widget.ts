import { Component, DestroyRef, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import {
    ServiceHealthItem,
    SystemStatusResponse,
    SystemStatusService,
} from '../../../../core/services/system-status.service';

@Component({
    selector: 'app-system-status-widget',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './system-status-widget.html',
    styleUrls: ['./system-status-widget.scss']
})
export class SystemStatusWidgetComponent implements OnInit {
    private readonly statusService = inject(SystemStatusService);
    private readonly destroyRef = inject(DestroyRef);

    systemStatus = signal<SystemStatusResponse | null>(null);
    services = signal<ServiceHealthItem[]>([]);
    loading = signal(true);
    error = signal<string | null>(null);

    ngOnInit(): void {
        this.loadData();
    }

    private loadData(): void {
        this.loading.set(true);
        this.error.set(null);

        this.statusService.getSystemStatus()
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe(status => {
                this.systemStatus.set(status);
                this.loading.set(false);
            });

        this.statusService.getServicesHealth()
            .pipe(takeUntilDestroyed(this.destroyRef))
            .subscribe(res => {
                this.services.set(res.services);
            });
    }

    formatUptime(seconds?: number | null): string {
        if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds < 0) {
            return 'N/A';
        }
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
        if (s === 'DEGRADED' || s === 'WARNING' || s === 'UNKNOWN') return 'yellow';
        return 'red';
    }
}
