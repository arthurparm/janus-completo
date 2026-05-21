import { Injectable, inject } from '@angular/core'

import { ConversationStateFacade } from './conversations-state.facade'
import type { RailNoticeKind, RailNoticeSection } from './conversations.types'

@Injectable({ providedIn: 'root' })
export class ConversationsNoticeService {
  private state = inject(ConversationStateFacade)
  private timers = new Map<RailNoticeSection, ReturnType<typeof setTimeout>>()

  set(section: RailNoticeSection, kind: RailNoticeKind, message: string, autoHideMs = 2800): void {
    const setter = this.noticeSignal(section)
    const existingTimer = this.timers.get(section)
    if (existingTimer) {
      clearTimeout(existingTimer)
      this.timers.delete(section)
    }
    setter.set({ kind, message, visible: true })
    if (kind === 'error') return
    const timer = setTimeout(() => {
      setter.set(null)
      this.timers.delete(section)
    }, autoHideMs)
    this.timers.set(section, timer)
  }

  clear(section: RailNoticeSection): void {
    const existingTimer = this.timers.get(section)
    if (existingTimer) {
      clearTimeout(existingTimer)
      this.timers.delete(section)
    }
    this.noticeSignal(section).set(null)
  }

  private noticeSignal(section: RailNoticeSection) {
    if (section === 'docs') return this.state.docsNotice
    if (section === 'memory') return this.state.memoryNotice
    if (section === 'rag') return this.state.ragNotice
    return this.state.autonomyNotice
  }
}

