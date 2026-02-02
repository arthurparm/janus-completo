import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly apiUrl = this.getApiUrl();

  private getApiUrl(): string {
    // Use Tailscale URL if enabled, otherwise use default
    if (environment.tailscale?.enabled && environment.tailscale?.apiUrl) {
      return environment.tailscale.apiUrl;
    }
    return environment.apiUrl;
  }

  private buildUrl(endpoint: string): string {
    // Remove leading slash if present
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
    return `${this.apiUrl}/${cleanEndpoint}`;
  }

  get<T>(url: string, options?: object): Observable<T> {
    return this.http.get<T>(this.buildUrl(url), options);
  }

  post<T>(url: string, body: unknown, options?: object): Observable<T> {
    return this.http.post<T>(this.buildUrl(url), body, options);
  }

  put<T>(url: string, body: unknown, options?: object): Observable<T> {
    return this.http.put<T>(this.buildUrl(url), body, options);
  }

  delete<T>(url: string, options?: object): Observable<T> {
    return this.http.delete<T>(this.buildUrl(url), options);
  }

  // Exemplo: healthcheck do backend
  health(): Observable<string> {
    return this.http.get(this.buildUrl('/healthz'), { responseType: 'text' });
  }

  // Health check detalhado com informações do sistema
  detailedHealth(): Observable<any> {
    return this.http.get(this.buildUrl('/health'));
  }
}
