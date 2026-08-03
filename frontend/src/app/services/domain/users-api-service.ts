import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ApiContextService } from '../api-context.service';
import { UserRolesResponse, UserStatusResponse } from '../../models';

@Injectable({ providedIn: 'root' })
export class UsersApiService {
  constructor(
    private http: HttpClient,
    private apiContext: ApiContextService
  ) {}

getUserRoles(targetActorId: number): Observable<UserRolesResponse> {
    return this.http.get<UserRolesResponse>(`/api/v1/users/${encodeURIComponent(String(targetActorId))}/roles`)
  }

getUserStatus(_userId: string): Observable<UserStatusResponse> {
    return this.http.get<UserStatusResponse>(this.apiContext.buildUrl(`/api/v1/system/status/user`))
  }
}
