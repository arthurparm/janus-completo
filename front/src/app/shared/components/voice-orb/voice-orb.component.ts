import { Component, Input, Output, EventEmitter, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';

type OrbState = 'idle' | 'listening' | 'processing' | 'speaking';

@Component({
  selector: 'app-voice-orb',
  standalone: true,
  imports: [CommonModule],
  template: `
    <button 
      class="voice-orb" 
      [class]="state"
      [disabled]="disabled"
      (click)="handleClick()"
      [attr.aria-label]="getAriaLabel()"
    >
      <!-- Background glow -->
      <div class="orb-glow"></div>
      
      <!-- Outer rings -->
      <div class="orb-ring ring-1"></div>
      <div class="orb-ring ring-2"></div>
      <div class="orb-ring ring-3"></div>
      
      <!-- Listening audio waves -->
      <div class="audio-waves" *ngIf="state === 'listening'">
        <div class="wave" *ngFor="let w of [1,2,3,4,5,6,7,8]" [style.--i]="w"></div>
      </div>
      
      <!-- Core with icon -->
      <div class="orb-core">
        <!-- Idle: Microphone icon -->
        <svg *ngIf="state === 'idle'" class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="23"/>
          <line x1="8" y1="23" x2="16" y2="23"/>
        </svg>
        
        <!-- Listening: Animated mic -->
        <svg *ngIf="state === 'listening'" class="icon listening-icon" viewBox="0 0 24 24" fill="currentColor">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
          <line x1="12" y1="19" x2="12" y2="23" stroke="currentColor" stroke-width="2"/>
          <line x1="8" y1="23" x2="16" y2="23" stroke="currentColor" stroke-width="2"/>
        </svg>
        
        <!-- Processing: Spinner -->
        <div *ngIf="state === 'processing'" class="processing-spinner">
          <div class="spinner-ring"></div>
        </div>
        
        <!-- Speaking: Sound waves icon -->
        <svg *ngIf="state === 'speaking'" class="icon speaking-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
          <path d="M19.07 4.93a10 10 0 0 1 0 14.14" class="wave-line wave-1"/>
          <path d="M15.54 8.46a5 5 0 0 1 0 7.07" class="wave-line wave-2"/>
        </svg>
      </div>
      
      <!-- State label -->
      <span class="orb-label" *ngIf="showLabel">
        {{ getStateLabel() }}
      </span>
    </button>
  `,
  styles: [`
    :host {
      display: inline-block;
    }

    .voice-orb {
      position: relative;
      width: var(--orb-size, 56px);
      height: var(--orb-size, 56px);
      border: none;
      border-radius: 50%;
      background: linear-gradient(135deg, rgba(10, 15, 26, 0.8), rgba(20, 30, 50, 0.8));
      backdrop-filter: blur(5px);
      box-shadow: 
        inset 0 0 10px rgba(0, 212, 255, 0.2),
        0 4px 15px rgba(0, 0, 0, 0.3);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
      outline: none;
      z-index: 10;

      &:hover:not(:disabled) {
        transform: scale(1.05);
        background: linear-gradient(135deg, rgba(20, 30, 50, 0.9), rgba(30, 40, 70, 0.9));
        box-shadow: 
          inset 0 0 15px rgba(0, 212, 255, 0.3),
          0 0 20px rgba(0, 212, 255, 0.2);
        
        .orb-glow { opacity: 0.6; }
        .icon { color: #00d4ff; }
      }

      &:active:not(:disabled) {
        transform: scale(0.98);
      }

      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
        filter: grayscale(1);
      }

      &:focus-visible {
        box-shadow: 0 0 0 3px rgba(0, 212, 255, 0.5);
      }
    }

    /* Glow behind */
    .orb-glow {
      position: absolute;
      inset: -8px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(0, 212, 255, 0.4) 0%, transparent 70%);
      opacity: 0.5;
      transition: opacity 0.3s;
      pointer-events: none;
    }

    /* Rings */
    .orb-ring {
      position: absolute;
      border-radius: 50%;
      border: 1px solid rgba(0, 212, 255, 0.3);
      pointer-events: none;
    }

    .ring-1 {
      inset: -4px;
      animation: ringPulse 3s ease-in-out infinite;
    }

    .ring-2 {
      inset: -8px;
      animation: ringPulse 3s ease-in-out infinite 0.5s;
      border-color: rgba(124, 58, 237, 0.3);
    }

    .ring-3 {
      inset: -12px;
      animation: ringPulse 3s ease-in-out infinite 1s;
      border-color: rgba(236, 72, 153, 0.2);
    }

    @keyframes ringPulse {
      0%, 100% { transform: scale(1); opacity: 0.3; }
      50% { transform: scale(1.1); opacity: 0.6; }
    }

    /* Core */
    .orb-core {
      position: relative;
      width: 60%;
      height: 60%;
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1;
    }

    .icon {
      width: 24px;
      height: 24px;
      color: #00d4ff;
      transition: all 0.3s;
    }

    /* Listening state */
    .voice-orb.listening {
      background: linear-gradient(135deg, #7c2d12, #dc2626);
      animation: listeningPulse 0.8s ease-in-out infinite;

      .orb-glow {
        background: radial-gradient(circle, rgba(239, 68, 68, 0.5) 0%, transparent 70%);
        opacity: 1;
      }

      .orb-ring {
        border-color: rgba(239, 68, 68, 0.4);
        animation: ringExpand 1s ease-out infinite;
      }

      .ring-2 { animation-delay: 0.2s; }
      .ring-3 { animation-delay: 0.4s; }
    }

    @keyframes listeningPulse {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.03); }
    }

    @keyframes ringExpand {
      0% { transform: scale(1); opacity: 0.6; }
      100% { transform: scale(1.5); opacity: 0; }
    }

    .listening-icon {
      color: #fef2f2;
      animation: micPulse 0.5s ease-in-out infinite;
    }

    @keyframes micPulse {
      0%, 100% { transform: scale(1); }
      50% { transform: scale(1.1); }
    }

    /* Audio waves during listening */
    .audio-waves {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 3px;
    }

    .audio-waves .wave {
      width: 3px;
      height: 20px;
      background: linear-gradient(180deg, #fef2f2, #ef4444);
      border-radius: 2px;
      animation: waveHeight 0.6s ease-in-out infinite;
      animation-delay: calc(var(--i) * 0.1s);
    }

    @keyframes waveHeight {
      0%, 100% { transform: scaleY(0.3); }
      50% { transform: scaleY(1); }
    }

    /* Processing state */
    .voice-orb.processing {
      background: linear-gradient(135deg, #1e3a5f, #3b82f6);

      .orb-glow {
        background: radial-gradient(circle, rgba(59, 130, 246, 0.5) 0%, transparent 70%);
      }
    }

    .processing-spinner {
      width: 28px;
      height: 28px;
      position: relative;
    }

    .spinner-ring {
      width: 100%;
      height: 100%;
      border: 3px solid rgba(255, 255, 255, 0.2);
      border-top-color: #00d4ff;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }

    @keyframes spin {
      to { transform: rotate(360deg); }
    }

    /* Speaking state */
    .voice-orb.speaking {
      background: linear-gradient(135deg, #064e3b, #10b981);

      .orb-glow {
        background: radial-gradient(circle, rgba(16, 185, 129, 0.5) 0%, transparent 70%);
      }

      .icon { color: #ecfdf5; }
    }

    .speaking-icon .wave-line {
      animation: speakingWave 1s ease-in-out infinite;
    }

    .wave-1 { animation-delay: 0s; }
    .wave-2 { animation-delay: 0.15s; }

    @keyframes speakingWave {
      0%, 100% { opacity: 0.3; transform: translateX(-2px); }
      50% { opacity: 1; transform: translateX(0); }
    }

    /* Label */
    .orb-label {
      position: absolute;
      bottom: -24px;
      left: 50%;
      transform: translateX(-50%);
      font-size: 0.7rem;
      color: #a5b4fc;
      white-space: nowrap;
      text-transform: uppercase;
      letter-spacing: 1px;
    }
  `]
})
export class VoiceOrbComponent implements OnDestroy {
  @Input() state: OrbState = 'idle';
  @Input() disabled: boolean = false;
  @Input() showLabel: boolean = false;

  @Output() startListening = new EventEmitter<void>();
  @Output() stopListening = new EventEmitter<void>();
  @Output() cancelSpeaking = new EventEmitter<void>();

  handleClick() {
    switch (this.state) {
      case 'idle':
        this.startListening.emit();
        break;
      case 'listening':
        this.stopListening.emit();
        break;
      case 'speaking':
        this.cancelSpeaking.emit();
        break;
    }
  }

  getStateLabel(): string {
    switch (this.state) {
      case 'idle': return 'Voice';
      case 'listening': return 'Listening...';
      case 'processing': return 'Processing';
      case 'speaking': return 'Speaking';
      default: return '';
    }
  }

  getAriaLabel(): string {
    switch (this.state) {
      case 'idle': return 'Click to start voice input';
      case 'listening': return 'Listening, click to stop';
      case 'processing': return 'Processing voice input';
      case 'speaking': return 'Speaking, click to stop';
      default: return 'Voice input';
    }
  }

  ngOnDestroy() {
    // Cleanup if needed
  }
}
