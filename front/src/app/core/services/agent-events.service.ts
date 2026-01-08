import { Injectable, NgZone } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { API_BASE_URL } from '../../services/api.config';
import { AuthService } from '../auth/auth.service';

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

    constructor(
        private zone: NgZone,
        private auth: AuthService
    ) { }

    public get events$(): Observable<AgentEvent> {
        return this._events$.asObservable();
    }

    public connect(conversationId: string): void {
        if (this.eventSource) {
            this.eventSource.close();
        }

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

        console.log(`[AgentEvents] Connecting to ${url}`);

        this.eventSource = new EventSource(url);

        this.eventSource.onmessage = (event) => {
            this.zone.run(() => {
                try {
                    const data = JSON.parse(event.data) as AgentEvent;
                    this._events$.next(data);
                } catch (e) {
                    console.error('[AgentEvents] Error parsing event', e);
                }
            });
        };

        this.eventSource.onerror = (error) => {
            this.zone.run(() => {
                // EventSource automatically retries, but we logs it
                // If state is CLOSED (2), we might need manual reconnect logic or let it be.
                if (this.eventSource?.readyState === EventSource.CLOSED) {
                    console.log('[AgentEvents] Connection closed');
                }
            });
        };

        // Listen for named events if the backend sends them (e.g. event: agent_event)
        this.eventSource.addEventListener('agent_event', (event: MessageEvent) => {
            this.zone.run(() => {
                try {
                    const data = JSON.parse(event.data) as AgentEvent;
                    this._events$.next(data);
                } catch (e) {
                    console.error('[AgentEvents] Error parsing named event', e);
                }
            });
        });
    }

    public disconnect(): void {
        if (this.eventSource) {
            console.log('[AgentEvents] Disconnecting');
            this.eventSource.close();
            this.eventSource = undefined;
        }
    }
}
