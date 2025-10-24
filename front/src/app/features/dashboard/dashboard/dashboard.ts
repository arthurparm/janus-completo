import {Component, OnInit, OnDestroy} from '@angular/core'
import {NgIf, NgFor} from '@angular/common'
import {HttpClientModule} from '@angular/common/http'
import {JanusApiService, SystemStatus, ServiceHealthItem, WorkersStatusItem} from '../../../services/janus-api.service'
import { forkJoin, Subject } from 'rxjs'
import { takeUntil } from 'rxjs/operators'

@Component({
  selector: 'app-dashboard',
  imports: [NgIf, NgFor, HttpClientModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss'
})
export class Dashboard implements OnInit, OnDestroy {
  loading = true
  apiHealthy: 'unknown' | 'ok' = 'unknown'
  systemStatus?: SystemStatus
  services: ServiceHealthItem[] = []
  workers: WorkersStatusItem[] = []
  private destroy$ = new Subject<void>()

  constructor(private api: JanusApiService) {}

  ngOnInit(): void {
    this.loading = true

    forkJoin({
      health: this.api.health(),
      system: this.api.getSystemStatus(),
      services: this.api.getServicesHealth(),
      workers: this.api.getWorkersStatus()
    }).pipe(takeUntil(this.destroy$)).subscribe({
      next: ({ health, system, services, workers }) => {
        this.apiHealthy = health.status === 'ok' ? 'ok' : 'unknown'
        this.systemStatus = system
        this.services = services.services || []
        this.workers = workers.workers || []
      },
      error: () => {
        // Errors are handled globally by interceptors; just stop loading
        this.loading = false
      },
      complete: () => {
        this.loading = false
      }
    })
  }

  ngOnDestroy(): void {
    this.destroy$.next()
    this.destroy$.complete()
  }

  startWorkers(): void {
    this.api.startAllWorkers().pipe(takeUntil(this.destroy$)).subscribe({
      next: () => this.refreshWorkers(),
      error: () => {}
    })
  }

  stopWorkers(): void {
    this.api.stopAllWorkers().pipe(takeUntil(this.destroy$)).subscribe({
      next: () => this.refreshWorkers(),
      error: () => {}
    })
  }

  private refreshWorkers(): void {
    this.api.getWorkersStatus().pipe(takeUntil(this.destroy$)).subscribe({
      next: (resp) => (this.workers = resp.workers || []),
      error: () => {}
    })
  }
}
