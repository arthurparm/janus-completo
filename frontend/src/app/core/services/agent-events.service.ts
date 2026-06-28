import { Injectable, NgZone } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { API_BASE_URL } from '../../services/api.config';
import { buildChatStreamAuthHeaders } from '../../services/chat-auth-headers.util';
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
    private abortController?: AbortController;
    private _events$ = new Subject<AgentEvent>();
    private currentConversationId?: string;
    private connectSeq = 0;

    constructor(
        private zone: NgZone,
        private logger: AppLoggerService
    ) { }

    public get events$(): Observable<AgentEvent> {
        return this._events$.asObservable();
    }

    public connect(conversationId: string): void {
        this.disconnect();
        this.currentConversationId = conversationId;
        const url = `${API_BASE_URL}/v1/chat/${encodeURIComponent(conversationId)}/events`;
        const controller = new AbortController();
        const seq = ++this.connectSeq;
        this.abortController = controller;
        this.logger.info('[AgentEvents] Connecting', { url, conversationId });
        void this.consume(url, controller, seq);
    }

    public disconnect(): void {
        if (this.abortController) {
            this.logger.info('[AgentEvents] Disconnecting');
            try {
                this.abortController.abort();
            } catch {
                /* noop */
            }
            this.abortController = undefined;
        }
        this.currentConversationId = undefined;
    }

    private async consume(url: string, controller: AbortController, seq: number): Promise<void> {
        try {
            const headers = buildChatStreamAuthHeaders();
            headers.set('Accept', 'text/event-stream');
            const response = await fetch(url, {
                method: 'GET',
                headers,
                signal: controller.signal,
            });

            if (!response.ok) {
                this.logger.warn('[AgentEvents] Stream request failed', {
                    status: response.status,
                    conversationId: this.currentConversationId,
                });
                return;
            }

            if (!response.body) {
                this.logger.warn('[AgentEvents] Empty stream body', {
                    conversationId: this.currentConversationId,
                });
                return;
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                if (controller.signal.aborted || seq !== this.connectSeq) return;
                buffer += decoder.decode(value, { stream: true });
                const parsed = this.extractEvents(buffer);
                buffer = parsed.remaining;
                for (const evt of parsed.events) {
                    this.handleEvent(evt.event, evt.data);
                    if (controller.signal.aborted || seq !== this.connectSeq) return;
                }
            }

            buffer += decoder.decode();
            const trailing = this.extractEvents(buffer, true);
            for (const evt of trailing.events) {
                this.handleEvent(evt.event, evt.data);
            }
        } catch (error) {
            if (controller.signal.aborted || seq !== this.connectSeq) {
                return;
            }
            this.logger.error('[AgentEvents] Stream consumption failed', error);
        } finally {
            if (this.abortController === controller) {
                this.abortController = undefined;
            }
        }
    }

    private extractEvents(input: string, flush = false): { events: Array<{ event: string; data: string }>; remaining: string } {
        const normalized = input.replace(/\r\n/g, '\n');
        const events: Array<{ event: string; data: string }> = [];
        let cursor = 0;

        while (true) {
            const separatorIndex = normalized.indexOf('\n\n', cursor);
            if (separatorIndex === -1) break;
            const block = normalized.slice(cursor, separatorIndex);
            cursor = separatorIndex + 2;
            const parsed = this.parseBlock(block);
            if (parsed) events.push(parsed);
        }

        let remaining = normalized.slice(cursor);
        if (flush && remaining.trim()) {
            const parsed = this.parseBlock(remaining);
            if (parsed) events.push(parsed);
            remaining = '';
        }

        return { events, remaining };
    }

    private parseBlock(block: string): { event: string; data: string } | null {
        const lines = block.split('\n');
        let event = 'message';
        const dataLines: string[] = [];

        for (const rawLine of lines) {
            const line = rawLine ?? '';
            if (!line || line.startsWith(':')) continue;
            if (line.startsWith('event:')) {
                event = line.slice('event:'.length).trim() || 'message';
                continue;
            }
            if (line.startsWith('data:')) {
                dataLines.push(line.slice('data:'.length).trimStart());
            }
        }

        if (dataLines.length === 0) return null;
        return { event, data: dataLines.join('\n') };
    }

    private handleEvent(event: string, data: string): void {
        this.zone.run(() => {
            try {
                const payload = JSON.parse(data);
                if (event === 'agent_event' || event === 'message') {
                    this._events$.next(this.normalizeEvent(payload));
                    return;
                }
                this._events$.next(this.normalizeEvent({
                    ...payload,
                    event_type: payload?.event_type || event,
                }));
            } catch (error) {
                this.logger.error('[AgentEvents] Error parsing event', error);
            }
        });
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
