import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { JanusApiService, KnowledgeStats } from '../../../../services/janus-api.service';
import { Observable, of } from 'rxjs';
import { catchError, shareReplay } from 'rxjs/operators';

@Component({
  selector: 'app-knowledge-widget',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './knowledge-widget.html',
  styleUrls: ['./knowledge-widget.scss'],
})
export class KnowledgeWidget {
  private api = inject(JanusApiService);

  stats$: Observable<KnowledgeStats | null>;

  constructor() {
    this.stats$ = this.api.getKnowledgeStats().pipe(
      catchError(() => of(null)),
      shareReplay({ bufferSize: 1, refCount: true })
    );
  }

  getTopLabels(stats: KnowledgeStats): { label: string; count: number }[] {
    if (!stats?.labels) return [];
    return Object.entries(stats.labels)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 4)
      .map(([label, count]) => ({ label, count }));
  }
}
