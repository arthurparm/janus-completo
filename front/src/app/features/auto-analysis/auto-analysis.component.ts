import { Component, OnInit } from '@angular/core'
import { CommonModule } from '@angular/common'
import { AutoAnalysisService, AutoAnalysisResponse, HealthInsight } from '../../services/auto-analysis.service'
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
  template: `
    <mat-card class="analysis-card">
      <mat-card-header>
        <mat-icon mat-card-avatar>psychology</mat-icon>
        <mat-card-title>Como estou me saindo?</mat-card-title>
        <mat-card-subtitle>Auto-análise do Janus</mat-card-subtitle>
      </mat-card-header>
      
      <mat-card-content>
        <div *ngIf="loading" class="loading-container">
          <mat-spinner diameter="40"></mat-spinner>
          <p>Analisando meu próprio sistema...</p>
        </div>

        <div *ngIf="!loading && analysis" class="analysis-content">
          <!-- Status Geral -->
          <div class="overall-status">
            <mat-icon [class.healthy]="analysis.overall_health === 'healthy'" 
                     [class.warning]="analysis.overall_health === 'warning'"
                     [class.critical]="analysis.overall_health === 'critical'">
              {{ getHealthIcon() }}
            </mat-icon>
            <span class="status-text">
              {{ getHealthText() }}
            </span>
          </div>

          <!-- Insights -->
          <div class="insights-section">
            <h3>Insights</h3>
            <div *ngFor="let insight of analysis.insights" class="insight-item">
              <mat-chip-listbox>
                <mat-chip [class.severity-low]="insight.severity === 'low'"
                         [class.severity-medium]="insight.severity === 'medium'"
                         [class.severity-high]="insight.severity === 'high'">
                  {{ insight.issue }}
                </mat-chip>
              </mat-chip-listbox>
              
              <div class="insight-details">
                <p class="suggestion">💡 {{ insight.suggestion }}</p>
                <p class="impact">📊 {{ insight.estimated_impact }}</p>
              </div>
            </div>
          </div>

          <!-- Fun Fact -->
          <div class="fun-fact" *ngIf="analysis.fun_fact">
            <mat-icon>mood</mat-icon>
            <span>{{ analysis.fun_fact }}</span>
          </div>
        </div>

        <div *ngIf="!loading && !analysis" class="error-container">
          <mat-icon>error_outline</mat-icon>
          <p>Não consegui me analisar desta vez. Tente novamente!</p>
        </div>
      </mat-card-content>
      
      <mat-card-actions>
        <button mat-button (click)="refreshAnalysis()">
          <mat-icon>refresh</mat-icon>
          Analisar novamente
        </button>
      </mat-card-actions>
    </mat-card>
  `,
  styles: [`
    .analysis-card {
      max-width: 600px;
      margin: 20px auto;
      background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }

    .loading-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 40px;
      gap: 20px;
    }

    .analysis-content {
      padding: 16px 0;
    }

    .overall-status {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 24px;
      padding: 16px;
      background: rgba(255, 255, 255, 0.7);
      border-radius: 12px;
    }

    .overall-status mat-icon {
      font-size: 32px;
      width: 32px;
      height: 32px;
    }

    .overall-status mat-icon.healthy {
      color: #4caf50;
    }

    .overall-status mat-icon.warning {
      color: #ff9800;
    }

    .overall-status mat-icon.critical {
      color: #f44336;
    }

    .status-text {
      font-size: 18px;
      font-weight: 500;
    }

    .insights-section h3 {
      margin-bottom: 16px;
      color: #333;
    }

    .insight-item {
      margin-bottom: 20px;
      padding: 16px;
      background: rgba(255, 255, 255, 0.8);
      border-radius: 8px;
      border-left: 4px solid #2196f3;
    }

    .insight-details {
      margin-top: 12px;
      padding-left: 8px;
    }

    .suggestion, .impact {
      margin: 8px 0;
      font-size: 14px;
      line-height: 1.5;
    }

    .suggestion {
      color: #1976d2;
      font-weight: 500;
    }

    .impact {
      color: #666;
    }

    .fun-fact {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-top: 24px;
      padding: 16px;
      background: rgba(255, 235, 59, 0.3);
      border-radius: 12px;
      font-style: italic;
    }

    .error-container {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 40px;
      gap: 16px;
      color: #f44336;
    }

    mat-chip {
      font-weight: 500;
    }

    .severity-low {
      background-color: #e8f5e8 !important;
      color: #2e7d32 !important;
    }

    .severity-medium {
      background-color: #fff3e0 !important;
      color: #ef6c00 !important;
    }

    .severity-high {
      background-color: #ffebee !important;
      color: #c62828 !important;
    }
  `]
})
export class AutoAnalysisComponent implements OnInit {
  analysis: AutoAnalysisResponse | null = null
  loading = true

  constructor(
    private autoAnalysisService: AutoAnalysisService,
    private mockService: MockAutoAnalysisService
  ) {}

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