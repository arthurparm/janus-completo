import { Injectable } from '@angular/core';
import { API_BASE_URL } from './api.config';

@Injectable({ providedIn: 'root' })
export class ApiContextService {
  private _projectId?: string;
  private _sessionId?: string;
  private _conversationId?: string;
  private _persona?: string;
  private _role?: string;
  private _priority?: string;

  public buildUrl(path: string): string {
    const p = String(path || '');
    if (p === '/healthz') return p;
    if (p.startsWith('/api/')) return p;
    if (p.startsWith('/v1/')) return `${API_BASE_URL}${p}`;
    return `${API_BASE_URL}${p.startsWith('/') ? '' : '/'}${p}`;
  }

  private _reqId(): string {
    const s = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx';
    return s.replace(/[xy]/g, c => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

  private _traceparent(): string {
    const hex = (size: number) => {
      let out = '';
      for (let i = 0; i < size; i += 1) {
        out += Math.floor(Math.random() * 16).toString(16);
      }
      return out;
    };
    return `00-${hex(32)}-${hex(16)}-01`;
  }

  setProjectId(project_id?: string) { this._projectId = project_id || undefined; }
  setSessionId(session_id?: string) { this._sessionId = session_id || undefined; }
  setConversationId(conversation_id?: string) { this._conversationId = conversation_id || undefined; }
  setPersona(persona?: string) { this._persona = persona || undefined; }
  setRole(role?: string) { this._role = role || undefined; }
  setPriority(priority?: string) { this._priority = priority || undefined; }
  clearContext() { this._projectId = undefined; this._sessionId = undefined; this._conversationId = undefined; }

  public headersFor(userId?: number | string): Record<string, string> {
    const h: Record<string, string> = {
      'X-Request-ID': this._reqId(),
      traceparent: this._traceparent(),
    };
    if (typeof userId !== 'undefined') h['X-User-Id'] = String(userId);
    if (this._projectId) h['X-Project-Id'] = this._projectId;
    if (this._sessionId) h['X-Session-Id'] = this._sessionId;
    if (this._conversationId) h['X-Conversation-Id'] = this._conversationId;
    if (this._persona) h['X-Persona'] = this._persona;
    if (this._role) h['X-Role'] = this._role;
    if (this._priority) h['X-Priority'] = this._priority;
    return h;
  }
}
