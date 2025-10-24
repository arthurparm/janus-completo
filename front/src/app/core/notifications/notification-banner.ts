import { Component, OnDestroy, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NotificationService, NotificationMessage } from './notification.service';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-notification-banner',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './notification-banner.html',
  styleUrl: './notification-banner.scss'
})
export class NotificationBanner implements OnInit, OnDestroy {
  private sub?: Subscription;
  current = signal<NotificationMessage | null>(null);

  constructor(private notifications: NotificationService) {}

  ngOnInit(): void {
    this.sub = this.notifications.stream$.subscribe((msg) => {
      this.current.set(msg);
      // Auto-hide non-error after 5s
      if (msg.type !== 'error') {
        setTimeout(() => {
          if (this.current()?.timestamp === msg.timestamp) {
            this.dismiss();
          }
        }, 5000);
      }
    });
  }

  ngOnDestroy(): void {
    this.sub?.unsubscribe();
  }

  dismiss(): void {
    this.current.set(null);
  }
}