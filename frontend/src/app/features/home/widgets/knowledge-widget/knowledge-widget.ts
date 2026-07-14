import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { BackendApiService } from '../../../../services/backend-api.service';
import { KnowledgeStats } from '../../../../models';
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
  private api = inject(BackendApiService);
  private router = inject(Router);

  stats$: Observable<KnowledgeStats | null>;

  constructor() {
    this.stats$ = this.api.knowledge.getKnowledgeStats().pipe(
      catchError(() => of(null)),
      shareReplay({ bufferSize: 1, refCount: true })
    );
  }

  getTopLabels(stats: KnowledgeStats): { label: string; count: number }[] {
    if (stats?.labels && Object.keys(stats.labels).length > 0) {
      return Object.entries(stats.labels)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 4)
      .map(([label, count]) => ({ label, count }));
    }

    return (stats?.node_types || [])
      .slice()
      .sort((a, b) => b.count - a.count)
      .slice(0, 4)
      .map((item) => ({ label: item.type, count: item.count }));
  }

  openKnowledgeView(): void {
    void this.router.navigate(['/knowledge-graph']);
  }
}
