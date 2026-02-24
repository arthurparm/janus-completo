import { Injectable, NgZone } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { API_BASE_URL } from '../../services/api.config';
import { AuthService } from '../auth/auth.service';
import { AppLoggerService } from './app-logger.service';

export interface AgentEvent {
    task_id: string;
    agent_role: string;
    event_type: string;
    content: string;
    conversation_id: string;
    timestamp: number;
}

@Injectable({
    providedIn: 'root'
})
export class AgentEventsService {
    private eventSource?: EventSource;
    private _events$ = new Subject<AgentEvent>();
    private currentConversationId?: string;

    constructor(
        private zone: NgZone,
        private auth: AuthService,
        private logger: AppLoggerService
    ) { }

    public get events$(): Observable<AgentEvent> {
        return this._events$.asObservable();
    }

    public connect(conversationId: string): void {
        if (this.eventSource) {
            this.eventSource.close();
        }
        this.currentConversationId = conversationId;

        // Prepare URL with user_id param for simple auth/tracking
        let url = `${API_BASE_URL}/v1/chat/${conversationId}/events`;

        // Attempt to get current user ID
        // Note: AuthService might expose it synchronously or we might need to subscribe.
        // For simplicity, we assume we can get it from localStorage or AuthService state if available.
        // Let's rely on backend 'http.state' (cookies) mostly, but ideally we pass query param.
        // Assuming auth.currentUser value is available or we decode token.
        const user = this.auth.currentUserValue; // Hypothetical accessor
        if (user?.id) {
            url += `?user_id=${user.id}`;
        }

        this.logger.info('[AgentEvents] Connecting', { url });

        this.eventSource = new EventSource(url);

        this.eventSource.onmessage = (event) => {
            this.zone.run(() => {
                try {
                    const data = JSON.parse(event.data);
                    this._events$.next(this.normalizeEvent(data));
                } catch (e) {
                    this.logger.error('[AgentEvents] Error parsing event', e);
                }
            });
        };

        this.eventSource.onerror = (_error) => {
            this.zone.run(() => {
                // EventSource automatically retries, but we logs it
                // If state is CLOSED (2), we might need manual reconnect logic or let it be.
                if (this.eventSource?.readyState === EventSource.CLOSED) {
                    this.logger.warn('[AgentEvents] Connection closed');
                }
            });
        };

        // Listen for named events if the backend sends them (e.g. event: agent_event)
        this.eventSource.addEventListener('agent_event', (event: MessageEvent) => {
            this.zone.run(() => {
                try {
                    const data = JSON.parse(event.data);
                    this._events$.next(this.normalizeEvent(data));
                } catch (e) {
                    this.logger.error('[AgentEvents] Error parsing named event', e);
                }
            });
        });
    }

    public disconnect(): void {
        if (this.eventSource) {
            this.logger.info('[AgentEvents] Disconnecting');
            this.eventSource.close();
            this.eventSource = undefined;
        }
        this.currentConversationId = undefined;
    }

    /**
     * Normaliza eventos vindos do SSE para o formato esperado pelo HUD.
     * Backend pode enviar chaves diferentes (type vs event_type, agent vs agent_role).
     */
    private normalizeEvent(data: any): AgentEvent {
        const now = Date.now();
        return {
            event_type: data?.event_type || data?.type || 'unknown',
            agent_role: data?.agent_role || data?.agent || 'unknown',
            content: data?.content || '',
            conversation_id: data?.conversation_id || this.currentConversationId || '',
            task_id: data?.task_id || data?.thread_id || data?.conversation_id || this.currentConversationId || '',
            timestamp: data?.timestamp ? Number(data.timestamp) : now
        };
    }
}
