import { Component, Input, Output, EventEmitter, ChangeDetectionStrategy, inject } from '@angular/core'
import { CommonModule } from '@angular/common'
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner'
import { LoadingStateService } from '../../../core/services/loading-state.service'

/**
 * Componente de loading reutilizável para todo o sistema
 * Uso: <app-loading [isLoading]="true" [message]="Carregando..." />
 */
@Component({
  selector: 'app-loading',
  standalone: true,
  imports: [CommonModule, MatProgressSpinnerModule],
  template: `
    <div *ngIf="actualLoading" class="loading-container" [class.overlay]="overlay">
      <div class="loading-content">
        <mat-spinner 
          *ngIf="showSpinner"
          [diameter]="diameter" 
          [color]="color"
          [mode]="mode">
        </mat-spinner>
        <p *ngIf="showMessage && actualMessage" class="loading-message">{{ actualMessage }}</p>
        <p *ngIf="subMessage" class="loading-submessage">{{ subMessage }}</p>
      </div>
    </div>
    <ng-content *ngIf="!actualLoading"></ng-content>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    .loading-container {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 2rem;
      min-height: 200px;
    }

    .loading-container.overlay {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: rgba(255, 255, 255, 0.9);
      z-index: 1000;
      padding: 0;
    }

    .loading-content {
      text-align: center;
    }

    .loading-message {
      margin: 1rem 0 0.5rem 0;
      font-size: 1.1rem;
      font-weight: 500;
      color: #333;
    }

    .loading-submessage {
      margin: 0;
      font-size: 0.9rem;
      color: #666;
    }

    /* Animação suave de entrada/saída */
    :host {
      display: block;
      transition: opacity 0.3s ease;
    }
  `]
})
export class LoadingComponent {
  private readonly loadingStateService = inject(LoadingStateService)
  
  @Input() isLoading = false
  @Input() message = ''
  @Input() subMessage = ''
  @Input() diameter = 40
  @Input() color: 'primary' | 'accent' | 'warn' = 'primary'
  @Input() mode: 'determinate' | 'indeterminate' = 'indeterminate'
  @Input() overlay = false
  @Input() loadingKey?: string
  @Input() showSpinner = true
  @Input() showMessage = true

  get actualLoading(): boolean {
    if (this.loadingKey) {
      return this.loadingStateService.isKeyLoading(this.loadingKey)
    }
    return this.isLoading
  }

  get actualMessage(): string {
    if (this.loadingKey) {
      const state = this.loadingStateService.getLoadingState(this.loadingKey)
      return state?.message || this.message
    }
    return this.message
  }
}