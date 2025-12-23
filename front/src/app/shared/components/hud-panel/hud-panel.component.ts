import { Component, Input, Output, EventEmitter, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { trigger, transition, style, animate } from '@angular/animations';

export interface HudSection {
    id: string;
    title: string;
    icon: string;
    collapsed: boolean;
    items: HudItem[];
}

export interface HudItem {
    label: string;
    value: string;
    status?: 'success' | 'warning' | 'error' | 'info';
    timestamp?: number;
}

export interface ThoughtEvent {
    type: 'thinking' | 'tool' | 'memory' | 'decision';
    content: string;
    timestamp: number;
    agent?: string;
}

@Component({
    selector: 'app-hud-panel',
    standalone: true,
    imports: [CommonModule],
    animations: [
        trigger('sectionContent', [
            transition(':enter', [
                style({ height: 0, opacity: 0 }),
                animate('200ms ease-out', style({ height: '*', opacity: 1 }))
            ]),
            transition(':leave', [
                animate('150ms ease-in', style({ height: 0, opacity: 0 }))
            ])
        ]),
        trigger('itemEnter', [
            transition(':enter', [
                style({ opacity: 0, transform: 'translateX(-10px)' }),
                animate('300ms ease-out', style({ opacity: 1, transform: 'translateX(0)' }))
            ])
        ])
    ],
    template: `
    <div class="hud-panel" [class.expanded]="expanded">
      <!-- Panel Header -->
      <div class="panel-header" (click)="toggleExpanded()">
        <div class="header-info">
          <span class="header-icon">🧠</span>
          <h3>{{ title }}</h3>
        </div>
        <div class="header-controls">
          <span class="status-dot" [class]="connectionStatus"></span>
          <button class="expand-btn" [class.rotated]="expanded">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M19 9l-7 7-7-7"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- Panel Content -->
      <div class="panel-content" *ngIf="expanded" @sectionContent>
        <!-- Quick Stats -->
        <div class="quick-stats">
          <div class="stat-item" *ngFor="let stat of quickStats">
            <span class="stat-icon">{{ stat.icon }}</span>
            <div class="stat-info">
              <span class="stat-value" [class]="stat.status">{{ stat.value }}</span>
              <span class="stat-label">{{ stat.label }}</span>
            </div>
          </div>
        </div>

        <!-- Collapsible Sections -->
        <div class="sections">
          <div class="section" *ngFor="let section of sections" [class.collapsed]="section.collapsed">
            <div class="section-header" (click)="toggleSection(section)">
              <div class="section-title">
                <span class="section-icon">{{ section.icon }}</span>
                <span>{{ section.title }}</span>
                <span class="item-count" *ngIf="section.items.length">{{ section.items.length }}</span>
              </div>
              <svg class="chevron" [class.rotated]="!section.collapsed" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 5l7 7-7 7"/>
              </svg>
            </div>
            
            <div class="section-content" *ngIf="!section.collapsed" @sectionContent>
              <div class="section-item" *ngFor="let item of section.items" @itemEnter>
                <span class="item-label">{{ item.label }}</span>
                <span class="item-value" [class]="item.status || 'info'">{{ item.value }}</span>
              </div>
              <div class="empty-section" *ngIf="section.items.length === 0">
                No data available
              </div>
            </div>
          </div>
        </div>

        <!-- Thought Stream -->
        <div class="thought-stream" *ngIf="showThoughtStream">
          <div class="stream-header">
            <span class="stream-icon">💭</span>
            <span>Thought Stream</span>
            <button class="clear-btn" (click)="clearThoughts.emit()" *ngIf="thoughts.length > 0">Clear</button>
          </div>
          <div class="stream-content" #streamContainer>
            <div class="thought-item" *ngFor="let thought of thoughts" @itemEnter [class]="thought.type">
              <div class="thought-header">
                <span class="thought-type">{{ getThoughtTypeLabel(thought.type) }}</span>
                <span class="thought-time">{{ formatTime(thought.timestamp) }}</span>
              </div>
              <div class="thought-content">{{ thought.content }}</div>
            </div>
            <div class="empty-stream" *ngIf="thoughts.length === 0">
              <div class="pulse-dot"></div>
              <span>Awaiting cognitive activity...</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
    styles: [`
    :host {
      --hud-bg: rgba(10, 15, 26, 0.95);
      --hud-surface: rgba(17, 24, 39, 0.8);
      --hud-border: rgba(0, 212, 255, 0.2);
      --text-primary: #e0f8ff;
      --text-secondary: #9ec8d6;
      --text-muted: #6b7280;
      --accent-cyan: #00d4ff;
      --accent-purple: #7c3aed;
      --accent-green: #10b981;
      --accent-yellow: #ffc107;
      --accent-red: #ef4444;
    }

    .hud-panel {
      background: var(--hud-bg);
      border: 1px solid var(--hud-border);
      border-radius: 12px;
      overflow: hidden;
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 0.85rem;
    }

    /* Header */
    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem 1rem;
      background: linear-gradient(90deg, rgba(0, 212, 255, 0.1), rgba(124, 58, 237, 0.1));
      cursor: pointer;
      transition: background 0.2s;

      &:hover {
        background: linear-gradient(90deg, rgba(0, 212, 255, 0.15), rgba(124, 58, 237, 0.15));
      }
    }

    .header-info {
      display: flex;
      align-items: center;
      gap: 8px;

      .header-icon { font-size: 1.1rem; }

      h3 {
        margin: 0;
        font-size: 0.9rem;
        font-weight: 600;
        color: var(--text-primary);
      }
    }

    .header-controls {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--text-muted);

      &.connected {
        background: var(--accent-green);
        box-shadow: 0 0 8px rgba(16, 185, 129, 0.6);
        animation: pulse 2s ease-in-out infinite;
      }

      &.disconnected {
        background: var(--accent-red);
      }

      &.connecting {
        background: var(--accent-yellow);
        animation: blink 1s linear infinite;
      }
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }

    @keyframes blink {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.3; }
    }

    .expand-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      width: 24px;
      height: 24px;
      cursor: pointer;
      transition: transform 0.2s;
      
      svg {
        width: 16px;
        height: 16px;
      }

      &.rotated {
        transform: rotate(180deg);
      }
    }

    /* Content */
    .panel-content {
      border-top: 1px solid var(--hud-border);
      max-height: 400px;
      overflow-y: auto;

      &::-webkit-scrollbar {
        width: 4px;
      }

      &::-webkit-scrollbar-thumb {
        background: rgba(0, 212, 255, 0.3);
        border-radius: 2px;
      }
    }

    /* Quick Stats */
    .quick-stats {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1px;
      background: var(--hud-border);
      border-bottom: 1px solid var(--hud-border);
    }

    .stat-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0.75rem;
      background: var(--hud-surface);

      .stat-icon { font-size: 1rem; }

      .stat-info {
        display: flex;
        flex-direction: column;

        .stat-value {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--text-primary);

          &.success { color: var(--accent-green); }
          &.warning { color: var(--accent-yellow); }
          &.error { color: var(--accent-red); }
        }

        .stat-label {
          font-size: 0.65rem;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
      }
    }

    /* Sections */
    .sections {
      padding: 0.5rem;
    }

    .section {
      margin-bottom: 0.5rem;
      border: 1px solid var(--hud-border);
      border-radius: 8px;
      overflow: hidden;

      &:last-child { margin-bottom: 0; }
    }

    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.5rem 0.75rem;
      background: var(--hud-surface);
      cursor: pointer;
      transition: background 0.2s;

      &:hover {
        background: rgba(0, 212, 255, 0.1);
      }
    }

    .section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--text-primary);
      font-size: 0.8rem;

      .section-icon { font-size: 0.9rem; }

      .item-count {
        background: var(--accent-cyan);
        color: var(--hud-bg);
        font-size: 0.65rem;
        padding: 1px 6px;
        border-radius: 10px;
        font-weight: 700;
      }
    }

    .chevron {
      width: 14px;
      height: 14px;
      color: var(--text-muted);
      transition: transform 0.2s;

      &.rotated { transform: rotate(90deg); }
    }

    .section-content {
      padding: 0.5rem;
      background: rgba(0, 0, 0, 0.2);
    }

    .section-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.35rem 0.5rem;
      border-radius: 4px;

      &:hover {
        background: rgba(0, 212, 255, 0.05);
      }

      .item-label {
        color: var(--text-secondary);
        font-size: 0.75rem;
      }

      .item-value {
        font-size: 0.75rem;
        font-weight: 600;

        &.success { color: var(--accent-green); }
        &.warning { color: var(--accent-yellow); }
        &.error { color: var(--accent-red); }
        &.info { color: var(--accent-cyan); }
      }
    }

    .empty-section {
      color: var(--text-muted);
      font-size: 0.75rem;
      text-align: center;
      padding: 0.5rem;
      font-style: italic;
    }

    /* Thought Stream */
    .thought-stream {
      border-top: 1px solid var(--hud-border);
    }

    .stream-header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0.5rem 0.75rem;
      background: rgba(124, 58, 237, 0.1);
      color: var(--text-primary);
      font-size: 0.8rem;

      .stream-icon { font-size: 0.9rem; }

      .clear-btn {
        margin-left: auto;
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: var(--text-muted);
        font-size: 0.65rem;
        padding: 2px 8px;
        border-radius: 4px;
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          border-color: var(--accent-red);
          color: var(--accent-red);
        }
      }
    }

    .stream-content {
      max-height: 200px;
      overflow-y: auto;
      padding: 0.5rem;

      &::-webkit-scrollbar { width: 3px; }
      &::-webkit-scrollbar-thumb { background: rgba(124, 58, 237, 0.3); }
    }

    .thought-item {
      padding: 0.5rem;
      margin-bottom: 0.5rem;
      border-left: 3px solid var(--accent-purple);
      background: rgba(124, 58, 237, 0.05);
      border-radius: 0 6px 6px 0;

      &.thinking { border-left-color: var(--accent-yellow); }
      &.tool { border-left-color: var(--accent-green); }
      &.memory { border-left-color: var(--accent-cyan); }
      &.decision { border-left-color: var(--accent-purple); }
    }

    .thought-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 4px;

      .thought-type {
        font-size: 0.65rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: var(--accent-purple);
      }

      .thought-time {
        font-size: 0.65rem;
        color: var(--text-muted);
      }
    }

    .thought-content {
      font-size: 0.75rem;
      color: var(--text-secondary);
      line-height: 1.4;
      word-break: break-word;
    }

    .empty-stream {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 1.5rem;
      color: var(--text-muted);
      font-size: 0.75rem;

      .pulse-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: var(--accent-purple);
        animation: pulse 2s ease-in-out infinite;
      }
    }
  `]
})
export class HudPanelComponent implements OnInit, OnDestroy {
    @Input() title: string = 'System HUD';
    @Input() expanded: boolean = true;
    @Input() connectionStatus: 'connected' | 'disconnected' | 'connecting' = 'connected';
    @Input() showThoughtStream: boolean = true;

    @Input() quickStats: { icon: string; label: string; value: string; status?: string }[] = [
        { icon: '🧠', label: 'Memory', value: 'Active', status: 'success' },
        { icon: '🔧', label: 'Tools', value: 'Ready', status: 'success' },
        { icon: '📡', label: 'Status', value: 'Online', status: 'success' }
    ];

    @Input() sections: HudSection[] = [
        { id: 'memory', title: 'Active Memory', icon: '💾', collapsed: true, items: [] },
        { id: 'tools', title: 'Available Tools', icon: '🔧', collapsed: true, items: [] },
        { id: 'context', title: 'Context', icon: '📋', collapsed: true, items: [] }
    ];

    @Input() thoughts: ThoughtEvent[] = [];

    @Output() clearThoughts = new EventEmitter<void>();
    @Output() sectionToggle = new EventEmitter<string>();

    ngOnInit() { }

    ngOnDestroy() { }

    toggleExpanded() {
        this.expanded = !this.expanded;
    }

    toggleSection(section: HudSection) {
        section.collapsed = !section.collapsed;
        this.sectionToggle.emit(section.id);
    }

    getThoughtTypeLabel(type: string): string {
        const labels: Record<string, string> = {
            'thinking': '💭 Thinking',
            'tool': '🔧 Tool Call',
            'memory': '💾 Memory Access',
            'decision': '⚡ Decision'
        };
        return labels[type] || type;
    }

    formatTime(timestamp: number): string {
        const date = new Date(timestamp);
        return date.toLocaleTimeString('pt-BR', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
}
