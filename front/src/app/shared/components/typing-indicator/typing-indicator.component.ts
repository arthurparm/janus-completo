import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-typing-indicator',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="typing-indicator" [class.compact]="compact">
      <div class="typing-content">
        <!-- Audio wave visualization -->
        <div class="wave-container">
          <svg class="waves" viewBox="0 0 100 40" preserveAspectRatio="none">
            <!-- Sine Wave 1 (Cyan) -->
            <path class="sine-wave wave-1" d="M0 20 Q 25 5 50 20 T 100 20 V 40 H 0 Z" fill="rgba(0, 212, 255, 0.4)" />
            <!-- Sine Wave 2 (Purple) -->
            <path class="sine-wave wave-2" d="M0 20 Q 25 35 50 20 T 100 20 V 40 H 0 Z" fill="rgba(124, 58, 237, 0.4)" />
            <!-- Sine Wave 3 (Pink - Stroke only for holographic feel) -->
            <path class="sine-wave wave-3" d="M0 20 Q 25 15 50 20 T 100 20" fill="none" stroke="rgba(236, 72, 153, 0.8)" stroke-width="2" />
          </svg>
        </div>
        
        <!-- Label -->
        <span class="typing-label" *ngIf="showLabel">
          {{ label }}
          <span class="dots">
            <span>.</span><span>.</span><span>.</span>
          </span>
        </span>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }

    .typing-indicator {
      display: inline-flex;
      align-items: center;
      padding: 10px 20px;
      background: rgba(10, 15, 26, 0.6);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(0, 212, 255, 0.2);
      border-radius: 20px;
      box-shadow: 
        0 4px 20px rgba(0, 0, 0, 0.2),
        inset 0 0 20px rgba(0, 212, 255, 0.05);
      
      &.compact {
        padding: 6px 12px;
        .wave-container { width: 40px; height: 20px; }
        .typing-label { font-size: 0.75rem; }
      }
    }

    .typing-content {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .wave-container {
      width: 100px;
      height: 30px;
      overflow: hidden;
      position: relative;
    }

    .waves {
      width: 200%; /* Double width for seamless scroll */
      height: 100%;
      animation: waveScroll 4s linear infinite;
    }

    .sine-wave {
      vector-effect: non-scaling-stroke;
    }

    .wave-1 { animation: waveFloat 3s ease-in-out infinite alternate; }
    .wave-2 { animation: waveFloat 4s ease-in-out infinite alternate-reverse; }
    .wave-3 { 
      stroke-dasharray: 10 5;
      animation: waveFloat 2s ease-in-out infinite alternate; 
    }

    @keyframes waveScroll {
      0% { transform: translateX(0); }
      100% { transform: translateX(-50%); }
    }

    @keyframes waveFloat {
      0% { transform: scaleY(0.8) translateY(2px); }
      100% { transform: scaleY(1.2) translateY(-2px); }
    }

    .typing-label {
      color: #a5b4fc;
      font-size: 0.85rem;
      font-weight: 500;
      letter-spacing: 0.5px;
      text-transform: uppercase;
    }

    .dots {
      display: inline-flex;
      margin-left: 2px;
      
      span {
        animation: dotFade 1.4s ease-in-out infinite;
        
        &:nth-child(2) { animation-delay: 0.2s; }
        &:nth-child(3) { animation-delay: 0.4s; }
      }
    }

    @keyframes dotFade {
      0%, 80%, 100% { opacity: 0.2; }
      40% { opacity: 1; }
    }
  `]
})
export class TypingIndicatorComponent {
  @Input() label: string = 'Janus is thinking';
  @Input() showLabel: boolean = true;
  @Input() compact: boolean = false;
}
