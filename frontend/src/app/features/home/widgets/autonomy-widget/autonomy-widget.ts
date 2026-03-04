import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { BackendApiService, AutonomyStatusResponse } from '../../../../services/backend-api.service';
import { Observable, of } from 'rxjs';
import { catchError, shareReplay } from 'rxjs/operators';

@Component({
  selector: 'app-autonomy-widget',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './autonomy-widget.html',
  styleUrls: ['./autonomy-widget.scss'],
})
export class AutonomyWidget {
  private api = inject(BackendApiService);
  private router = inject(Router);

  status$: Observable<AutonomyStatusResponse | null>;

  constructor() {
    this.status$ = this.api.getAutonomyStatus().pipe(
      catchError(() => of(null)),
      shareReplay({ bufferSize: 1, refCount: true })
    );
  }

  getRiskProfile(status: AutonomyStatusResponse | null): string {
    return status?.config?.risk_profile || 'Unknown';
  }

  getRiskColor(risk: string | undefined): string {
    switch (risk?.toLowerCase()) {
      case 'aggressive': return 'text-red-400';
      case 'balanced': return 'text-yellow-400';
      case 'conservative': return 'text-green-400';
      default: return 'text-gray-400';
    }
  }

  openAutonomyPanel(): void {
    try {
      localStorage.setItem('janus.conversations.show_advanced_mode', '1');
      localStorage.setItem('janus.conversations.advanced_rail_tab', 'autonomia');
    } catch {
      // no-op
    }
    void this.router.navigate(['/conversations']);
  }
}
