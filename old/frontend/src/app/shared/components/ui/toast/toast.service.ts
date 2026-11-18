import { Injectable } from '@angular/core';
import { Overlay, OverlayRef } from '@angular/cdk/overlay';
import { ComponentPortal } from '@angular/cdk/portal';
import { UiToasterComponent } from './toaster.component';
import { ToastConfig } from './toast.types';

@Injectable({ providedIn: 'root' })
export class UiToastService {
    private overlayRef?: OverlayRef;
    private toaster?: UiToasterComponent;

    constructor(private overlay: Overlay) { }

    show(config: ToastConfig) {
        this.ensureToaster();
        this.toaster?.add({
            ...config,
            id: Date.now() + Math.random()
        });
    }

    success(message: string, duration = 5000) {
        this.show({ message, type: 'success', duration });
    }

    error(message: string, duration = 5000) {
        this.show({ message, type: 'error', duration });
    }

    info(message: string, duration = 5000) {
        this.show({ message, type: 'info', duration });
    }

    warning(message: string, duration = 5000) {
        this.show({ message, type: 'warning', duration });
    }

    private ensureToaster() {
        if (this.toaster) return;

        this.overlayRef = this.overlay.create({
            panelClass: 'toast-overlay-container',
            hasBackdrop: false,
            positionStrategy: this.overlay.position().global(),
            scrollStrategy: this.overlay.scrollStrategies.noop()
        });

        const portal = new ComponentPortal(UiToasterComponent);
        const ref = this.overlayRef.attach(portal);
        this.toaster = ref.instance;
    }
}
