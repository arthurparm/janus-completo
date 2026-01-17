import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

type AvatarState = 'idle' | 'thinking' | 'speaking' | 'listening';

@Component({
  selector: 'app-jarvis-avatar',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="jarvis-avatar" [class]="state">
      <!-- Outer glow ring -->
      <div class="glow-ring"></div>
      
      <!-- Rotating outer ring -->
      <svg class="ring ring-outer" viewBox="0 0 100 100">
        <circle 
          cx="50" cy="50" r="46" 
          fill="none" 
          stroke="url(#gradientOuter)" 
          stroke-width="1.5"
          stroke-dasharray="8 4"
        />
        <defs>
          <linearGradient id="gradientOuter" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:var(--janus-secondary)"/>
            <stop offset="100%" style="stop-color:var(--janus-primary)"/>
          </linearGradient>
        </defs>
      </svg>
      
      <!-- Counter-rotating middle ring -->
      <svg class="ring ring-middle" viewBox="0 0 100 100">
        <circle 
          cx="50" cy="50" r="38" 
          fill="none" 
          stroke="url(#gradientMiddle)" 
          stroke-width="2"
          stroke-dasharray="12 6"
        />
        <defs>
          <linearGradient id="gradientMiddle" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:var(--janus-primary)"/>
            <stop offset="100%" style="stop-color:var(--janus-accent)"/>
          </linearGradient>
        </defs>
      </svg>
      
      <!-- Inner ring -->
      <svg class="ring ring-inner" viewBox="0 0 100 100">
        <circle 
          cx="50" cy="50" r="30" 
          fill="none" 
          stroke="url(#gradientInner)" 
          stroke-width="1"
          stroke-dasharray="4 8"
        />
        <defs>
          <linearGradient id="gradientInner" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:var(--janus-secondary)"/>
            <stop offset="100%" style="stop-color:var(--success)"/>
          </linearGradient>
        </defs>
      </svg>
      
      <!-- Core orb -->
      <div class="core">
        <div class="core-inner"></div>
        <div class="core-pulse"></div>
      </div>
      
      <!-- Speaking waves -->
      <div class="speaking-waves" *ngIf="state === 'speaking'">
        <div class="wave wave-1"></div>
        <div class="wave wave-2"></div>
        <div class="wave wave-3"></div>
      </div>
      
      <!-- Thinking dots -->
      <div class="thinking-dots" *ngIf="state === 'thinking'">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .jarvis-avatar {
      position: relative;
      width: var(--avatar-size, 48px);
      height: var(--avatar-size, 48px);
      display: flex;
      align-items: center;
      justify-content: center;
    }

    /* Glow effect */
    .glow-ring {
      position: absolute;
      inset: -8px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(var(--janus-secondary-rgb), 0.4) 0%, transparent 70%);
      animation: glowPulse 4s ease-in-out infinite;
      filter: blur(4px);
    }

    @keyframes glowPulse {
      0%, 100% { opacity: 0.3; transform: scale(0.95); }
      50% { opacity: 0.8; transform: scale(1.1); }
    }

    /* Rings */
    .ring {
      position: absolute;
      width: 100%;
      height: 100%;
      filter: drop-shadow(0 0 4px rgba(var(--janus-secondary-rgb), 0.5));
    }

    .ring-outer {
      animation: rotateClockwise 20s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }

    .ring-middle {
      animation: rotateCounterClockwise 15s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }

    .ring-inner {
      animation: rotateClockwise 10s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }

    @keyframes rotateClockwise {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }

    @keyframes rotateCounterClockwise {
      from { transform: rotate(360deg); }
      to { transform: rotate(0deg); }
    }

    /* Core */
    .core {
      position: relative;
      width: 42%;
      height: 42%;
      border-radius: 50%;
      background: linear-gradient(135deg, var(--janus-primary), var(--janus-secondary));
      box-shadow: 
        0 0 20px rgba(var(--janus-primary-rgb), 0.8),
        inset 0 0 10px rgba(255, 255, 255, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 10;
    }

    .core-inner {
      width: 60%;
      height: 60%;
      border-radius: 50%;
      background: radial-gradient(circle, #ffffff 0%, var(--janus-secondary) 100%);
      animation: corePulse 3s cubic-bezier(0.4, 0, 0.2, 1) infinite;
      box-shadow: 0 0 15px rgba(255, 255, 255, 0.8);
    }

    .core-pulse {
      position: absolute;
      inset: 0;
      border-radius: 50%;
      background: inherit;
      animation: coreExpand 2.5s cubic-bezier(0, 0, 0.2, 1) infinite;
    }

    @keyframes corePulse {
      0%, 100% { transform: scale(0.9); opacity: 0.8; }
      50% { transform: scale(1.05); opacity: 1; }
    }

    @keyframes coreExpand {
      0% { transform: scale(1); opacity: 0.6; }
      100% { transform: scale(2.2); opacity: 0; }
    }

    /* State: Thinking */
    .jarvis-avatar.thinking {
      .ring-outer { animation-duration: 4s; stroke: var(--janus-accent); }
      .ring-middle { animation-ration: 3s; }
      .ring-inner { animation-duration: 2s; }
      .glow-ring { background: radial-gradient(circle, rgba(var(--janus-accent-rgb), 0.4) 0%, transparent 70%); }
      .core { 
        background: linear-gradient(135deg, var(--janus-accent), var(--janus-secondary));
        box-shadow: 0 0 25px rgba(var(--janus-accent-rgb), 0.6);
      }
    }

    .thinking-dots {
      position: absolute;
      bottom: -12px;
      display: flex;
      gap: 5px;
      
      span {
        width: 5px;
        height: 5px;
        border-radius: 50%;
        background: var(--janus-primary);
        box-shadow: 0 0 5px var(--janus-primary);
        animation: thinkingBounce 1.4s ease-in-out infinite;
        
        &:nth-child(2) { animation-delay: 0.2s; }
        &:nth-child(3) { animation-delay: 0.4s; }
      }
    }

    @keyframes thinkingBounce {
      0%, 80%, 100% { transform: translateY(0); opacity: 0.5; }
      40% { transform: translateY(-4px); opacity: 1; }
    }

    /* State: Speaking */
    .jarvis-avatar.speaking {
      .glow-ring { background: radial-gradient(circle, rgba(var(--success-rgb), 0.5) 0%, transparent 70%); }
      .core { 
        background: linear-gradient(135deg, var(--success), var(--janus-secondary));
        box-shadow: 0 0 30px rgba(var(--success-rgb), 0.6);
      }
    }

    /* State: Listening */
    .jarvis-avatar.listening {
      .glow-ring { 
        background: radial-gradient(circle, rgba(var(--error-rgb), 0.5) 0%, transparent 70%);
        animation: glowPulse 0.8s ease-in-out infinite;
      }
      .core { 
        background: linear-gradient(135deg, var(--error), var(--janus-accent));
        animation: listeningPulse 0.5s ease-in-out infinite;
      }
    }

    @keyframes listeningPulse {
      0%, 100% { transform: scale(1); box-shadow: 0 0 20px rgba(var(--error-rgb), 0.5); }
      50% { transform: scale(1.15); box-shadow: 0 0 40px rgba(var(--error-rgb), 0.8); }
    }
  `]
})
export class JarvisAvatarComponent {
  @Input() state: AvatarState = 'idle';
  @Input() size: number = 48;
}
