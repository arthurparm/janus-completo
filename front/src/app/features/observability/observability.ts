import { Component, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { SystemStatusWidgetComponent } from './widgets/system-status-widget/system-status-widget';
import { DatabaseHealthWidgetComponent } from './widgets/database-health-widget/database-health-widget';
import { KnowledgeHealthWidgetComponent } from './widgets/knowledge-health-widget/knowledge-health-widget';

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
        }
    }

    private stopAutoRefresh(): void {
        this.refreshSubscription?.unsubscribe();
    }
}
