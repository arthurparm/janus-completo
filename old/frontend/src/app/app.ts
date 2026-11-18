import { Component, signal, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { BackendAvailabilityService } from './core/services/backend-availability.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, CommonModule],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly title = signal('janus-angular');
  readonly backendAvailability = inject(BackendAvailabilityService);

  retryBackend(): void {
    void this.backendAvailability.checkNow();
  }
}
