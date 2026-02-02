import { Injectable } from '@angular/core'
import { BehaviorSubject, Observable } from 'rxjs'
import { HttpClient } from '@angular/common/http'
import { API_BASE_URL, UX_METRICS_SAMPLING } from './api.config'

export interface UxMetricItem { ttft_ms?: number; latency_ms?: number; outcome: 'success'|'error'|'cancel'; retries?: number; provider?: string; model?: string; timestamp: number }

@Injectable({ providedIn: 'root' })
export class UxMetricsService {
  private items$ = new BehaviorSubject<UxMetricItem[]>([])
  constructor(private http: HttpClient) {}

  metrics(): Observable<UxMetricItem[]> { return this.items$.asObservable() }

  record(item: UxMetricItem) {
    const arr = [item, ...this.items$.getValue()].slice(0, 500)
    this.items$.next(arr)
    if (Math.random() < UX_METRICS_SAMPLING) {
      const url = `${API_BASE_URL}/v1/observability/metrics/ux`
      this.http.post(url, item).subscribe({ next: () => {}, error: () => {} })
    }
  }

  p95Latency(): number | null {
    const xs = this.items$.getValue().map(i => i.latency_ms || 0).filter(x => x > 0).sort((a, b) => a - b)
    if (!xs.length) return null
    const idx = Math.floor(xs.length * 0.95) - 1
    return xs[Math.max(0, idx)]
  }
}
