import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiContextService } from '../api-context.service';
import { ExperimentWinnerResponse, AssignmentResponse, FeedbackSubmitResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class ExperimentApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getExperimentWinner(experiment_id: number, metric_name: string = 'accuracy'): Observable<ExperimentWinnerResponse> {
    const qs = new URLSearchParams({ metric_name })
    return this.http.get<ExperimentWinnerResponse>(this.apiContext.buildUrl(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/winner?${qs.toString()}`))
  }

assignUserToExperiment(experiment_id: number, _userId: string): Observable<AssignmentResponse> {
    return this.http.post<AssignmentResponse>(this.apiContext.buildUrl(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/assign`), {})
  }

submitExperimentFeedback(experiment_id: number, _userId: string, rating: number, notes?: string): Observable<FeedbackSubmitResponse> {
    return this.http.post<FeedbackSubmitResponse>(this.apiContext.buildUrl(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/feedback`), { rating, notes })
  }

getExperimentFeedbackStats(experiment_id: number): Observable<Record<string, unknown>> {
    return this.http.get<Record<string, unknown>>(this.apiContext.buildUrl(`/api/v1/evaluation/experiments/${encodeURIComponent(String(experiment_id))}/feedback/stats`))
  }
}
