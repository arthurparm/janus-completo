import { Injectable } from '@angular/core'
import { Observable, of } from 'rxjs'
import { delay } from 'rxjs/operators'
import { AutoAnalysisResponse } from './auto-analysis.service'

/**
 * Mock service para testar o componente de auto-análise sem depender do backend
 */
@Injectable({ providedIn: 'root' })
export class MockAutoAnalysisService {
  private mockResponse: AutoAnalysisResponse = {
    timestamp: new Date().toISOString(),
    overall_health: 'healthy',
    insights: [
      {
        issue: 'Gastos com APIs: $12.50',
        severity: 'low',
        suggestion: 'Considere usar mais modelos locais (Ollama) para economizar',
        estimated_impact: 'Provedores ativos: 2'
      },
      {
        issue: 'Performance de Respostas',
        severity: 'low',
        suggestion: 'Respostas estão rápidas! Continue assim',
        estimated_impact: 'Tempo médio de resposta: <2s ✅'
      },
      {
        issue: 'Qualidade das Respostas',
        severity: 'low',
        suggestion: 'Considere alternar entre modelos para melhor variedade',
        estimated_impact: 'Satisfação do usuário: Boa 📈'
      }
    ],
    fun_fact: 'Você sabia? Já processei mais de 1000 perguntas! 🤯'
  }

  getHealthCheck(): Observable<AutoAnalysisResponse> {
    // Simula delay de rede
    return of(this.mockResponse).pipe(delay(1000))
  }
}