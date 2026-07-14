import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { BackendApiService } from '../../../../services/backend-api.service';
import { PostSprintSummaryResponse } from '../../../../models';
import { Observable, of } from 'rxjs';
import { catchError, shareReplay } from 'rxjs/operators';

@Component({
  selector: 'app-learning-widget',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './learning-widget.html',
  styleUrls: ['./learning-widget.scss'],
})
export class LearningWidget {
  private api = inject(BackendApiService);
  private router = inject(Router);

  summary$: Observable<PostSprintSummaryResponse | null>;

  constructor() {
    this.summary$ = this.api.observability.getReflexionSummary(5).pipe(
      catchError(() => of(null)),
      shareReplay({ bufferSize: 1, refCount: true })
    );
  }

  hasLessons(summary: PostSprintSummaryResponse | null): boolean {
    return (summary?.lessons?.length ?? 0) > 0;
  }

  hasMetaReport(summary: PostSprintSummaryResponse | null): boolean {
    return Boolean(summary?.meta_report);
  }

  getMetaStatus(summary: PostSprintSummaryResponse | null): string {
    return summary?.meta_report?.overall_status || 'unknown';
  }

  getHealthScore(summary: PostSprintSummaryResponse | null): number | null {
    const score = Number(summary?.meta_report?.health_score);
    return Number.isFinite(score) ? score : null;
  }

  getMetaSummary(summary: PostSprintSummaryResponse | null): string {
    const report = summary?.meta_report;
    if (!report) return 'Sem relatório de reflexão disponível.';
    if (report.summary?.trim()) return report.summary.trim();
    const issueCount = report.issues_detected?.length ?? 0;
    const recommendationCount = report.recommendations?.length ?? 0;
    if (issueCount === 0 && recommendationCount === 0) {
      return 'Nenhuma falha detectada no ciclo mais recente.';
    }
    return `${issueCount} issue(s), ${recommendationCount} recomendação(ões).`;
  }

  openLearningInsights(): void {
    try {
      localStorage.setItem('janus.conversations.show_advanced_mode', '1');
      localStorage.setItem('janus.conversations.advanced_rail_tab', 'insights');
    } catch {
      // no-op
    }
    void this.router.navigate(['/conversations']);
  }
}
