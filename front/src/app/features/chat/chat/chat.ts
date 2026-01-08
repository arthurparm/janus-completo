import { Component, OnInit, OnDestroy, ViewChild, ElementRef, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { Subscription, forkJoin } from 'rxjs';
import { trigger, transition, style, animate } from '@angular/animations';

import { JanusApiService, ChatMessage, Tool, ToolListResponse } from '../../../services/janus-api.service';
import { AgentEventsService, AgentEvent } from '../../../core/services/agent-events.service';
import { SpeechRecognition, SpeechRecognitionEvent, SpeechRecognitionErrorEvent } from '../../../core/types';
import { marked } from 'marked';
import Prism from 'prismjs';
import { AuthService } from '../../../core/auth/auth.service';

// Import new components
import { JarvisAvatarComponent } from '../../../shared/components/jarvis-avatar/jarvis-avatar.component';
import { TypingIndicatorComponent } from '../../../shared/components/typing-indicator/typing-indicator.component';
import { VoiceOrbComponent } from '../../../shared/components/voice-orb/voice-orb.component';
import { HudPanelComponent, HudSection, HudItem, ThoughtEvent } from '../../../shared/components/hud-panel/hud-panel.component';

type VoiceState = 'idle' | 'listening' | 'processing' | 'speaking';
type AvatarState = 'idle' | 'thinking' | 'speaking' | 'listening';

@Component({
    selector: 'app-chat',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        MatProgressSpinnerModule,
        MatIconModule,
        JarvisAvatarComponent,
        TypingIndicatorComponent,
        VoiceOrbComponent,
        HudPanelComponent
    ],
    templateUrl: './chat.html',
    styleUrls: ['./chat.scss'],
    animations: [
        trigger('messageAnimation', [
            transition(':enter', [
                style({ opacity: 0, transform: 'translateY(20px)' }),
                animate('400ms cubic-bezier(0.4, 0, 0.2, 1)', style({ opacity: 1, transform: 'translateY(0)' }))
            ])
        ])
    ]
})
export class ChatComponent implements OnInit, OnDestroy {
    // Services
    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private api = inject(JanusApiService);
    private eventsService = inject(AgentEventsService);
    private auth = inject(AuthService);
    private cdr = inject(ChangeDetectorRef);

    // State
    conversationId: string | null = null;
    messages: ChatMessage[] = [];
    loading = false;
    sending = false;
    newMessage = '';
    title = '';

    // Voice State
    voiceState: VoiceState = 'idle';
    private recognition: SpeechRecognition | null = null;
    private speechSynthesis: SpeechSynthesis | null = null;

    // HUD connection status
    connectionStatus: 'connected' | 'disconnected' | 'connecting' = 'connecting';

    // HUD State
    hudVisible = true;
    agentEvents: ThoughtEvent[] = [];

    // Initial HUD Data
    quickStats = [
        { icon: '🧠', label: 'Memory', value: 'Syncing...', status: 'warning' },
        { icon: '🔧', label: 'Tools', value: 'Checking...', status: 'warning' },
        { icon: '📡', label: 'Status', value: 'Connecting...', status: 'warning' }
    ];

    hudSections: HudSection[] = [
        { id: 'memory', title: 'Active Memory', icon: '💾', collapsed: true, items: [] },
        { id: 'tools', title: 'Available Tools', icon: '🔧', collapsed: true, items: [] },
        { id: 'context', title: 'Context', icon: '📋', collapsed: false, items: [] }
    ];

    // Subs
    private subs: Subscription[] = [];

    // UI Refs
    @ViewChild('scrollContainer') private scrollContainer!: ElementRef;
    @ViewChild('hudScrollContainer') private hudScrollContainer!: ElementRef;

    ngOnInit() {
        // Initialize speech APIs
        this.initSpeechRecognition();
        this.speechSynthesis = window.speechSynthesis || null;

        this.route.paramMap.subscribe(params => {
            const cid = params.get('conversationId');
            if (cid && cid !== this.conversationId) {
                this.conversationId = cid;
                this.loadChat(cid);
                this.connectHud(cid);
                this.loadHudData();
            }
        });

        // Subscribe to HUD events
        this.subs.push(
            this.eventsService.events$.subscribe(evt => {
                const thought = this.mapEventToThought(evt);
                this.agentEvents = [...this.agentEvents, thought];
                this.scrollToBottomHud();
            })
        );
    }

    ngOnDestroy() {
        this.eventsService.disconnect();
        this.subs.forEach(s => s.unsubscribe());
        if (this.recognition) {
            this.recognition.abort();
        }
    }

    // =====================================
    // Avatar State Management
    // =====================================

    getAvatarState(): AvatarState {
        if (this.voiceState === 'listening') return 'listening';
        if (this.sending) return 'thinking';
        if (this.voiceState === 'speaking') return 'speaking';
        return 'idle';
    }

    // =====================================
    // Voice Interaction
    // =====================================

