import { Component, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../../auth/auth.service';
import { CommonModule } from '@angular/common';
import { JarvisAvatarComponent } from '../../../shared/components/jarvis-avatar/jarvis-avatar.component';
import { JanusApiService, SystemStatus } from '../../../services/janus-api.service';
import { Observable, of, timer } from 'rxjs';
import { catchError, map, shareReplay, switchMap } from 'rxjs/operators';

interface HeaderMetrics {
  cpu: number | null;
  memory: number | null;
}

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, CommonModule, JarvisAvatarComponent],
  templateUrl: './header.html',
  styleUrl: './header.scss'
})
export class Header {
  private auth = inject(AuthService);
  private api = inject(JanusApiService);

  isMenuOpen = false;
  isAuthenticated$ = this.auth.isAuthenticated$;

  metrics$: Observable<HeaderMetrics>;

  constructor() {
    this.metrics$ = timer(0, 10000).pipe(
      switchMap(() => this.api.getSystemStatus().pipe(catchError(() => of(null)))),
      map((status: SystemStatus | null) => {
        const perf = status?.performance as { cpu_percent?: number; memory_percent?: number } | undefined;
        const cpu = typeof perf?.cpu_percent === 'number' ? perf.cpu_percent : null;
        const memory = typeof perf?.memory_percent === 'number' ? perf.memory_percent : null;
        return { cpu, memory };
      }),
      shareReplay({ bufferSize: 1, refCount: true })
    );
  }

  toggleMenu() {
    this.isMenuOpen = !this.isMenuOpen;
  }

  closeMenu() {
    this.isMenuOpen = false;
  }

  logout() {
    this.auth.logout();
  }
}
