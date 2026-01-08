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
      --hud-bg: #0d1117; /* GitHub Dark Dimmed style background */
      --hud-surface: #161b22;
      --hud-border: #30363d;
      --text-primary: #c9d1d9;
      --text-secondary: #8b949e;
      --text-muted: #484f58;
      
      /* Professional Status Colors */
      --accent-cyan: #58a6ff;
      --accent-purple: #bc8cff;
      --accent-green: #3fb950;
      --accent-yellow: #d29922;
      --accent-red: #f85149;
    }

    .hud-panel {
      background: var(--hud-bg);
      border: 1px solid var(--hud-border);
      border-radius: 6px; /* Tighter radius for professional look */
      overflow: hidden;
      font-family: 'SF Mono', 'Segoe UI Mono', 'Roboto Mono', monospace; /* System mono fonts first */
      font-size: 13px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      display: flex;
      flex-direction: column;
    }

    /* Header */
    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 16px;
      background: var(--hud-surface);
      border-bottom: 1px solid var(--hud-border);
      cursor: pointer;
      user-select: none;
      
      &:hover {
        background: #1c2128;
      }
    }

    .header-info {
      display: flex;
      align-items: center;
      gap: 10px;

      .header-icon { 
        font-size: 14px; 
        opacity: 0.8;
      }

      h3 {
        margin: 0;
        font-size: 13px;
        font-weight: 600;
        color: var(--text-primary);
        letter-spacing: 0.5px;
        text-transform: uppercase;
      }
    }

    .header-controls {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .status-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--text-muted);

      &.connected {
        background: var(--accent-green);
        box-shadow: 0 0 4px rgba(63, 185, 80, 0.4);
      }
      &.disconnected { background: var(--accent-red); }
      &.connecting { background: var(--accent-yellow); }
    }

    .expand-btn {
      background: transparent;
      border: none;
      color: var(--text-secondary);
      width: 20px;
      height: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.2s;
      
      svg { width: 14px; height: 14px; }
      &.rotated { transform: rotate(180deg); }
    }

    /* Content */
    .panel-content {
      max-height: 600px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
    }

    /* Quick Stats */
    .quick-stats {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      border-bottom: 1px solid var(--hud-border);
      background: var(--hud-bg);
    }

    .stat-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      border-right: 1px solid var(--hud-border);

      &:last-child { border-right: none; }

      .stat-icon { font-size: 14px; opacity: 0.7; }

      .stat-info {
        display: flex;
        flex-direction: column;
        gap: 2px;

        .stat-value {
          font-size: 12px;
          font-weight: 600;
          color: var(--text-primary);
          
          &.success { color: var(--accent-green); }
          &.warning { color: var(--accent-yellow); }
          &.error { color: var(--accent-red); }
        }

        .stat-label {
          font-size: 10px;
          color: var(--text-secondary);
          text-transform: uppercase;
          font-weight: 500;
        }
      }
    }

    /* Sections */
    .sections {
      padding: 1px 0;
      background: var(--hud-border); /* separator color */
      display: flex;
      flex-direction: column;
      gap: 1px;
    }

    .section {
      background: var(--hud-bg);
    }

    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 8px 16px;
      cursor: pointer;
      user-select: none;

      &:hover {
        background: var(--hud-surface);
      }
    }

    .section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--text-secondary);
      font-size: 12px;
      font-weight: 500;

      .section-icon { font-size: 12px; }

      .item-count {
        background: var(--hud-border);
        color: var(--text-primary);
        font-size: 10px;
        padding: 0 6px;
        border-radius: 10px;
        min-width: 16px;
        text-align: center;
      }
    }

    .chevron {
      width: 12px;
      height: 12px;
      color: var(--text-muted);
      transition: transform 0.2s;
      &.rotated { transform: rotate(90deg); }
    }

    .section-content {
      padding: 8px 16px 12px;
      border-top: 1px solid var(--hud-border);
      background: rgba(13, 17, 23, 0.5);
    }

    .section-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 4px 0;
      font-size: 12px;
      border-bottom: 1px dashed rgba(48, 54, 61, 0.5);
      
      &:last-child { border-bottom: none; }

      .item-label { color: var(--text-secondary); }
      .item-value { color: var(--text-primary); font-family: monospace; }
    }

    .empty-section {
      color: var(--text-muted);
      font-size: 11px;
      padding: 4px 0;
      font-style: italic;
    }

    /* Thought Stream */
    .thought-stream {
      display: flex;
      flex-direction: column;
      flex: 1;
      height: 100%; /* Ensure it spans */
      min-height: 200px;
      background: #000000; /* Terminal black */
    }

    .stream-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 16px;
      background: var(--hud-surface);
      border-top: 1px solid var(--hud-border);
      border-bottom: 1px solid var(--hud-border);
      
      span {
        font-size: 11px;
        font-weight: 600;
        text-transform: uppercase;
        color: var(--text-muted);
        letter-spacing: 0.5px;
      }

      .clear-btn {
        background: none;
        border: none;
        color: var(--text-muted);
        font-size: 10px;
        cursor: pointer;
        padding: 2px 6px;
        border-radius: 4px;
        
        &:hover {
          background: rgba(248, 81, 73, 0.1);
          color: var(--accent-red);
        }
      }
    }

    .stream-content {
      flex: 1;
      overflow-y: auto;
      padding: 12px;
      font-family: 'Consolas', 'Monaco', monospace;
      
      &::-webkit-scrollbar { width: 6px; }
      &::-webkit-scrollbar-thumb { background: var(--hud-border); border-radius: 3px; }
      &::-webkit-scrollbar-track { background: transparent; }
    }

    .thought-item {
      margin-bottom: 8px;
      padding-left: 10px;
      border-left: 2px solid var(--text-muted);
      opacity: 0.9;
      
      &.thinking { border-left-color: var(--accent-yellow); color: #e3b341; }
      &.tool { border-left-color: var(--accent-green); color: #7ee787; }
      &.memory { border-left-color: var(--accent-cyan); color: #79c0ff; }
      &.decision { border-left-color: var(--accent-purple); color: #d2a8ff; }

      &:last-child {
         opacity: 1;
         animation: highlight 1s ease-out;
      }
    }

    @keyframes highlight {
      0% { background: rgba(255, 255, 255, 0.05); }
      100% { background: transparent; }
    }

    .thought-header {
      display: flex;
      gap: 8px;
      margin-bottom: 2px;
      align-items: baseline;
    }

    .thought-type {
      font-size: 10px;
      font-weight: bold;
      opacity: 0.8;
    }

    .thought-time {
      font-size: 10px;
      color: var(--text-muted);
    }

    .thought-content {
      font-size: 12px;
      line-height: 1.4;
      color: inherit;
      white-space: pre-wrap; /* Preserve code formatting */
    }

    .empty-stream {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100%;
      color: var(--text-muted);
      gap: 12px;

      .pulse-dot {
        width: 8px;
        height: 8px;
        background: var(--hud-border);
        border-radius: 50%;
        animation: pulse 3s infinite;
      }
      
      span { font-size: 11px; }
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
