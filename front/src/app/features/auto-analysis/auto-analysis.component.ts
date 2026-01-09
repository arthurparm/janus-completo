import { Component, OnInit } from '@angular/core'
import { CommonModule } from '@angular/common'
import { AutoAnalysisService, AutoAnalysisResponse } from '../../services/auto-analysis.service'
import { MockAutoAnalysisService } from '../../services/mock-auto-analysis.service'
import { MatCardModule } from '@angular/material/card'
import { MatIconModule } from '@angular/material/icon'
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner'
import { MatChipsModule } from '@angular/material/chips'

@Component({
  selector: 'app-auto-analysis',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatChipsModule
  ],
  templateUrl: './auto-analysis.html',
  styleUrl: './auto-analysis.scss'
})
export class AutoAnalysisComponent implements OnInit {
  analysis: AutoAnalysisResponse | null = null
  loading = true

  constructor(
    private autoAnalysisService: AutoAnalysisService,
    private mockService: MockAutoAnalysisService
  ) { }

  ngOnInit() {
    this.loadAnalysis()
  }

  loadAnalysis() {
    this.loading = true

    // Tenta usar o serviço real primeiro
    this.autoAnalysisService.getHealthCheck().subscribe({
      next: (response) => {
        this.analysis = response
        this.loading = false
      },
      error: (error) => {
        console.warn('Serviço real indisponível, usando mock:', error)
        // Fallback para mock
        this.mockService.getHealthCheck().subscribe({
          next: (response) => {
            this.analysis = response
            this.loading = false
          },
          error: (mockError) => {
            console.error('Erro ao carregar análise:', mockError)
            this.loading = false
            this.analysis = null
          }
        })
      }
    })
  }

  refreshAnalysis() {
    this.loadAnalysis()
  }

  getHealthIcon(): string {
    if (!this.analysis) return 'help_outline'

    switch (this.analysis.overall_health) {
      case 'healthy': return 'check_circle'
      case 'warning': return 'warning'
      case 'critical': return 'error'
      default: return 'help_outline'
    }
  }

  getHealthText(): string {
    if (!this.analysis) return 'Status desconhecido'

    switch (this.analysis.overall_health) {
      case 'healthy': return 'Estou ótimo! 💪'
      case 'warning': return 'Tem alguma coisinha... 🤔'
      case 'critical': return 'Preciso de atenção! 🚨'
      default: return 'Não consegui me avaliar'
    }
  }
}