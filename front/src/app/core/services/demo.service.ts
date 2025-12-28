import { Injectable, signal } from '@angular/core';

@Injectable({
    providedIn: 'root'
})
export class DemoService {
    // Signal to track if we are in offline/demo mode
    // Default to false, potentially set to true on first error
    readonly isOffline = signal<boolean>(false);

    constructor() {
        // Always start fresh, let the app discover if backend is down
        this.isOffline.set(false);
    }

    /**
     * Enable offline mode.
     * Can be called by interceptors when critical failures occur.
     */
    enableOfflineMode(): void {
        if (!this.isOffline()) {
            console.warn('[DemoService] Backend unreachable. Switching to Demo/Offline Mode.');
            this.isOffline.set(true);
            // sessionStorage.setItem('JANUS_OFFLINE_MODE', 'true');
        }
    }

    /**
     * Reset offline mode (e.g. if user manually retries).
     */
    resetMode(): void {
        this.isOffline.set(false);
        sessionStorage.removeItem('JANUS_OFFLINE_MODE');
    }
}
