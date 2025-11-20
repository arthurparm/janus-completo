import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map, catchError } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface TailscaleConfig {
  enabled: boolean;
  host?: string;
  backendUrl?: string;
  frontendUrl?: string;
}

export interface SystemHealth {
  status: string;
  service: string;
  version: string;
  environment: string;
  tailscale?: TailscaleConfig;
}

@Injectable({
  providedIn: 'root'
})
export class TailscaleService {
  private tailscaleConfig: TailscaleConfig | null = null;
  private apiUrl: string;

  constructor(private http: HttpClient) {
    this.apiUrl = this.getApiUrl();
  }

  /**
   * Get the appropriate API URL based on Tailscale configuration
   */
  private getApiUrl(): string {
    // Check if Tailscale is enabled and configured
    if (environment.tailscale?.enabled && environment.tailscale?.apiUrl) {
      return environment.tailscale.apiUrl;
    }
    
    // Fall back to default API URL
    return environment.apiUrl;
  }

  /**
   * Check if Tailscale Serve is enabled and configured
   */
  isTailscaleEnabled(): boolean {
    return environment.tailscale?.enabled || false;
  }

  /**
   * Get current Tailscale configuration
   */
  getTailscaleConfig(): Observable<TailscaleConfig> {
    if (this.tailscaleConfig) {
      return of(this.tailscaleConfig);
    }

    // Try to get Tailscale config from backend health endpoint
    return this.http.get<SystemHealth>(`${this.apiUrl}/health`).pipe(
      map(health => {
        this.tailscaleConfig = health.tailscale || {
          enabled: false
        };
        return this.tailscaleConfig;
      }),
      catchError(() => {
        // If health endpoint fails, return local config
        this.tailscaleConfig = {
          enabled: this.isTailscaleEnabled(),
          backendUrl: environment.tailscale?.apiUrl,
          frontendUrl: environment.tailscale?.frontendUrl
        };
        return of(this.tailscaleConfig);
      })
    );
  }

  /**
   * Get system health including Tailscale status
   */
  getSystemHealth(): Observable<SystemHealth> {
    return this.http.get<SystemHealth>(`${this.apiUrl}/health`);
  }

  /**
   * Test connectivity to backend via Tailscale
   */
  testBackendConnectivity(): Observable<boolean> {
    return this.http.get<SystemHealth>(`${this.apiUrl}/health`).pipe(
      map(() => true),
      catchError(() => of(false))
    );
  }

  /**
   * Get Tailscale status information
   */
  getTailscaleStatus(): Observable<any> {
    return this.http.get(`${this.apiUrl}/system/status`).pipe(
      catchError(error => {
        console.warn('Failed to get system status:', error);
        return of(null);
      })
    );
  }

  /**
   * Update API URL dynamically (useful for switching between local and Tailscale)
   */
  updateApiUrl(url: string): void {
    this.apiUrl = url;
  }

  /**
   * Get the current API URL
   */
  getCurrentApiUrl(): string {
    return this.apiUrl;
  }

  /**
   * Check if we're currently using Tailscale URLs
   */
  isUsingTailscaleUrls(): boolean {
    return this.isTailscaleEnabled() && 
           this.apiUrl.includes('.ts.net');
  }
}