    private initSpeechRecognition() {
        const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition;

        if (SpeechRecognitionCtor) {
            this.recognition = new SpeechRecognitionCtor();
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'pt-BR'; // Portuguese by default

            this.recognition.onresult = (event: SpeechRecognitionEvent) => {
                const transcript = event.results[0][0].transcript;
                this.newMessage = transcript;
                this.voiceState = 'processing';
                this.cdr.detectChanges();

                // Auto-send after voice input
                setTimeout(() => {
                    this.sendMessage();
                    this.voiceState = 'idle';
                }, 500);
            };

            this.recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
                console.error('Speech recognition error:', event.error);
                this.voiceState = 'idle';
                this.cdr.detectChanges();
            };

            this.recognition.onend = () => {
                if (this.voiceState === 'listening') {
                    this.voiceState = 'idle';
                    this.cdr.detectChanges();
                }
            };
        }
    }

    onStartVoice() {
        if (this.recognition) {
            try {
                this.recognition.start();
                this.voiceState = 'listening';
            } catch (e) {
                console.error('Failed to start recognition:', e);
            }
        } else {
            console.warn('Speech recognition not supported');
        }
    }

    onStopVoice() {
        if (this.recognition) {
            this.recognition.stop();
            this.voiceState = 'idle';
        }
    }

    // Optional: Speak response (using browser TTS or Windows Agent)
    async speakResponse(text: string) {
        this.voiceState = 'speaking';

        // Try Windows Agent first (if available)
        try {
            const response = await fetch('http://localhost:5001/speak', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, rate: 150 })
            });

            if (response.ok) {
                // Windows Agent handled it
                setTimeout(() => {
                    this.voiceState = 'idle';
                    this.cdr.detectChanges();
                }, text.length * 50); // Rough estimate
                return;
            }
        } catch (e) {
            // Windows Agent not available, fall back to browser TTS
        }

        // Browser TTS fallback
        if (this.speechSynthesis) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = 'pt-BR';
            utterance.rate = 1;

            utterance.onend = () => {
                this.voiceState = 'idle';
                this.cdr.detectChanges();
            };

            this.speechSynthesis.speak(utterance);
        } else {
            this.voiceState = 'idle';
        }
    }

    // =====================================
    // Chat Logic
    // =====================================

    loadChat(cid: string) {
        this.loading = true;
        this.agentEvents = [];

        this.api.getChatHistory(cid).subscribe({
            next: (res) => {
                this.messages = res.messages;
                this.title = res.conversation_id;
                this.loading = false;
                this.cdr.detectChanges(); // Force view update
                setTimeout(() => this.scrollToBottom(), 100);
            },
            error: (err) => {
                console.error('Failed to load chat', err);
                this.loading = false;
                this.cdr.detectChanges(); // Update loading state
            }
        });
    }

    // Load static data for HUD
    loadHudData() {
        // 1. Get Tools
        this.api.getTools().subscribe({
            next: (res) => {
                const toolsSection = this.hudSections.find(s => s.id === 'tools');
                if (toolsSection) {
                    toolsSection.items = (res.tools || []).map(t => ({
                        label: t.name,
                        value: t.enabled ? 'Enabled' : 'Disabled',
                        status: t.enabled ? 'success' : 'error' as const
                    }));
                }

                // Update Quick Stat
                const toolStat = this.quickStats.find(s => s.label === 'Tools');
                if (toolStat) {
                    toolStat.value = `${(res.tools || []).filter(t => t.enabled).length} Ready`;
                    toolStat.status = 'success';
                }
                this.cdr.detectChanges();
            },
            error: () => {
                const toolStat = this.quickStats.find(s => s.label === 'Tools');
                if (toolStat) {
                    toolStat.value = 'Error';
                    toolStat.status = 'error';
                }
            }
        });

        // 2. Get System Status & Context (Parallel)
        forkJoin({
            status: this.api.getSystemStatus(),
            context: this.api.getCurrentContext(),
            memory: this.api.getMemoryTimeline({ limit: 5 })
        }).subscribe({
            next: ({ status, context, memory }) => {
                // Status Stat
                const statusStat = this.quickStats.find(s => s.label === 'Status');
                if (statusStat) {
                    statusStat.value = status.status === 'ok' ? 'Online' : 'Issues';
                    statusStat.status = status.status === 'ok' ? 'success' : 'warning';
                    this.connectionStatus = status.status === 'ok' ? 'connected' : 'disconnected';
                }

                // Memory Stat and Section
                const memStat = this.quickStats.find(s => s.label === 'Memory');
                if (memStat) {
                    memStat.value = 'Active';
                    memStat.status = 'success';
                }

                const memorySection = this.hudSections.find(s => s.id === 'memory');
                if (memorySection && memory && memory.length > 0) {
                    memorySection.items = memory.map(m => ({
                        label: 'Memory',
                        value: m.content.substring(0, 40) + (m.content.length > 40 ? '...' : ''),
                        status: 'info' as const,
                        timestamp: m.ts_ms
                    }));
                } else if (memorySection) {
                    memorySection.items = [];
                }


                // Context Section
                const contextSection = this.hudSections.find(s => s.id === 'context');
                if (contextSection) {
                    const items = [];
                    if (context['environment']) items.push({ label: 'Environment', value: String(context['environment']), status: 'info' as const });
                    if (context['system_info']) {
                        Object.entries(context['system_info']).forEach(([k, v]) => {
                            items.push({ label: k, value: String(v), status: 'info' as const });
                        });
                    }
                    if (context['datetime_info']) {
                        const dtInfo = context['datetime_info'] as Record<string, unknown>;
                        items.push({ label: 'Time', value: String(dtInfo['time'] || ''), status: 'info' as const });
                    }
                    contextSection.items = items.slice(0, 6) as HudItem[];
                }

                this.cdr.detectChanges();
            },
            error: (err) => {
                console.error('HUD Data Error', err);
                const statusStat = this.quickStats.find(s => s.label === 'Status');
                if (statusStat) {
                    statusStat.value = 'Offline';
                    statusStat.status = 'error';
                }
                this.connectionStatus = 'disconnected';
            }
        });
    }

    connectHud(cid: string) {
        this.eventsService.disconnect();
        this.eventsService.connect(cid);
    }

    sendMessage() {
        if (!this.newMessage.trim() || !this.conversationId) return;

        const content = this.newMessage;
        this.newMessage = '';
        this.sending = true;

        // Optimistic UI
        const tempMsg: ChatMessage = {
            role: 'user',
            text: content,
            timestamp: Date.now() / 1000 // Seconds
        };
        this.messages.push(tempMsg);
        this.cdr.detectChanges();
        this.scrollToBottom();

        const userId = this.auth.currentUserValue?.id;
        this.api.sendChatMessage(this.conversationId, content, 'orchestrator', 'fast_and_cheap', undefined, userId).subscribe({
            next: (res) => {
                if (res.response) {
                    const msg: ChatMessage = {
                        role: res.role || 'assistant',
                        text: res.response,
                        timestamp: Date.now() / 1000,
                        citations: res.citations
                    };
                    this.messages.push(msg);
                    this.cdr.detectChanges();

                    // Optional: speak the response
                    // this.speakResponse(res.response);
                }
                this.sending = false;
                this.cdr.detectChanges();
                this.scrollToBottom();
            },
            error: (err) => {
                console.error('Send error', err);
                this.sending = false;
                this.cdr.detectChanges();
            }
        });
    }

    onEnter(event: Event) {
        const kewhat = (event as KeyboardEvent);
        if (!kewhat.shiftKey) {
            event.preventDefault();
            this.sendMessage();
        }
    }

    toggleHud() {
        this.hudVisible = !this.hudVisible;
        setTimeout(() => {
            if (this.hudVisible) this.scrollToBottomHud();
        }, 50);
    }

    clearHud() {
        this.agentEvents = [];
    }

    scrollToBottom() {
        if (this.scrollContainer?.nativeElement) {
            this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
        }
    }

    scrollToBottomHud() {
        if (this.hudScrollContainer?.nativeElement) {
            this.hudScrollContainer.nativeElement.scrollTop = this.hudScrollContainer.nativeElement.scrollHeight;
        }
    }

    formatMessage(content: string): string {
        if (!content) return '';
        try {
            // Configure marked with prism for highlighting
            marked.setOptions({
                // highlight: (code, lang) => {
                //    if (Prism.languages[lang]) {
                //        return Prism.highlight(code, Prism.languages[lang], lang);
                //    }
                //    return code;
                // },
                breaks: true,
                gfm: true
            });

            return marked.parse(content) as string;
        } catch (e) {
            return this.simpleFormat(content);
        }
    }

    private simpleFormat(content: string): string {
        if (!content) return '';
        // Protect code blocks from processing
        const codeBlocks: string[] = [];
        let protectedContent = content.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
            codeBlocks.push(`<pre><code class="language-${lang}">${this.escapeHtml(code)}</code></pre>`);
            return `__CODEBLOCK_${codeBlocks.length - 1}__`;
        });

        // Basic markdown-like formatting
        let formatted = protectedContent
            .replace(/>/g, '&gt;')
            .replace(/\n/g, '<br>'); // ensure newlines are handled

        return formatted;
    }

    // Map AgentEvent to ThoughtEvent for HUD
    private mapEventToThought(evt: AgentEvent): ThoughtEvent {
        // Map types: 'thought' -> 'thinking', 'tool_call' -> 'tool', etc.
        const typeMap: Record<string, 'thinking' | 'tool' | 'memory' | 'decision'> = {
            'thought': 'thinking',
            'agent_thought': 'thinking',
            'tool_call': 'tool',
            'tool_start': 'tool',
            'tool_end': 'tool',
            'memory_access': 'memory',
            'memory_consolidated': 'memory', // New event type
            'decision': 'decision',
            'system': 'decision' // map generic system msgs too
        };

        return {
            type: typeMap[evt.event_type] || 'thinking',
            content: evt.content || '',
            timestamp: Date.now(),
            agent: evt.agent_role || 'Janus'
        };
    }

    private escapeHtml(text: string): string {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }
}
