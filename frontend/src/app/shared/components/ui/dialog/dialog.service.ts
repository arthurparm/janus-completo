import { Injectable, Injector } from '@angular/core';
import { Overlay, OverlayConfig } from '@angular/cdk/overlay';
import { ComponentPortal, ComponentType } from '@angular/cdk/portal';
import { UiDialogRef } from './dialog-ref';
import { UI_DIALOG_DATA } from './dialog.tokens';
import { UiDialogContainerComponent } from './dialog-container.component';

export interface DialogConfig<D = any> {
    data?: D;
    width?: string;
    disableClose?: boolean;
}

@Injectable({ providedIn: 'root' })
export class UiDialogService {
    constructor(private overlay: Overlay, private injector: Injector) { }

    open<T, D = any, R = any>(component: ComponentType<T>, config?: DialogConfig<D>): UiDialogRef<R> {
        const positionStrategy = this.overlay.position()
            .global()
            .centerHorizontally()
            .centerVertically();

        const overlayConfig = new OverlayConfig({
            hasBackdrop: true,
            backdropClass: ['bg-black/80', 'backdrop-blur-sm'],
            scrollStrategy: this.overlay.scrollStrategies.block(),
            positionStrategy,
            width: config?.width,
            panelClass: 'p-0' // Reset padding on the CDK pane itself
        });

        const overlayRef = this.overlay.create(overlayConfig);
        const dialogRef = new UiDialogRef<R>(overlayRef);

        // Create injector with data and ref
        const injector = Injector.create({
            parent: this.injector,
            providers: [
                { provide: UiDialogRef, useValue: dialogRef },
                { provide: UI_DIALOG_DATA, useValue: config?.data }
            ]
        });

        // Attach container
        const containerPortal = new ComponentPortal(UiDialogContainerComponent);
        const containerRef = overlayRef.attach(containerPortal);

        // Attach user component to container
        const userPortal = new ComponentPortal(component, null, injector);
        containerRef.instance.portalOutlet.attachComponentPortal(userPortal);

        // Close on backdrop click (if enabled)
        if (!config?.disableClose) {
            overlayRef.backdropClick().subscribe(() => dialogRef.close());
        }

        return dialogRef;
    }
}
