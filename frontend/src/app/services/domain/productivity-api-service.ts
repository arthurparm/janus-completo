import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiContextService } from '../api-context.service';
import { ProductivityLimitsStatusResponse, GoogleOAuthStartResponse, GoogleOAuthCallbackResponse, CalendarAddRequest, MailSendRequest, QueueAck } from '../../models';

@Injectable({ providedIn: 'root' })
export class ProductivityApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getProductivityLimitsStatus(user_id: number): Observable<ProductivityLimitsStatusResponse> {
    const headers = this.apiContext.headersFor(user_id)
    return this.http.get<ProductivityLimitsStatusResponse>(
      this.apiContext.buildUrl(`/api/v1/productivity/limits/status?user_id=${encodeURIComponent(String(user_id))}`),
      { headers }
    )
  }

getProductivityLimitsStatusSelf(): Observable<ProductivityLimitsStatusResponse> {
    return this.http.get<ProductivityLimitsStatusResponse>(
      this.apiContext.buildUrl(`/api/v1/productivity/limits/status`)
    )
  }

googleOAuthStart(user_id: number, scope: 'calendar' | 'mail' | 'notes' = 'calendar'): Observable<GoogleOAuthStartResponse> {
    const headers = this.apiContext.headersFor(user_id)
    const qs = new URLSearchParams({ user_id: String(user_id), scope })
    return this.http.get<GoogleOAuthStartResponse>(this.apiContext.buildUrl(`/api/v1/productivity/oauth/google/start?${qs.toString()}`), { headers })
  }

googleOAuthCallback(code: string, state: string): Observable<GoogleOAuthCallbackResponse> {
    return this.http.post<GoogleOAuthCallbackResponse>(this.apiContext.buildUrl(`/api/v1/productivity/oauth/google/callback`), { code, state })
  }

calendarAddEvent(req: CalendarAddRequest): Observable<QueueAck> {
    const headers = this.apiContext.headersFor(req.user_id)
    return this.http.post<QueueAck>(this.apiContext.buildUrl(`/api/v1/productivity/calendar/events/add`), req, { headers })
  }

mailSend(req: MailSendRequest): Observable<QueueAck> {
    const headers = this.apiContext.headersFor(req.user_id)
    return this.http.post<QueueAck>(this.apiContext.buildUrl(`/api/v1/productivity/mail/messages/send`), req, { headers })
  }
}
