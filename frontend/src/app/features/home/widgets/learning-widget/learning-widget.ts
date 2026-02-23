import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
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

  summary$: Observable<PostSprintSummaryResponse | null>;

  constructor() {
    this.summary$ = this.api.getReflexionSummary(5).pipe(
      catchError(() => of(null)),
      shareReplay({ bufferSize: 1, refCount: true })
    );
  }
}
