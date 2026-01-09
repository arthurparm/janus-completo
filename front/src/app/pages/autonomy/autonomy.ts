import { Component, OnInit, OnDestroy, ChangeDetectorRef, ChangeDetectionStrategy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import { JanusApiService, AutonomyStatusResponse, AutonomyStartRequest } from '../../services/janus-api.service';
import { Observable } from 'rxjs';
import { MatTabsModule } from '@angular/material/tabs';
import { GoalsComponent } from '../goals/goals';
import { Database, ref, onValue, listVal, query, limitToLast } from '@angular/fire/database';

@Component({
    selector: 'app-autonomy',
    standalone: true,
    imports: [
        CommonModule,
        MatCardModule,
        MatButtonModule,
        MatIconModule,
        MatChipsModule,
        MatProgressBarModule,
        MatSelectModule,
        MatFormFieldModule,
        MatInputModule,
        FormsModule,
        MatTabsModule,
        GoalsComponent
    ],
    templateUrl: './autonomy.html',
    styleUrl: './autonomy.scss',
    changeDetection: ChangeDetectionStrategy.OnPush
})
export class AutonomyComponent implements OnInit, OnDestroy {
    status: AutonomyStatusResponse | null = null;
    rtStatus: { state: string, detail: string, timestamp: number } | null = null;
    isLoading = false;

    // Config Form
    selectedRisk: 'conservative' | 'balanced' | 'aggressive' = 'balanced';
    cycleInterval = 60;

    logs$: Observable<any[]>;

    private db = inject(Database);

    constructor(
        private janus: JanusApiService,
        private cdr: ChangeDetectorRef
    ) {
        const logsRef = query(ref(this.db, 'autonomy/logs'), limitToLast(50));
        this.logs$ = listVal(logsRef);
    }

    ngOnInit() {
        this.refreshStatus();

        // RTDB Status Listener
        const statusRef = ref(this.db, 'autonomy/status');
        onValue(statusRef, (snapshot) => {
            const val = snapshot.val();
            if (val) {
                this.rtStatus = val;
                this.cdr.markForCheck();
            }
        });
    }

    ngOnDestroy() {
    }

    refreshStatus() {
        this.janus.getAutonomyStatus().subscribe(s => {
            this.status = s;
            this.cdr.markForCheck();
        });
    }

    toggleAutonomy() {
        if (this.status?.active) {
            this.stop();
        } else {
            this.start();
        }
    }

    start() {
        this.isLoading = true;
        this.cdr.markForCheck();
        const req: AutonomyStartRequest = {
            interval_seconds: this.cycleInterval,
            risk_profile: this.selectedRisk,
            auto_confirm: true // For now, auto-confirm actions
        };

        this.janus.startAutonomy(req).subscribe({
            next: () => {
                this.isLoading = false;
                // Log removed
                this.refreshStatus();
                this.cdr.markForCheck();
            },
            error: (err) => {
                this.isLoading = false;
                console.error('Start error', err);
                this.cdr.markForCheck();
            }
        });
    }

    stop() {
        this.isLoading = true;
        this.cdr.markForCheck();
        this.janus.stopAutonomy().subscribe({
            next: () => {
                this.isLoading = false;
                // Log removed
                this.refreshStatus();
                this.cdr.markForCheck();
            },
            error: (err) => {
                this.isLoading = false;
                console.error('Stop error', err);
                this.cdr.markForCheck();
            }
        });
    }

    getRiskColor(): string {
        switch (this.status?.config?.['risk_profile'] || this.selectedRisk) {
            case 'conservative': return 'primary'; // Blue/Green
            case 'balanced': return 'accent'; // Purple/Yellow
            case 'aggressive': return 'warn'; // Red
            default: return '';
        }
    }

    /* addLog removed */
}
