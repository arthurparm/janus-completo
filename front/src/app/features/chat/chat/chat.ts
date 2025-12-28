import { Component, OnInit, OnDestroy, ViewChild, ElementRef, inject, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';
import { Subscription } from 'rxjs';
import { trigger, transition, style, animate } from '@angular/animations';

import { JanusApiService, ChatMessage } from '../../../services/janus-api.service';
import { AgentEventsService, AgentEvent } from '../../../core/services/agent-events.service';
import { marked } from 'marked';
import Prism from 'prismjs';
import { AuthService } from '../../../core/auth/auth.service';

// Import new components
import { JarvisAvatarComponent } from '../../../shared/components/jarvis-avatar/jarvis-avatar.component';
import { TypingIndicatorComponent } from '../../../shared/components/typing-indicator/typing-indicator.component';
import { VoiceOrbComponent } from '../../../shared/components/voice-orb/voice-orb.component';
import { HudPanelComponent } from '../../../shared/components/hud-panel/hud-panel.component';

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
    private recognition: any = null;
    private speechSynthesis: SpeechSynthesis | null = null;

    // HUD State
    hudVisible = true;
    agentEvents: any[] = []; // storing mapped ThoughtEvents

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
        const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

        if (SpeechRecognition) {
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = false;
            this.recognition.lang = 'pt-BR'; // Portuguese by default

            this.recognition.onresult = (event: any) => {
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

            this.recognition.onerror = (event: any) => {
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
        const tempMsg: ChatMessage = { role: 'user', content: content, timestamp: new Date().toISOString() };
        this.messages.push(tempMsg);
        this.cdr.detectChanges();
        this.scrollToBottom();

        const userId = this.auth.currentUserValue?.id;
        this.api.sendChatMessage(this.conversationId, content, 'orchestrator', 'fast_and_cheap', undefined, userId).subscribe({
            next: (res) => {
                if (res.assistant_message) {
                    this.messages.push(res.assistant_message);
                    this.cdr.detectChanges();

                    // Optional: speak the response
                    // this.speakResponse(res.assistant_message.content);
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

            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            return (marked.parse(content) as any) as string;
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
    private mapEventToThought(evt: AgentEvent): any {
        // Map types: 'thought' -> 'thinking', 'tool_call' -> 'tool', etc.
        const typeMap: Record<string, string> = {
            'thought': 'thinking',
            'tool_call': 'tool',
            'memory_access': 'memory',
            'memory_consolidated': 'memory', // New event type
            'decision': 'decision'
        };

        return {
            type: typeMap[evt.type] || 'thinking',
            content: evt.content || '',
            timestamp: Date.now(),
            agent: 'Janus'
        };
    }

    private escapeHtml(text: string): string {
        return text
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    }
}
