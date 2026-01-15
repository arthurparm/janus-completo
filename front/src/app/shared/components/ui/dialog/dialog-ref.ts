import { OverlayRef } from '@angular/cdk/overlay';
import { Subject, Observable } from 'rxjs';

export class UiDialogRef<R = any> {
    private _afterClosed = new Subject<R | undefined>();

    constructor(private overlayRef: OverlayRef) { }

    close(result?: R): void {
        this.overlayRef.dispose();
        this._afterClosed.next(result);
        this._afterClosed.complete();
    }

    afterClosed(): Observable<R | undefined> {
        return this._afterClosed.asObservable();
    }
}
