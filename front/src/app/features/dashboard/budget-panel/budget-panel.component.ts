import { Component, OnInit, OnDestroy, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { JanusApiService } from '../../../services/janus-api.service';
import { interval, Subscription } from 'rxjs';
import { switchMap, startWith } from 'rxjs/operators';

interface ProviderBudget {
    provider: string;
    spent: number;
    budget: number;
    remaining: number;
    percentage: number;
}

interface BudgetMetrics {
    providers: ProviderBudget[];
    totalSpent: number;
    totalBudget: number;
    guardrailActive: boolean;
}

@Component({
    selector: 'app-budget-panel',
    standalone: true,
    imports: [CommonModule],
    template: `
    <div class="budget-panel">
      <div class="panel-header">
        <h3>💰 Budget & Usage</h3>
        <button (click)="toggleAutoRefresh()" [class.active]="autoRefresh()">
          {{ autoRefresh() ? '⏸️ Pause' : '▶️ Auto-refresh' }}
        </button>
      </div>

      @if (loading() && !metrics()) {
        <div class="loading">Loading budget data...</div>
      }

      @if (error()) {
        <div class="error-message">{{ error() }}</div>
      }

      @if (metrics(); as data) {
        <!-- Guardrail Alert -->
        @if (data.guardrailActive) {
          <div class="guardrail-alert">
            ⚠️ Budget Guardrail Active - Cloud models restricted
          </div>
        }

        <!-- Total Budget -->
        <div class="total-budget">
          <div class="budget-label">Total Monthly Budget</div>
          <div class="budget-amount">\${{ data.totalBudget.toFixed(2) }}</div>
          <div class="budget-progress-bar">
            <div 
              class="budget-progress-fill" 
              [style.width.%]="totalPercentage()"
              [class.warning]="totalPercentage() > 75"
              [class.danger]="totalPercentage() > 90">
            </div>
          </div>
          <div class="budget-stats">
            <span>Spent: \${{ data.totalSpent.toFixed(2) }}</span>
            <span>{{ totalPercentage() }}%</span>
          </div>
        </div>

        <!-- Provider Breakdown -->
        <div class="providers-list">
          @for (provider of data.providers; track provider.provider) {
            <div class="provider-card" [class.over-budget]="provider.percentage > 100">
              <div class="provider-header">
                <span class="provider-name">{{ providerDisplayName(provider.provider) }}</span>
                <span class="provider-percentage">{{ provider.percentage.toFixed(1) }}%</span>
              </div>
              <div class="provider-bar">
                <div 
                  class="provider-bar-fill" 
                  [style.width.%]="Math.min(provider.percentage, 100)"
                  [class.warning]="provider.percentage > 75"
                  [class.danger]="provider.percentage > 90">
                </div>
              </div>
              <div class="provider-details">
                <span>\${{ provider.spent.toFixed(4) }} / \${{ provider.budget.toFixed(2) }}</span>
                <span class="remaining">\${{ provider.remaining.toFixed(2) }} left</span>
              </div>
            </div>
          }
        </div>

        <div class="last-updated">
          Last updated: {{ lastUpdated() | date:'short' }}
        </div>
      }
    </div>
  `,
    styles: [`
    .budget-panel {
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      border-radius: 12px;
      padding: 1.5rem;
      color: #eee;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 1.5rem;
    }

    .panel-header h3 {
      margin: 0;
      font-size: 1.5rem;
    }

    button {
      padding: 0.5rem 1rem;
      background: #2a2a3e;
      color: #4a90e2;
      border: 1px solid #4a90e2;
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.2s;
    }

    button:hover {
      background: #4a90e2;
      color: white;
    }

    button.active {
      background: #4a90e2;
      color: white;
    }

    .guardrail-alert {
      background: #ff4444;
      padding: 1rem;
      border-radius: 8px;
      margin-bottom: 1rem;
      text-align: center;
      font-weight: bold;
    }

    .total-budget {
      background: rgba(74, 144, 226, 0.1);
      border: 2px solid #4a90e2;
      border-radius: 8px;
      padding: 1.5rem;
      margin-bottom: 1.5rem;
    }

    .budget-label {
      font-size: 0.9rem;
      opacity: 0.8;
      margin-bottom: 0.5rem;
    }

    .budget-amount {
      font-size: 2rem;
      font-weight: bold;
      margin-bottom: 1rem;
    }

    .budget-progress-bar {
      height: 12px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 6px;
      overflow: hidden;
      margin-bottom: 0.5rem;
    }

    .budget-progress-fill {
      height: 100%;
      background: linear-gradient(90deg, #4a90e2, #357abd);
      transition: width 0.3s ease;
    }

    .budget-progress-fill.warning {
      background: linear-gradient(90deg, #f39c12, #e67e22);
    }

    .budget-progress-fill.danger {
      background: linear-gradient(90deg, #e74c3c, #c0392b);
    }

    .budget-stats {
      display: flex;
      justify-content: space-between;
      font-size: 0.9rem;
    }

    .providers-list {
      display: grid;
      gap: 1rem;
    }

    .provider-card {
      background: rgba(255, 255, 255, 0.05);
      border-radius: 8px;
      padding: 1rem;
      border-left: 4px solid #4a90e2;
      transition: transform 0.2s;
    }

    .provider-card:hover {
      transform: translateX(4px);
    }

    .provider-card.over-budget {
      border-left-color: #e74c3c;
      background: rgba(231, 76, 60, 0.1);
    }

    .provider-header {
      display: flex;
      justify-content: space-between;
      margin-bottom: 0.5rem;
      font-weight: bold;
    }

    .provider-name {
      text-transform: capitalize;
    }

    .provider-percentage {
      color: #4a90e2;
    }

    .provider-bar {
      height: 8px;
      background: rgba(255, 255, 255, 0.1);
      border-radius: 4px;
      overflow: hidden;
      margin-bottom: 0.5rem;
    }

    .provider-bar-fill {
      height: 100%;
      background: #4a90e2;
      transition: width 0.3s ease;
    }

    .provider-bar-fill.warning {
      background: #f39c12;
    }

    .provider-bar-fill.danger {
      background: #e74c3c;
    }

    .provider-details {
      display: flex;
      justify-content: space-between;
      font-size: 0.85rem;
      opacity: 0.8;
    }

    .remaining {
      color: #2ecc71;
    }

    .last-updated {
      text-align: center;
      font-size: 0.8rem;
      opacity: 0.6;
      margin-top: 1rem;
    }

    .loading, .error-message {
      padding: 2rem;
      text-align: center;
    }

    .error-message {
      color: #e74c3c;
    }
  `]
})
export class BudgetPanelComponent implements OnInit, OnDestroy {
    private api = inject(JanusApiService);

    // Signals
    metrics = signal<BudgetMetrics | null>(null);
    loading = signal(false);
    error = signal<string | null>(null);
    autoRefresh = signal(true);
    lastUpdated = signal(new Date());

    // Computed
    totalPercentage = computed(() => {
        const m = this.metrics();
        if (!m || m.totalBudget === 0) return 0;
        return (m.totalSpent / m.totalBudget) * 100;
    });

    Math = Math; // For template

    private refreshSub?: Subscription;

    ngOnInit() {
        this.startAutoRefresh();
    }

    ngOnDestroy() {
        this.stopAutoRefresh();
    }

    private startAutoRefresh() {
        if (this.refreshSub) return;

        // Poll every 30 seconds
        this.refreshSub = interval(30000).pipe(
            startWith(0),
            switchMap(() => this.fetchMetrics())
        ).subscribe();
    }

    private stopAutoRefresh() {
        this.refreshSub?.unsubscribe();
        this.refreshSub = undefined;
    }

    toggleAutoRefresh() {
        if (this.autoRefresh()) {
            this.autoRefresh.set(false);
            this.stopAutoRefresh();
        } else {
            this.autoRefresh.set(true);
            this.startAutoRefresh();
        }
    }

    private fetchMetrics() {
        this.loading.set(true);
        this.error.set(null);

        return this.api.getMetricsSummary().subscribe({
            next: (data) => {
                // Transform backend metrics to our format
                const providers: ProviderBudget[] = [
                    {
                        provider: 'openai',
                        spent: this.extractProviderSpent(data, 'openai'),
                        budget: 50, // From config
                        remaining: 0,
                        percentage: 0
                    },
                    {
                        provider: 'deepseek',
                        spent: this.extractProviderSpent(data, 'deepseek'),
                        budget: 20,
                        remaining: 0,
                        percentage: 0
                    },
                    {
                        provider: 'google_gemini',
                        spent: this.extractProviderSpent(data, 'google_gemini'),
                        budget: 25,
                        remaining: 0,
                        percentage: 0
                    }
                ];

                // Calculate percentages and remaining
                providers.forEach(p => {
                    p.remaining = Math.max(0, p.budget - p.spent);
                    p.percentage = p.budget > 0 ? (p.spent / p.budget) * 100 : 0;
                });

                const totalSpent = providers.reduce((sum, p) => sum + p.spent, 0);
                const totalBudget = providers.reduce((sum, p) => sum + p.budget, 0);

                this.metrics.set({
                    providers,
                    totalSpent,
                    totalBudget,
                    guardrailActive: totalSpent >= (totalBudget * 0.9)
                });

                this.lastUpdated.set(new Date());
                this.loading.set(false);
            },
            error: (err) => {
                this.error.set('Failed to load budget metrics');
                console.error(err);
                this.loading.set(false);
            }
        });
    }

    private extractProviderSpent(data: any, provider: string): number {
        // This would need to match actual backend metrics structure
        // For now, returning mock data
        return Math.random() * 10;
    }

    providerDisplayName(provider: string): string {
        const names: Record<string, string> = {
            'openai': 'OpenAI',
            'deepseek': 'DeepSeek',
            'google_gemini': 'Google Gemini',
            'ollama': 'Ollama (Local)'
        };
        return names[provider] || provider;
    }
}
