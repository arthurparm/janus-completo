import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType } from '@angular/common/http';
import { Observable, BehaviorSubject, Subject } from 'rxjs';
import { map, tap } from 'rxjs/operators';
import { ApiContextService } from '../api-context.service';
import { Tool, ToolListResponse, ToolStats } from '../../models';

@Injectable({ providedIn: 'root' })
export class ToolsApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getTools(category?: string, permissionLevel?: string, tags?: string): Observable<ToolListResponse> {
    const qs = new URLSearchParams()
    if (category) qs.set('category', category)
    if (permissionLevel) qs.set('permission_level', permissionLevel)
    if (tags) qs.set('tags', tags)
    return this.http.get<ToolListResponse>(this.apiContext.buildUrl(`/api/v1/tools/${qs.toString() ? '?' + qs.toString() : ''}`))
  }

getToolDetails(toolName: string): Observable<Tool> {
    return this.http.get<Tool>(this.apiContext.buildUrl(`/api/v1/tools/${encodeURIComponent(toolName)}`))
  }

getToolStats(): Observable<ToolStats> {
    return this.http.get<ToolStats>(this.apiContext.buildUrl(`/api/v1/tools/stats/usage`))
  }

getToolCategories(): Observable<{ categories: string[] }> {
    return this.http.get<{ categories: string[] }>(this.apiContext.buildUrl(`/api/v1/tools/categories/list`))
  }

getToolPermissions(): Observable<{ permission_levels: string[] }> {
    return this.http.get<{ permission_levels: string[] }>(this.apiContext.buildUrl(`/api/v1/tools/permissions/list`))
  }
}
