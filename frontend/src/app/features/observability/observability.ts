import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { SystemStatusWidgetComponent } from './widgets/system-status-widget/system-status-widget';
import { DatabaseHealthWidgetComponent } from './widgets/database-health-widget/database-health-widget';
import { KnowledgeHealthWidgetComponent } from './widgets/knowledge-health-widget/knowledge-health-widget';
import { AppLoggerService } from '../../core/services/app-logger.service';

@Component({
    selector: 'app-observability',
    standalone: true,
    imports: [CommonModule, SystemStatusWidgetComponent, DatabaseHealthWidgetComponent, KnowledgeHealthWidgetComponent],
    templateUrl: './observability.html',
    styleUrls: ['./observability.scss']
})
export class ObservabilityComponent implements OnInit, OnDestroy {
    autoRefreshEnabled = signal(true); // Default: ON per user requirement
    private refreshSubscription?: Subscription;
    private readonly REFRESH_INTERVAL_MS = 5000; // 5 seconds
    private readonly logger = inject(AppLoggerService);

    ngOnInit(): void {
        this.startAutoRefresh();
    }

    ngOnDestroy(): void {
        this.stopAutoRefresh();
    }

    toggleAutoRefresh(): void {
        this.autoRefreshEnabled.update(enabled => !enabled);
        if (this.autoRefreshEnabled()) {
            this.startAutoRefresh();
        } else {
            this.stopAutoRefresh();
        }
    }

    private startAutoRefresh(): void {
        if (this.autoRefreshEnabled()) {
            // Auto-refresh logic will be implemented when widgets are ready
            // Widgets will handle their own data fetching via services
            this.logger.info('[Observability] Auto-refresh enabled', {
                intervalMs: this.REFRESH_INTERVAL_MS,
            });
        }
    }

    private stopAutoRefresh(): void {
        this.refreshSubscription?.unsubscribe();
        this.logger.info('[Observability] Auto-refresh disabled');
    }
}
