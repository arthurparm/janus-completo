import {Component, OnInit} from '@angular/core'
import {NgIf, NgFor} from '@angular/common'
import {HttpClientModule} from '@angular/common/http'
import {JanusApiService, SystemStatus, ServiceHealthItem, WorkersStatusItem} from '../../../services/janus-api.service'

@Component({
  selector: 'app-dashboard',
  imports: [NgIf, NgFor, HttpClientModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss'
})
export class Dashboard implements OnInit {
  loading = true
  apiHealthy: 'unknown' | 'ok' = 'unknown'
  systemStatus?: SystemStatus
  services: ServiceHealthItem[] = []
  workers: WorkersStatusItem[] = []

  constructor(private api: JanusApiService) {}

  ngOnInit(): void {
    // Quick API health
    this.api.health().subscribe({
      next: (h) => (this.apiHealthy = h.status === 'ok' ? 'ok' : 'unknown'),
      error: () => (this.apiHealthy = 'unknown')
    })

    // System status
    this.api.getSystemStatus().subscribe({
      next: (status) => {
        this.systemStatus = status
      },
      error: () => {},
      complete: () => {
        this.loading = false
      }
    })

    // Services health
    this.api.getServicesHealth().subscribe({
      next: (resp) => (this.services = resp.services || []),
      error: () => {}
    })

    // Workers status
    this.api.getWorkersStatus().subscribe({
      next: (resp) => (this.workers = resp.workers || []),
      error: () => {}
    })
  }

  startWorkers(): void {
    this.api.startAllWorkers().subscribe({
      next: () => this.refreshWorkers(),
      error: () => {}
    })
  }

  stopWorkers(): void {
    this.api.stopAllWorkers().subscribe({
      next: () => this.refreshWorkers(),
      error: () => {}
    })
  }

  private refreshWorkers(): void {
    this.api.getWorkersStatus().subscribe({
      next: (resp) => (this.workers = resp.workers || []),
      error: () => {}
    })
  }
}
