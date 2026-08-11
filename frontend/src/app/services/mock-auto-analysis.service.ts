import { Injectable } from '@angular/core'
import { Observable, of } from 'rxjs'
import { delay } from 'rxjs/operators'
import { AutoAnalysisResponse } from '../models'

/**
 * Mock service para testar o componente de auto-análise sem depender do backend
 */
@Injectable()
export class MockAutoAnalysisService {
  private mockResponse: AutoAnalysisResponse = {
    timestamp: new Date().toISOString(),
    overall_health: 'healthy',
    insights: [
      {
        issue: 'Gastos com APIs: $12.50',
        severity: 'low',
        suggestion: 'Considere usar mais modelos locais (Ollama) para economizar',
        estimated_impact: 'Provedores ativos: 2',
        source: 'llm_cost_tracker',
        status: 'ok',
        evidence: {}
      },
      {
        issue: 'Performance de Respostas',
        severity: 'low',
        suggestion: 'Respostas estão rápidas! Continue assim',
        estimated_impact: 'Tempo médio de resposta: <2s ✅',
        source: 'observability_slo',
        status: 'ok',
        evidence: {}
      },
      {
        issue: 'Qualidade das Respostas',
        severity: 'low',
        suggestion: 'Considere alternar entre modelos para melhor variedade',
        estimated_impact: 'Satisfação do usuário: Boa 📈',
        source: 'feedback',
        status: 'ok',
        evidence: {}
      }
    ],
    summary: 'Resposta demonstrativa exclusiva para testes.',
    fun_fact: null
  }

  getHealthCheck(): Observable<AutoAnalysisResponse> {
    // Simula delay de rede
    return of(this.mockResponse).pipe(delay(1000))
  }
}
