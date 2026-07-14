import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core'
import { CommonModule } from '@angular/common'
import { RouterLink } from '@angular/router'
import { forkJoin, of } from 'rxjs'
import { catchError } from 'rxjs/operators'
import { takeUntilDestroyed } from '@angular/core/rxjs-interop'

import { Header } from '../../core/layout/header/header'
import { BackendApiService } from '../../services/backend-api.service'
import { KnowledgeStats } from '../../models'

type GraphTypeMetric = {
  type: string
  count: number
}

@Component({
  selector: 'app-knowledge-graph',
  standalone: true,
  imports: [CommonModule, RouterLink, Header],
  templateUrl: './knowledge-graph.html',
  styleUrls: ['./knowledge-graph.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class KnowledgeGraphComponent {
  private api = inject(BackendApiService)
  private destroyRef = inject(DestroyRef)

  readonly loading = signal(true)
  readonly error = signal('')
  readonly stats = signal<KnowledgeStats | null>(null)
  readonly nodeTypes = signal<string[]>([])

  constructor() {
    this.loadGraphSummary()
  }

  loadGraphSummary(): void {
    this.loading.set(true)
    this.error.set('')

    forkJoin({
      stats: this.api.knowledge.getKnowledgeStats().pipe(catchError(() => of(null))),
      nodeTypes: this.api.knowledge.getKnowledgeNodeTypes().pipe(catchError(() => of({ types: [] }))),
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(({ stats, nodeTypes }) => {
        this.stats.set(stats)
        this.nodeTypes.set(nodeTypes.types || [])
        this.loading.set(false)
        if (!stats) {
          this.error.set('Nao foi possivel carregar o grafo de conhecimento.')
        }
      })
  }

  nodeTypeMetrics(): GraphTypeMetric[] {
    const stats = this.stats()
    if (stats?.node_types?.length) {
      return stats.node_types.slice().sort((a, b) => b.count - a.count)
    }
    return this.nodeTypes().map((type) => ({ type, count: 0 }))
  }

  relationshipTypeMetrics(): GraphTypeMetric[] {
    return (this.stats()?.relationship_types || []).slice().sort((a, b) => b.count - a.count)
  }
}
