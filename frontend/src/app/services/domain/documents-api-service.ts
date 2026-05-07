import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { AppLoggerService } from '../../core/services/app-logger.service';
import { UploadResponse, DocListResponse, DocSearchResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class DocumentsApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService,
    private logger: AppLoggerService
  ) {}

linkUrl(conversation_id: string, url: string, user_id?: string): Observable<UploadResponse> {
    const form = new FormData()
    form.append('url', url)
    form.append('conversation_id', conversation_id)
    if (user_id) form.append('user_id', user_id)
    return this.http.post<UploadResponse>(this.apiContext.buildUrl(`/api/v1/documents/link-url`), form)
  }

listDocuments(conversationId?: string, userId?: string): Observable<DocListResponse> {
    const qs = new URLSearchParams();
    if (conversationId) qs.set('conversation_id', conversationId);
    if (userId) qs.set('user_id', userId);
    const headers = this.apiContext.headersFor(userId);
    return this.http.get<DocListResponse>(this.apiContext.buildUrl(`/api/v1/documents/list${qs.toString() ? '?' + qs.toString() : ''}`), { headers });
  }

uploadDocument(file: File, conversationId?: string, userId?: string): Observable<{ progress?: number; response?: UploadResponse }> {
    const form = new FormData();
    form.append('file', file);
    if (conversationId) form.append('conversation_id', conversationId);
    if (userId) form.append('user_id', userId);

    const headers = this.apiContext.headersFor(userId);
    this.logger.debug('[BackendApiService] uploadDocument params', { userId, userHeader: headers['X-User-Id'] });
    return this.http.post<UploadResponse>(this.apiContext.buildUrl(`/api/v1/documents/upload`), form, { headers, reportProgress: true, observe: 'events' }).pipe(
      map((event: HttpEvent<UploadResponse>) => {
        if (event.type === HttpEventType.UploadProgress) {
          const pct = Math.round((event.loaded / Math.max(1, event.total || 1)) * 100)
          return { progress: pct }
        } else if (event.type === HttpEventType.Response) {
          return { response: event.body || undefined }
        }
        return {}
      })
    )
  }

searchDocuments(query: string, minScore?: number, docId?: string, userId?: string): Observable<DocSearchResponse> {
    const qs = new URLSearchParams()
    qs.set('query', query)
    if (minScore !== undefined) qs.set('min_score', String(minScore))
    if (docId) qs.set('doc_id', docId)
    if (userId) qs.set('user_id', String(userId))
    const headers = userId ? this.apiContext.headersFor(userId) : undefined
    return this.http.get<DocSearchResponse>(
      this.apiContext.buildUrl(`/api/v1/documents/search?${qs.toString()}`),
      headers ? { headers } : undefined
    )
  }

deleteDocument(docId: string, userId?: string): Observable<{ status: string; doc_id: string }> {
    const qs = new URLSearchParams()
    if (userId) qs.set('user_id', String(userId))
    const headers = userId ? this.apiContext.headersFor(userId) : undefined
    return this.http.delete<{ status: string; doc_id: string }>(
      this.apiContext.buildUrl(`/api/v1/documents/${encodeURIComponent(docId)}${qs.toString() ? '?' + qs.toString() : ''}`),
      headers ? { headers } : undefined
    )
  }
}
