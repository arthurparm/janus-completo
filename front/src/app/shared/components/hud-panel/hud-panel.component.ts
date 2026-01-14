import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { trigger, transition, style, animate } from '@angular/animations';
import { UiCardComponent, UiBadgeComponent, UiButtonDirective } from '../ui';

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
  imports: [CommonModule, UiCardComponent, UiBadgeComponent, UiButtonDirective],
  templateUrl: './hud-panel.component.html',
  styleUrls: ['./hud-panel.component.scss'],
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
        style({ opacity: 0, transform: 'translateX(-5px)' }),
        animate('200ms ease-out', style({ opacity: 1, transform: 'translateX(0)' }))
      ])
    ])
  ]
})
export class HudPanelComponent {
  @Input() title: string = 'System HUD';
  @Input() expanded: boolean = true;
  @Input() connectionStatus: 'connected' | 'disconnected' | 'connecting' = 'connected';
  @Input() showThoughtStream: boolean = true;
  @Input() quickStats: { icon: string; label: string; value: string; status?: string }[] = [];
  @Input() sections: HudSection[] = [];
  @Input() thoughts: ThoughtEvent[] = [];

  @Output() clearThoughts = new EventEmitter<void>();
  @Output() sectionToggle = new EventEmitter<string>();

  toggleExpanded() { this.expanded = !this.expanded; }

  toggleSection(section: HudSection) {
    section.collapsed = !section.collapsed;
    this.sectionToggle.emit(section.id);
  }

  getStatColor(status?: string): string {
    switch (status) {
      case 'success': return 'text-success';
      case 'warning': return 'text-warning';
      case 'error': return 'text-error'; // corrected from text-danger to standard utility if needed, but text-error exists in tokens usually
      default: return 'text-primary';
    }
  }

  getThoughtColorClass(type: string): string {
    return `thought-${type}`;
  }

  getThoughtTypeLabel(type: string): string {
    const labels: Record<string, string> = {
      'thinking': 'THINKING',
      'tool': 'TOOL',
      'memory': 'MEMORY',
      'decision': 'DECISION'
    };
    return labels[type] || type.toUpperCase();
  }

  formatTime(timestamp: number): string {
    return new Date(timestamp).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }
}
