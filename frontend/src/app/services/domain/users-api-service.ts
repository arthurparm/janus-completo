import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiContextService } from '../api-context.service';
import { UserRolesResponse, TokenResponse, UserStatusResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class UsersApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getUserRoles(user_id: number): Observable<UserRolesResponse> {
    return this.http.get<UserRolesResponse>(`/api/v1/users/${encodeURIComponent(String(user_id))}/roles`)
  }

issueToken(user_id: number, expires_in: number = 3600): Observable<TokenResponse> {
    const headers = this.apiContext.headersFor(user_id)
    return this.http.post<TokenResponse>(this.apiContext.buildUrl(`/api/v1/auth/token`), { user_id, expires_in }, { headers })
  }

getUserStatus(user_id: string): Observable<UserStatusResponse> {
    const qs = new URLSearchParams({ user_id })
    return this.http.get<UserStatusResponse>(this.apiContext.buildUrl(`/api/v1/system/status/user?${qs.toString()}`))
  }
}
