import { Component, inject, OnInit, OnDestroy, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription, catchError, forkJoin, interval, map, of, startWith } from 'rxjs';
import { SystemStatusWidgetComponent } from './widgets/system-status-widget/system-status-widget';
import { DatabaseHealthWidgetComponent } from './widgets/database-health-widget/database-health-widget';
import { KnowledgeHealthWidgetComponent } from './widgets/knowledge-health-widget/knowledge-health-widget';
import { AppLoggerService } from '../../core/services/app-logger.service';
import {
  BackendApiService,
  OrchestratorWorkerTaskStatus,
  QueueInfoResponse,
} from '../../services/backend-api.service';

@Component({
    selector: 'app-observability',
    standalone: true,
    imports: [CommonModule, SystemStatusWidgetComponent, DatabaseHealthWidgetComponent, KnowledgeHealthWidgetComponent],
    templateUrl: './observability.html',
    styleUrls: ['./observability.scss']
})
export class ObservabilityComponent implements OnInit, OnDestroy {
    autoRefreshEnabled = signal(true); // Default: ON per user requirement
    operatorLoading = signal(false);
    operatorError = signal<string | null>(null);
    workers = signal<OrchestratorWorkerTaskStatus[]>([]);
    queues = signal<QueueInfoResponse[]>([]);
    lastRefreshAt = signal<string | null>(null);
    private refreshSubscription?: Subscription;
    private readonly REFRESH_INTERVAL_MS = 5000; // 5 seconds
    private readonly logger = inject(AppLoggerService);
    private readonly api = inject(BackendApiService);
    private readonly queueNames = [
        'janus.tasks.router',
        'janus.agent.tasks',
        'janus.knowledge.consolidation',
        'janus.tasks.codex',
    ];

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
        this.stopAutoRefresh();
        this.refreshSubscription = interval(this.REFRESH_INTERVAL_MS)
            .pipe(startWith(0))
            .subscribe(() => this.refreshOperatorView());
        this.logger.info('[Observability] Auto-refresh enabled', {
            intervalMs: this.REFRESH_INTERVAL_MS,
        });
    }

    private stopAutoRefresh(): void {
        this.refreshSubscription?.unsubscribe();
        this.refreshSubscription = undefined;
        this.logger.info('[Observability] Auto-refresh disabled');
    }

    private refreshOperatorView(): void {
        this.operatorLoading.set(true);
        this.operatorError.set(null);

        const queueRequests = this.queueNames.map((queueName) =>
            this.api.getQueueInfo(queueName).pipe(
                catchError(() =>
                    of({
                        name: queueName,
                        messages: -1,
                        consumers: 0,
                    } satisfies QueueInfoResponse)
                )
            )
        );

        forkJoin({
            workers: this.api.getWorkersStatus().pipe(map((response) => response.workers || [])),
            queues: queueRequests.length ? forkJoin(queueRequests) : of([] as QueueInfoResponse[]),
        })
            .pipe(
                catchError((error) => {
                    this.logger.error('[Observability] Failed to refresh operator view', error);
                    this.operatorError.set('Nao foi possivel atualizar a visao de operador.');
                    return of({
                        workers: [] as OrchestratorWorkerTaskStatus[],
                        queues: [] as QueueInfoResponse[],
                    });
                })
            )
            .subscribe((snapshot) => {
                this.workers.set(snapshot.workers);
                this.queues.set(snapshot.queues);
                this.operatorLoading.set(false);
                this.lastRefreshAt.set(new Date().toLocaleTimeString());
            });
    }
}
