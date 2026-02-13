import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { JanusApiService, PostSprintSummaryResponse, ReflexionLesson } from '../../../../services/janus-api.service';
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
  private api = inject(JanusApiService);

  summary$: Observable<PostSprintSummaryResponse | null>;

  constructor() {
    this.summary$ = this.api.getReflexionSummary(5).pipe(
      catchError(() => of(null)),
      shareReplay({ bufferSize: 1, refCount: true })
    );
  }
}
