import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiContextService } from '../api-context.service';
import { FeedbackQuickRequest, FeedbackQuickResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class FeedbackApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

thumbsUpFeedback(req: FeedbackQuickRequest): Observable<FeedbackQuickResponse> {
    return this.http.post<FeedbackQuickResponse>(
      this.apiContext.buildUrl(`/api/v1/feedback/thumbs-up`),
      {
        conversation_id: req.conversation_id,
        message_id: req.message_id,
        comment: req.comment,
      }
    )
  }

thumbsDownFeedback(req: FeedbackQuickRequest): Observable<FeedbackQuickResponse> {
    return this.http.post<FeedbackQuickResponse>(
      this.apiContext.buildUrl(`/api/v1/feedback/thumbs-down`),
      {
        conversation_id: req.conversation_id,
        message_id: req.message_id,
        comment: req.comment,
      }
    )
  }
}
