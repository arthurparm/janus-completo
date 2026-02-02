import { Component, Input, ChangeDetectionStrategy } from '@angular/core'
import { CommonModule } from '@angular/common'

export type SkeletonVariant = 'text' | 'rect' | 'circle' | 'avatar' | 'button' | 'card' | 'paragraph'

export interface SkeletonConfig {
  variant: SkeletonVariant
  width?: string | number
  height?: string | number
  count?: number
  rounded?: boolean
  animated?: boolean
}

/**
 * Componente de skeleton para estados de carregamento
 * Uso: <app-skeleton variant="card" [count]="3" />
 */
@Component({
  selector: 'app-skeleton',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="skeleton-wrapper" [class.animated]="animated">
      @for (i of counter; track i) {
        <div
          class="skeleton"
          [class.skeleton-text]="variant === 'text'"
          [class.skeleton-rect]="variant === 'rect'"
          [class.skeleton-circle]="variant === 'circle'"
          [class.skeleton-avatar]="variant === 'avatar'"
          [class.skeleton-button]="variant === 'button'"
          [class.skeleton-card]="variant === 'card'"
          [class.skeleton-paragraph]="variant === 'paragraph'"
          [class.rounded]="rounded"
          [style.width]="getWidth()"
          [style.height]="getHeight()">
        </div>
      }
    </div>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    .skeleton-wrapper {
      display: block;
    }

    .skeleton {
      background: linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 37%, #f3f4f6 63%);
      background-size: 400% 100%;
      display: inline-block;
      vertical-align: middle;
      overflow: hidden;
      position: relative;
    }

    .skeleton.rounded {
      border-radius: 6px;
    }

    .animated .skeleton {
      animation: shimmer 1.4s ease infinite;
    }

    .skeleton-text {
      height: 1em;
      width: 100%;
      margin-bottom: 0.5em;
      border-radius: 4px;
    }

    .skeleton-rect {
      border-radius: 4px;
    }

    .skeleton-circle,
    .skeleton-avatar {
      border-radius: 50%;
      width: 40px;
      height: 40px;
    }

    .skeleton-avatar {
      width: 48px;
      height: 48px;
    }

    .skeleton-button {
      width: 64px;
      height: 36px;
      border-radius: 4px;
    }

    .skeleton-card {
      width: 100%;
      height: 120px;
      border-radius: 8px;
      margin-bottom: 12px;
    }

    .skeleton-paragraph {
      width: 100%;
      height: 12px;
      margin-bottom: 8px;
      border-radius: 4px;
    }

    .skeleton-paragraph:last-child {
      width: 80%;
    }

    @keyframes shimmer {
      0% {
        background-position: 100% 0;
      }
      100% {
        background-position: -100% 0;
      }
    }

    /* Tamanhos padrão por variante */
    .skeleton-text {
      width: 100%;
      max-width: 200px;
    }

    .skeleton-rect {
      width: 100%;
      max-width: 300px;
      height: 100px;
    }
  `]
})
export class SkeletonComponent {
  @Input() variant: SkeletonVariant = 'text'
  @Input() width?: string | number
  @Input() height?: string | number
  @Input() count = 1
  @Input() rounded = false
  @Input() animated = true

  get counter(): number[] {
    return Array(this.count).fill(0).map((_, i) => i)
  }

  getWidth(): string {
    if (this.width) {
      return typeof this.width === 'number' ? `${this.width}px` : this.width
    }
    return 'auto'
  }

  getHeight(): string {
    if (this.height) {
      return typeof this.height === 'number' ? `${this.height}px` : this.height
    }
    return 'auto'
  }
}
