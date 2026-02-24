import { Injectable } from '@angular/core';
import { Subject, Observable } from 'rxjs';

export type NotificationType = 'error' | 'info' | 'success' | 'warning';

export interface NotificationMessage {
  type: NotificationType;
  message: string;
  title?: string;
  detail?: string;
  timestamp?: number;
}

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private subject = new Subject<NotificationMessage>();
  readonly stream$: Observable<NotificationMessage> = this.subject.asObservable();

  notify(msg: NotificationMessage): void {
    this.subject.next({ ...msg, timestamp: Date.now() });
  }

  notifyError(message: string, detail?: string, title?: string): void {
    this.notify({ type: 'error', message, detail, title });
  }

  notifyInfo(message: string, detail?: string, title?: string): void {
    this.notify({ type: 'info', message, detail, title });
  }

  notifyWarning(message: string, detail?: string, title?: string): void {
    this.notify({ type: 'warning', message, detail, title });
  }

  notifySuccess(message: string, detail?: string, title?: string): void {
    this.notify({ type: 'success', message, detail, title });
  }
}