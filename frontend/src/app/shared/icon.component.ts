import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ICONS, IconName } from './icons';

@Component({
  selector: 'app-icon',
  standalone: true,
  imports: [CommonModule],
  template: `
    <span 
      class="icon-container"
      [class.spinning]="spin"
      [class.pulse]="pulse"
      [attr.aria-hidden]="ariaHidden"
      [attr.aria-label]="ariaLabel"
      [innerHTML]="iconSvg"
    ></span>
  `,
  styles: [`
    :host {
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }
    
    .icon-container {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s ease-in-out;
    }
    
    .icon-container.spinning {
      animation: spin 1s linear infinite;
    }
    
    .icon-container.pulse {
      animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }
    
    .icon-container :host-context(.button:hover) {
      transform: scale(1.1);
    }
    
    .icon-container :host-context(.button:active) {
      transform: scale(0.95);
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class IconComponent {
  @Input() name!: IconName;
  @Input() size: 'xs' | 'sm' | 'md' | 'lg' | 'xl' = 'md';
  @Input() spin = false;
  @Input() pulse = false;
  @Input() ariaHidden = 'true';
  @Input() ariaLabel?: string;

  get iconSvg(): string {
    return ICONS[this.name] || '';
  }

  get iconClass(): string {
    const sizeMap = {
      xs: 'w-3 h-3',
      sm: 'w-4 h-4', 
      md: 'w-5 h-5',
      lg: 'w-6 h-6',
      xl: 'w-8 h-8'
    };
    return sizeMap[this.size];
  }
}