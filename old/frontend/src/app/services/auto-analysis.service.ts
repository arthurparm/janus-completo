import { Injectable } from '@angular/core'
import { HttpClient } from '@angular/common/http'
import { Observable } from 'rxjs'
import { AutoAnalysisResponse } from '../models'
import { API_BASE_URL } from './api.config'

@Injectable({ providedIn: 'root' })
export class AutoAnalysisService {
  constructor(private http: HttpClient) { }

  /**
   * Retorna somente conclusões sustentadas por custo, SLO e feedback persistido.
   */
  getHealthCheck(): Observable<AutoAnalysisResponse> {
    return this.http.get<AutoAnalysisResponse>(
      `${API_BASE_URL}/v1/auto-analysis/health-check`
    )
  }
}
