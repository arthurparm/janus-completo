import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { FeedbackQuickRequest, FeedbackQuickResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class FeedbackApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

thumbsUpFeedback(req: FeedbackQuickRequest): Observable<FeedbackQuickResponse> {
    const qs = new URLSearchParams()
    if (req.user_id) qs.set('user_id', String(req.user_id))
    return this.http.post<FeedbackQuickResponse>(
      this.apiContext.buildUrl(`/api/v1/feedback/thumbs-up${qs.toString() ? '?' + qs.toString() : ''}`),
      {
        conversation_id: req.conversation_id,
        message_id: req.message_id,
        comment: req.comment,
      }
    )
  }

thumbsDownFeedback(req: FeedbackQuickRequest): Observable<FeedbackQuickResponse> {
    const qs = new URLSearchParams()
    if (req.user_id) qs.set('user_id', String(req.user_id))
    return this.http.post<FeedbackQuickResponse>(
      this.apiContext.buildUrl(`/api/v1/feedback/thumbs-down${qs.toString() ? '?' + qs.toString() : ''}`),
      {
        conversation_id: req.conversation_id,
        message_id: req.message_id,
        comment: req.comment,
      }
    )
  }
}
