import { Component, HostBinding, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

type AvatarState = 'idle' | 'thinking' | 'speaking' | 'listening';

@Component({
  selector: 'app-jarvis-avatar',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="janus-sigil" [ngClass]="state">
      <svg class="sigil" viewBox="0 0 120 120" role="img" aria-label="Janus">
        <defs>
          <linearGradient id="sigilHalo" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stop-color="var(--janus-secondary)" />
            <stop offset="100%" stop-color="var(--janus-primary)" />
          </linearGradient>
          <linearGradient id="sigilHex" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="var(--janus-accent)" />
            <stop offset="100%" stop-color="var(--janus-secondary)" />
          </linearGradient>
          <radialGradient id="sigilCore" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stop-color="#ffffff" />
            <stop offset="55%" stop-color="var(--janus-secondary)" />
            <stop offset="100%" stop-color="var(--janus-primary)" />
          </radialGradient>
        </defs>

        <circle class="halo" cx="60" cy="60" r="54"></circle>
        <g class="orbit">
          <circle class="node" cx="60" cy="10" r="2.2"></circle>
          <circle class="node" cx="110" cy="60" r="2.2"></circle>
          <circle class="node" cx="60" cy="110" r="2.2"></circle>
          <circle class="node" cx="10" cy="60" r="2.2"></circle>
        </g>
        <polygon
          class="hex"
          points="60,16 94,36 94,84 60,104 26,84 26,36"
        ></polygon>
        <circle class="core-glow" cx="60" cy="60" r="26"></circle>
        <circle class="core" cx="60" cy="60" r="16"></circle>
        <circle class="pulse" cx="60" cy="60" r="20"></circle>
      </svg>

      <span class="scan-line" aria-hidden="true"></span>
    </div>
  `,
  styles: [`
    :host {
      display: inline-flex;
      align-items: center;
      justify-content: center;
    }

    .janus-sigil {
      position: relative;
      width: var(--avatar-size, 48px);
      height: var(--avatar-size, 48px);
      display: grid;
      place-items: center;
    }

    .sigil {
      width: 100%;
      height: 100%;
      filter: drop-shadow(0 0 10px rgba(var(--janus-secondary-rgb), 0.35));
    }

    .halo {
      fill: none;
      stroke: url(#sigilHalo);
      stroke-width: 2;
      stroke-dasharray: 6 8;
      opacity: 0.65;
      transform-origin: 50% 50%;
      animation: sigilSpin 18s linear infinite;
    }

    .orbit {
      transform-origin: 50% 50%;
      transform-box: fill-box;
      animation: sigilSpinReverse 24s linear infinite;
    }

    .node {
      fill: var(--janus-secondary);
      opacity: 0.85;
      filter: drop-shadow(0 0 6px rgba(var(--janus-secondary-rgb), 0.6));
    }

    .hex {
      fill: none;
      stroke: url(#sigilHex);
      stroke-width: 2;
      opacity: 0.9;
    }

    .core-glow {
      fill: none;
      stroke: rgba(var(--janus-secondary-rgb), 0.5);
      stroke-width: 2;
      filter: drop-shadow(0 0 12px rgba(var(--janus-secondary-rgb), 0.6));
    }

    .core {
      fill: url(#sigilCore);
    }

    .pulse {
      fill: none;
      stroke: rgba(var(--janus-primary-rgb), 0.45);
      stroke-width: 1.5;
      transform-origin: 50% 50%;
      animation: sigilPulse 2.6s ease-in-out infinite;
    }

    .scan-line {
      position: absolute;
      width: 120%;
      height: 2px;
      background: linear-gradient(90deg, transparent, rgba(var(--janus-secondary-rgb), 0.7), transparent);
      animation: scanSweep 3.8s ease-in-out infinite;
      opacity: 0.7;
    }

    @keyframes sigilSpin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }

    @keyframes sigilSpinReverse {
      from { transform: rotate(360deg); }
      to { transform: rotate(0deg); }
    }

    @keyframes sigilPulse {
      0%, 100% { transform: scale(0.92); opacity: 0.4; }
      50% { transform: scale(1.08); opacity: 0.8; }
    }

    @keyframes scanSweep {
      0%, 100% { transform: translateY(-45%); opacity: 0; }
      45% { opacity: 0.6; }
      50% { transform: translateY(45%); opacity: 0.9; }
      55% { opacity: 0.6; }
    }

    /* State: Thinking */
    .janus-sigil.thinking .halo {
      animation-duration: 8s;
      stroke: var(--janus-accent);
      opacity: 0.85;
    }

    .janus-sigil.thinking .pulse {
      stroke: rgba(var(--janus-accent-rgb), 0.6);
    }

    /* State: Speaking */
    .janus-sigil.speaking .halo {
      stroke: var(--success);
      opacity: 0.9;
    }

    .janus-sigil.speaking .pulse {
      stroke: rgba(var(--success-rgb), 0.6);
      animation-duration: 1.6s;
    }

    /* State: Listening */
    .janus-sigil.listening .halo {
      stroke: var(--error);
      opacity: 0.9;
    }

    .janus-sigil.listening .scan-line {
      background: linear-gradient(90deg, transparent, rgba(var(--error-rgb), 0.8), transparent);
    }
  `]
})
export class JarvisAvatarComponent {
  @Input() state: AvatarState = 'idle';
  @Input() size: number = 48;

  @HostBinding('style.--avatar-size.px')
  get avatarSize(): number {
    return this.size;
  }
}
