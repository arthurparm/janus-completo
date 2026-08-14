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

getProductivityLimitsStatus(): Observable<ProductivityLimitsStatusResponse> {
    const headers = this.apiContext.headersFor()
    return this.http.get<ProductivityLimitsStatusResponse>(
      this.apiContext.buildUrl(`/api/v1/productivity/limits/status`),
      { headers }
    )
  }

getProductivityLimitsStatusSelf(): Observable<ProductivityLimitsStatusResponse> {
    return this.http.get<ProductivityLimitsStatusResponse>(
      this.apiContext.buildUrl(`/api/v1/productivity/limits/status`)
    )
  }

googleOAuthStart(scope: 'calendar' | 'mail' = 'calendar'): Observable<GoogleOAuthStartResponse> {
    const headers = this.apiContext.headersFor()
    const qs = new URLSearchParams({ scope })
    return this.http.get<GoogleOAuthStartResponse>(this.apiContext.buildUrl(`/api/v1/productivity/oauth/google/start?${qs.toString()}`), { headers })
  }

googleOAuthCallback(code: string, state: string): Observable<GoogleOAuthCallbackResponse> {
    return this.http.post<GoogleOAuthCallbackResponse>(this.apiContext.buildUrl(`/api/v1/productivity/oauth/google/callback`), { code, state })
  }

calendarAddEvent(req: CalendarAddRequest): Observable<QueueAck> {
    const headers = this.apiContext.headersFor()
    return this.http.post<QueueAck>(this.apiContext.buildUrl(`/api/v1/productivity/calendar/events/add`), req, { headers })
  }

mailSend(req: MailSendRequest): Observable<QueueAck> {
    const headers = this.apiContext.headersFor()
    return this.http.post<QueueAck>(this.apiContext.buildUrl(`/api/v1/productivity/mail/messages/send`), req, { headers })
  }
}
