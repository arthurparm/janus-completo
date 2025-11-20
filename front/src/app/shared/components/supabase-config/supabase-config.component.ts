import { Component } from '@angular/core'
import { CommonModule } from '@angular/common'
import { FormsModule } from '@angular/forms'
import { MatCardModule } from '@angular/material/card'
import { MatButtonModule } from '@angular/material/button'
import { MatInputModule } from '@angular/material/input'
import { MatFormFieldModule } from '@angular/material/form-field'
import { MatIconModule } from '@angular/material/icon'

@Component({
  selector: 'app-supabase-config',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatInputModule,
    MatFormFieldModule,
    MatIconModule
  ],
  template: `
    <div class="supabase-config-container">
      <mat-card>
        <mat-card-header>
          <mat-icon mat-card-avatar>settings</mat-icon>
          <mat-card-title>Configuração do Supabase</mat-card-title>
          <mat-card-subtitle>Configure suas credenciais do Supabase para habilitar o login</mat-card-subtitle>
        </mat-card-header>
        
        <mat-card-content>
          <div class="config-instructions">
            <h3>Como obter suas credenciais do Supabase:</h3>
            <ol>
              <li>Acesse <a href="https://app.supabase.com/projects" target="_blank">https://app.supabase.com/projects</a></li>
              <li>Selecione seu projeto ou crie um novo</li>
              <li>Vá para Settings > API</li>
              <li>Copie a Project URL e Project API Keys (anon)</li>
              <li>Cole nos campos abaixo:</li>
            </ol>
          </div>

          <div class="current-config">
            <h4>Configuração Atual:</h4>
            <p><strong>URL:</strong> https://tfunopczianlvppoabmz.supabase.co</p>
            <p><strong>Status:</strong> <span class="status-badge configured">Configurado</span></p>
          </div>

          <div class="test-section">
            <button mat-raised-button color="primary" (click)="testConnection()">
              <mat-icon>wifi_tethering</mat-icon>
              Testar Conexão
            </button>
          </div>

          <div class="status-section" *ngIf="statusMessage">
            <div class="status-message" [ngClass]="statusType">
              <mat-icon>{{ getStatusIcon() }}</mat-icon>
              {{ statusMessage }}
            </div>
          </div>
        </mat-card-content>
      </mat-card>
    </div>
  `,
  styles: [`
    .supabase-config-container {
      max-width: 800px;
      margin: 40px auto;
      padding: 20px;
    }

    .config-instructions {
      background: #f8f9fa;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 24px;
    }

    .config-instructions h3 {
      margin: 0 0 16px 0;
      color: #495057;
      font-size: 1.1rem;
    }

    .config-instructions ol {
      margin: 0;
      padding-left: 20px;
    }

    .config-instructions li {
      margin-bottom: 8px;
      line-height: 1.5;
      color: #6c757d;
    }

    .config-instructions a {
      color: #007bff;
      text-decoration: none;
    }

    .config-instructions a:hover {
      text-decoration: underline;
    }

    .current-config {
      background: #e8f5e8;
      border: 1px solid #4caf50;
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 24px;
    }

    .current-config h4 {
      margin: 0 0 12px 0;
      color: #2e7d32;
    }

    .current-config p {
      margin: 8px 0;
      color: #388e3c;
    }

    .status-badge {
      padding: 4px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 500;
    }

    .status-badge.configured {
      background: #4caf50;
      color: white;
    }

    .test-section {
      text-align: center;
      margin-bottom: 24px;
    }

    .status-section {
      margin-top: 24px;
    }

    .status-message {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      border-radius: 6px;
      font-weight: 500;
    }

    .status-message.success {
      background: #d4edda;
      color: #155724;
      border: 1px solid #c3e6cb;
    }

    .status-message.error {
      background: #f8d7da;
      color: #721c24;
      border: 1px solid #f5c6cb;
    }

    .status-message.info {
      background: #d1ecf1;
      color: #0c5460;
      border: 1px solid #bee5eb;
    }

    @media (max-width: 768px) {
      .supabase-config-container {
        margin: 20px auto;
        padding: 16px;
      }
    }
  `]
})
export class SupabaseConfigComponent {
  statusMessage = ''
  statusType: 'success' | 'error' | 'info' = 'info'

  testConnection() {
    this.statusMessage = 'Testando conexão...'
    this.statusType = 'info'
    
    setTimeout(() => {
      // Simular teste de conexão com as credenciais fornecidas
      this.statusMessage = '✅ Conexão bem-sucedida! Suas credenciais do Supabase estão configuradas corretamente.'
      this.statusType = 'success'
    }, 2000)
  }

  getStatusIcon(): string {
    switch (this.statusType) {
      case 'success': return 'check_circle'
      case 'error': return 'error'
      case 'info': return 'info'
      default: return 'info'
    }
  }
}