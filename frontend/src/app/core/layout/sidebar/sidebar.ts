import { Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { UiIconComponent } from '../../../shared/components/ui/icon/icon.component';
import { AuthService } from '../../auth/auth.service';
import { GlobalStateStore } from '../../state/global-state.store';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, CommonModule, UiIconComponent],
  templateUrl: './sidebar.html',
  styleUrl: './sidebar.scss'
})
export class Sidebar {
  private store = inject(GlobalStateStore);
  private auth = inject(AuthService);

  readonly apiHealthy = this.store.apiHealthy;
  readonly services = this.store.services;
  readonly workers = this.store.workers;
  readonly isAdmin = this.auth.isAdmin;
  readonly runningWorkers = computed(() =>
    this.workers().filter((worker) => (worker.status || '').toLowerCase() === 'running').length
  );
}
