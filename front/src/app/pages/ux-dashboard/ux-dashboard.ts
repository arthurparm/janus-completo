import { Component, OnInit, inject } from '@angular/core'
import { CommonModule } from '@angular/common'
import { UxMetricsService, UxMetricItem } from '../../services/ux-metrics.service'

@Component({
  selector: 'app-ux-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ux-dashboard.html',
  styleUrl: './ux-dashboard.scss'
})
export class UxDashboardComponent implements OnInit {
  private ux = inject(UxMetricsService)
  metrics: UxMetricItem[] = []
  p95: number | null = null
  ngOnInit() {
    this.ux.metrics().subscribe(m => { this.metrics = m; this.p95 = this.ux.p95Latency() })
  }
}