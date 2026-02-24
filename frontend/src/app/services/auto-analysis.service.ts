import { Injectable } from '@angular/core'
import { HttpClient } from '@angular/common/http'
import { Observable } from 'rxjs'
import { API_BASE_URL } from './api.config'

export interface HealthInsight {
  issue: string
  severity: 'low' | 'medium' | 'high'
  suggestion: string
  estimated_impact: string
}

export interface AutoAnalysisResponse {
  timestamp: string
  overall_health: 'healthy' | 'warning' | 'critical' | 'unknown'
  insights: HealthInsight[]
  fun_fact: string
  total_memories?: number
  session_duration?: string
  efficiency_score?: number
}

@Injectable({ providedIn: 'root' })
export class AutoAnalysisService {
  constructor(private http: HttpClient) { }

  /**
   * Pergunta ao Janus: "Como você está se saindo?"
   * Retorna uma análise simples e útil sobre o próprio sistema.
   */
  getHealthCheck(): Observable<AutoAnalysisResponse> {
    return this.http.get<AutoAnalysisResponse>(
      `${API_BASE_URL}/v1/auto-analysis/health-check`
    )
  }
}