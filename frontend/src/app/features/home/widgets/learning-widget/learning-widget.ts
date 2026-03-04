import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { BackendApiService, PostSprintSummaryResponse } from '../../../../services/backend-api.service';
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
    this.summary$ = this.api.getReflexionSummary(5).pipe(
      catchError(() => of(null)),
      shareReplay({ bufferSize: 1, refCount: true })
    );
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
