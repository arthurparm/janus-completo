import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';
import { AppLoggerService } from '../core/services/app-logger.service';

@Injectable({
  providedIn: 'root'
})
export class ConversationRefreshService {
  private refreshConversations$ = new Subject<void>();
  constructor(private readonly logger: AppLoggerService) {}

  // Observable para ouvir eventos de refresh
  get refreshConversations() {
    return this.refreshConversations$.asObservable();
  }

  // Emitir evento de refresh
  triggerRefresh() {
    this.logger.debug('[ConversationRefreshService] Triggering conversations refresh')
    this.refreshConversations$.next();
  }
}
