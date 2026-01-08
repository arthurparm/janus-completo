import { Injectable, computed, inject, signal } from '@angular/core';
import { JanusApiService, ConversationMeta } from '../../../services/janus-api.service';
import { AuthService } from '../../../core/auth/auth.service';
import { catchError, finalize, switchMap, take } from 'rxjs/operators';
import { of } from 'rxjs';

export interface ConversationsFilter {
    query: string;
    status: 'new' | 'progress' | 'done' | '';
    startDate?: string;
    endDate?: string;
}

export interface ConversationsSort {
    key: 'updated_at' | 'created_at' | 'last_message_at' | 'title' | 'message_count';
    direction: 'asc' | 'desc';
}

@Injectable({
    providedIn: 'root'
})
export class ConversationStore {
    private api = inject(JanusApiService);
    private auth = inject(AuthService);

    // State
    private _items = signal<ConversationMeta[]>([]);
    private _loading = signal<boolean>(false);
    private _error = signal<string | null>(null);

    // Filters & Sorting state
    private _filter = signal<ConversationsFilter>({
        query: '',
        status: '',
        startDate: undefined,
        endDate: undefined
    });

    private _sort = signal<ConversationsSort>({
        key: 'updated_at',
        direction: 'desc'
    });

    // Selectors
    readonly items = this._items.asReadonly();
    readonly loading = this._loading.asReadonly();
    readonly error = this._error.asReadonly();

    readonly filter = this._filter.asReadonly();
    readonly sort = this._sort.asReadonly();

    // Computed
    readonly filteredConversations = computed(() => {
        const items = this._items();
        const filter = this._filter();
        const sort = this._sort();

        // 1. Filter by Query (Title or Content)
        let result = items;
        const q = filter.query.toLowerCase().trim();
        if (q) {
            result = result.filter(it => {
                const t = (it.title || '').toLowerCase();
                const c = (it.last_message?.text || '').toLowerCase();
                return t.includes(q) || c.includes(q);
            });
        }

        // 2. Filter by Status
        if (filter.status) {
            result = result.filter(it => {
                const s = this.getStatusChip(it).toLowerCase();
                const label = this.getStatusFilterLabel(filter.status);
                return s === label;
            });
        }

        // 3. Filter by Date
        if (filter.startDate || filter.endDate) {
            const sd = filter.startDate ? Date.parse(filter.startDate) : undefined;
            const ed = filter.endDate ? Date.parse(filter.endDate) : undefined;

            result = result.filter(it => {
                const updatedAt = it.updated_at || it.created_at;
                const val = Number(updatedAt || 0);
                if (!updatedAt) return false;

                const startMatch = !sd || val >= sd;
                const endMatch = !ed || val <= ed;
                return startMatch && endMatch;
            });
        }

        // 4. Sort
        result = [...result].sort((a, b) => { // Create copy to avoid mutating signal value in place (good practice)
            let ka: string | number, kb: string | number;

            if (sort.key === 'last_message_at') {
                ka = Date.parse(a.last_message_at || '');
                kb = Date.parse(b.last_message_at || '');
            } else if (sort.key === 'title') {
                ka = (a.title || '').toLowerCase();
                kb = (b.title || '').toLowerCase();
            } else if (sort.key === 'message_count') {
                ka = a.message_count || 0;
                kb = b.message_count || 0;
            } else {
                ka = Number(a[sort.key] || 0);
                kb = Number(b[sort.key] || 0);
            }

            // Handle simple comparison
            if (ka > kb) return sort.direction === 'asc' ? 1 : -1;
            if (ka < kb) return sort.direction === 'asc' ? -1 : 1;
            return 0;
        });

        return result;
    });

    readonly totalCount = computed(() => this._items().length);
    readonly filteredCount = computed(() => this.filteredConversations().length);

    // Actions
    load(projectId?: string) {
        this._loading.set(true);
        this._error.set(null);

        // Use switchMap to handle auth dependency cleanly
        this.auth.user$.pipe(
            // We only want to trigger this fetch once per load call based on *current* user
            // But BehaviorSubject emits immediately. 
            // If we want to wait for non-null? Or just accept whatever is there?
            // Assuming we want to proceed even if user is null (public access?) or wait?
            // For now, take(1) gets the current/latest value.
            take(1),
            switchMap(user => {
                const userId = user?.id;
                const params = {
                    user_id: userId,
                    project_id: projectId
                };
                return this.api.listConversations(params);
            }),
            finalize(() => this._loading.set(false)),
            catchError(err => {
                console.error('Store loading error', err);
                this._error.set('Falha ao carregar conversas');
                return of({ conversations: [] });
            })
        ).subscribe(resp => {
            this._items.set(resp.conversations || []);
        });
    }

    setFilter(changes: Partial<ConversationsFilter>) {
        this._filter.update(current => ({ ...current, ...changes }));
    }

    setSort(key: ConversationsSort['key']) {
        this._sort.update(current => {
            if (current.key === key) {
                // Toggle direction
                return { ...current, direction: current.direction === 'asc' ? 'desc' : 'asc' };
            }
            return { key, direction: 'desc' }; // Default to desc for new key
        });
    }

    removeConversation(id: string) {
        this._items.update(items => items.filter(i => i.conversation_id !== id));
        // Also trigger API call to delete (optional: move to component or handle here with effect)
        // For a store pattern, it's often better to handle the API call here
        this.api.deleteConversation(id).subscribe({
            error: () => {
                // Optimistic update failed? Reload or show error.
                // For now, simpler to just reload or let component handle the "Delete" action flow fully.
                // But the "Store" philosophy says "tell store to delete".
                this.load(); // Revert/Reload
            }
        });
    }

    renameConversation(id: string, newTitle: string) {
        // Optimistic update
        this._items.update(items => items.map(i => {
            if (i.conversation_id === id) {
                return { ...i, title: newTitle };
            }
            return i;
        }));

        this.api.renameConversation(id, newTitle).subscribe({
            error: () => this.load() // Revert on error
        });
    }

    // Helpers (Logic moved from component)
    private getStatusChip(it: ConversationMeta): 'nova' | 'em andamento' | 'resolvida' {
        const hasMsg = !!it.last_message;
        const updated = Number(it.updated_at || 0);
        const now = Date.now();
        const days = (now - updated) / (1000 * 60 * 60 * 24);

        if (!hasMsg) return 'nova';
        if (days > 7) return 'resolvida';
        return 'em andamento';
    }

    private getStatusFilterLabel(filter: string): string {
        switch (filter) {
            case 'new': return 'nova';
            case 'progress': return 'em andamento';
            case 'done': return 'resolvida';
            default: return '';
        }
    }
}
