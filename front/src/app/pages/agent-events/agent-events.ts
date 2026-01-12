import { Component, OnInit, OnDestroy, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatBadgeModule } from '@angular/material/badge';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, takeUntil } from 'rxjs';
import { AgentEventsService, AgentEvent } from '../../core/services/agent-events.service';

interface AgentEventDisplay extends AgentEvent {
    formattedTime: string;
    agentColor: string;
}

@Component({
    selector: 'app-agent-events',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        MatCardModule,
        MatButtonModule,
        MatIconModule,
        MatChipsModule,
        MatFormFieldModule,
        MatSelectModule,
        MatInputModule,
        MatBadgeModule,
        MatTooltipModule
    ],
    templateUrl: './agent-events.html',
    styleUrl: './agent-events.scss'
})
export class AgentEventsComponent implements OnInit, OnDestroy {
    private destroy$ = new Subject<void>();

    // State
    events = signal<AgentEventDisplay[]>([]);
    isConnected = signal(false);
    connectionStatus = signal<'disconnected' | 'connecting' | 'connected'>('disconnected');

    // Filters
    filterAgent = signal('');
    filterEventType = signal('');
    searchQuery = signal('');
    conversationId = signal('');

    // Computed
    filteredEvents = computed(() => {
        let result = this.events();

        const agent = this.filterAgent();
        if (agent) {
            result = result.filter(e => e.agent_role === agent);
        }

        const eventType = this.filterEventType();
        if (eventType) {
            result = result.filter(e => e.event_type === eventType);
        }

        const query = this.searchQuery().toLowerCase();
        if (query) {
            result = result.filter(e =>
                e.content.toLowerCase().includes(query) ||
                e.task_id.toLowerCase().includes(query)
            );
        }

        return result;
    });

    uniqueAgents = computed(() => {
        const agents = new Set(this.events().map(e => e.agent_role));
        return Array.from(agents).sort();
    });

    uniqueEventTypes = computed(() => {
        const types = new Set(this.events().map(e => e.event_type));
        return Array.from(types).sort();
    });

    eventCounts = computed(() => {
        const counts: Record<string, number> = {};
        this.events().forEach(e => {
            counts[e.agent_role] = (counts[e.agent_role] || 0) + 1;
        });
        return counts;
    });

    // Agent colors for visual distinction
    private agentColors: Record<string, string> = {
        'orchestrator': '#00d4ff',
        'coder': '#7c3aed',
        'professor': '#ec4899',
        'sandbox': '#00ff88',
        'router': '#ffb800',
        'planner': '#ff6b6b',
        'default': '#9ec8d6'
    };

    constructor(private agentEventsService: AgentEventsService) { }

    ngOnInit(): void {
        // Subscribe to events stream
        this.agentEventsService.events$
            .pipe(takeUntil(this.destroy$))
            .subscribe(event => {
                const displayEvent: AgentEventDisplay = {
                    ...event,
                    formattedTime: this.formatTimestamp(event.timestamp),
                    agentColor: this.getAgentColor(event.agent_role)
                };

                // Prepend new events (most recent first)
                this.events.update(events => [displayEvent, ...events].slice(0, 500)); // Keep max 500
            });
    }

    ngOnDestroy(): void {
        this.destroy$.next();
        this.destroy$.complete();
        this.disconnect();
    }

    connect(): void {
        const convId = this.conversationId();
        if (!convId) return;

        this.connectionStatus.set('connecting');
        this.agentEventsService.connect(convId);

        // Simulate connection success after brief delay
        setTimeout(() => {
            this.connectionStatus.set('connected');
            this.isConnected.set(true);
        }, 500);
    }

    disconnect(): void {
        this.agentEventsService.disconnect();
        this.connectionStatus.set('disconnected');
        this.isConnected.set(false);
    }

    clearEvents(): void {
        this.events.set([]);
    }

    clearFilters(): void {
        this.filterAgent.set('');
        this.filterEventType.set('');
        this.searchQuery.set('');
    }

    getAgentColor(role: string): string {
        return this.agentColors[role.toLowerCase()] || this.agentColors['default'];
    }

    getEventTypeIcon(eventType: string): string {
        const icons: Record<string, string> = {
            'start': 'play_arrow',
            'complete': 'check_circle',
            'error': 'error',
            'thinking': 'psychology',
            'tool_call': 'build',
            'tool_result': 'assignment_turned_in',
            'message': 'chat',
            'handoff': 'swap_horiz',
            'default': 'fiber_manual_record'
        };
        return icons[eventType.toLowerCase()] || icons['default'];
    }

    getEventTypeClass(eventType: string): string {
        const classes: Record<string, string> = {
            'start': 'event-start',
            'complete': 'event-complete',
            'error': 'event-error',
            'thinking': 'event-thinking',
            'tool_call': 'event-tool',
            'tool_result': 'event-tool-result',
            'handoff': 'event-handoff'
        };
        return classes[eventType.toLowerCase()] || 'event-default';
    }

    private formatTimestamp(ts: number): string {
        const date = new Date(ts * 1000);
        return date.toLocaleTimeString('pt-BR', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            fractionalSecondDigits: 3
        });
    }

    trackByEvent(_index: number, event: AgentEventDisplay): string {
        return `${event.task_id}-${event.timestamp}-${event.event_type}`;
    }
}
