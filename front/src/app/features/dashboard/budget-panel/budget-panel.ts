import { Component, OnInit, OnDestroy, signal, computed, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { JanusApiService } from '../../../services/janus-api.service';
import { interval, Subscription, Observable } from 'rxjs';
import { switchMap, startWith } from 'rxjs/operators';

interface BudgetSummaryResponse {
  providers: ProviderBudget[];
  total_spent: number;
  total_budget: number;
  guardrail_active: boolean;
  timestamp: string;
}

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
  templateUrl: './budget-panel.html',
  styleUrl: './budget-panel.scss'
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

  private fetchMetrics(): Observable<void> {
    this.loading.set(true);
    this.error.set(null);

    return new Observable(observer => {
      this.api.getBudgetSummary().subscribe({
        next: (data: BudgetSummaryResponse) => {
          this.metrics.set({
            providers: data.providers,
            totalSpent: data.total_spent,
            totalBudget: data.total_budget,
            guardrailActive: data.guardrail_active
          });

          this.lastUpdated.set(new Date());
          this.loading.set(false);
          observer.next();
          observer.complete();
        },
        error: (err: Error) => {
          this.error.set('Failed to load budget metrics');
          console.error(err);
          this.loading.set(false);
          observer.error(err);
        }
      });
    });
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
