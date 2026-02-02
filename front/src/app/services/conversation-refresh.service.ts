import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ConversationRefreshService {
  private refreshConversations$ = new Subject<void>();

  // Observable para ouvir eventos de refresh
  get refreshConversations() {
    return this.refreshConversations$.asObservable();
  }

  // Emitir evento de refresh
  triggerRefresh() {
    console.log('🔄 ConversationRefreshService: Triggering conversations refresh')
    this.refreshConversations$.next();
  }
}
