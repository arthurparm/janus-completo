import { Component, OnInit, OnDestroy, ChangeDetectorRef, ChangeDetectionStrategy, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import {
    JanusApiService,
    AutonomyStatusResponse,
    AutonomyStartRequest,
    AutonomyPlanResponse,
    AutonomyPolicyUpdateRequest
} from '../../services/janus-api.service';
import { GoalsComponent } from '../goals/goals';
import { UiIconComponent } from '../../shared/components/ui/icon/icon.component';
import { UiBadgeComponent } from '../../shared/components/ui/ui-badge/ui-badge.component';
import { UiSpinnerComponent } from '../../shared/components/ui/spinner/spinner.component';
import { Database, ref, onValue, listVal, query, limitToLast } from '@angular/fire/database';

@Component({
    selector: 'app-autonomy',
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        GoalsComponent,
        UiIconComponent,
        UiBadgeComponent,
        UiSpinnerComponent
    ],
    templateUrl: './autonomy.html',
    styleUrl: './autonomy.scss',
    changeDetection: ChangeDetectionStrategy.OnPush
})
export class AutonomyComponent implements OnInit, OnDestroy {
    selectedTab = 0;
    status: AutonomyStatusResponse | null = null;
    rtStatus: { state: string, detail: string, timestamp: number } | null = null;
    isLoading = false;
    plan: AutonomyPlanResponse | null = null;
    planLoading = false;
    planError = '';
    statusError = '';
    policyLoading = false;
    policyMessage = '';
    policyError = '';
    private policyDirty = false;

    // Config Form
    selectedRisk: 'conservative' | 'balanced' | 'aggressive' = 'balanced';
    cycleInterval = 60;
    autoConfirm = true;
    allowlistText = '';
    blocklistText = '';
    maxActionsPerCycle: number | null = null;
    maxSecondsPerCycle: number | null = null;

    logs$: Observable<any[]>;

    private db = inject(Database);
    private stopStatusListener?: () => void;

    constructor(
        private janus: JanusApiService,
        private cdr: ChangeDetectorRef
    ) {
        const logsRef = query(ref(this.db, 'autonomy/logs'), limitToLast(50));
        this.logs$ = listVal(logsRef);
    }

    ngOnInit() {
        this.refreshStatus();
        this.refreshPlan();

        // RTDB Status Listener
        const statusRef = ref(this.db, 'autonomy/status');
        this.stopStatusListener = onValue(statusRef, (snapshot) => {
            const val = snapshot.val();
            if (val) {
                this.rtStatus = val;
                this.cdr.markForCheck();
            }
        });
    }

    ngOnDestroy() {
        if (this.stopStatusListener) {
            this.stopStatusListener();
            this.stopStatusListener = undefined;
        }
    }

    refreshStatus(): void {
        this.statusError = '';
        this.janus.getAutonomyStatus().subscribe({
            next: (status) => {
                this.status = status;
                this.syncPolicyFromStatus(status, false);
                this.cdr.markForCheck();
            },
            error: (err) => {
                console.error('Status error', err);
                this.statusError = 'Falha ao carregar o status.';
                this.cdr.markForCheck();
            }
        });
    }

    refreshPlan(): void {
        this.planLoading = true;
        this.planError = '';
        this.janus.getAutonomyPlan().subscribe({
            next: (plan) => {
                this.plan = plan;
                this.planLoading = false;
                this.cdr.markForCheck();
            },
            error: (err) => {
                console.error('Plan error', err);
                this.planLoading = false;
                this.planError = 'Falha ao carregar o plano.';
                this.cdr.markForCheck();
            }
        });
    }

    markPolicyDirty(): void {
        this.policyDirty = true;
        this.policyMessage = '';
        this.policyError = '';
    }

    resetPolicyForm(): void {
        this.policyDirty = false;
        this.policyMessage = '';
        this.policyError = '';
        this.syncPolicyFromStatus(this.status, true);
        this.cdr.markForCheck();
    }

    updatePolicy(): void {
        if (this.status?.active) {
            this.policyError = 'Pare a autonomia para salvar a politica.';
            this.cdr.markForCheck();
            return;
        }
        this.policyLoading = true;
        this.policyMessage = '';
        this.policyError = '';
        const payload = this.buildPolicyRequest();
        this.janus.updateAutonomyPolicy(payload).subscribe({
            next: () => {
                this.policyLoading = false;
                this.policyMessage = 'Politica atualizada.';
                this.policyDirty = false;
                this.refreshStatus();
                this.cdr.markForCheck();
            },
            error: (err) => {
                console.error('Policy update error', err);
                this.policyLoading = false;
                this.policyError = 'Falha ao atualizar a politica.';
                this.cdr.markForCheck();
            }
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
        const allowlist = this.parseTextList(this.allowlistText);
        const blocklist = this.parseTextList(this.blocklistText);
        const req: AutonomyStartRequest = {
            interval_seconds: this.cycleInterval,
            risk_profile: this.selectedRisk,
            auto_confirm: this.autoConfirm
        };
        if (allowlist.length) {
            req.allowlist = allowlist;
        }
        if (blocklist.length) {
            req.blocklist = blocklist;
        }
        if (typeof this.maxActionsPerCycle === 'number') {
            req.max_actions_per_cycle = this.maxActionsPerCycle;
        }
        if (typeof this.maxSecondsPerCycle === 'number') {
            req.max_seconds_per_cycle = this.maxSecondsPerCycle;
        }

        this.janus.startAutonomy(req).subscribe({
            next: () => {
                this.isLoading = false;
                // Log removed
                this.refreshStatus();
                this.refreshPlan();
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
                this.refreshPlan();
                this.cdr.markForCheck();
            },
            error: (err) => {
                this.isLoading = false;
                console.error('Stop error', err);
                this.cdr.markForCheck();
            }
        });
    }

    private buildPolicyRequest(): AutonomyPolicyUpdateRequest {
        const allowlist = this.parseTextList(this.allowlistText);
        const blocklist = this.parseTextList(this.blocklistText);
        const payload: AutonomyPolicyUpdateRequest = {
            risk_profile: this.selectedRisk,
            auto_confirm: this.autoConfirm,
            allowlist,
            blocklist
        };
        if (typeof this.maxActionsPerCycle === 'number' && Number.isFinite(this.maxActionsPerCycle)) {
            payload.max_actions_per_cycle = this.maxActionsPerCycle;
        }
        if (typeof this.maxSecondsPerCycle === 'number' && Number.isFinite(this.maxSecondsPerCycle)) {
            payload.max_seconds_per_cycle = this.maxSecondsPerCycle;
        }
        return payload;
    }

    private syncPolicyFromStatus(status: AutonomyStatusResponse | null, force: boolean): void {
        if (!status || !status.config) {
            if (force) {
                this.selectedRisk = 'balanced';
                this.cycleInterval = 60;
                this.autoConfirm = true;
                this.allowlistText = '';
                this.blocklistText = '';
                this.maxActionsPerCycle = null;
                this.maxSecondsPerCycle = null;
            }
            return;
        }
        if (this.policyDirty && !force) {
            return;
        }
        const config = status.config || {};
        const risk = this.normalizeRiskValue(config['risk_profile']);
        if (risk) {
            this.selectedRisk = risk;
        }
        const interval = this.normalizeNumber(config['interval_seconds'], null);
        if (interval != null) {
            this.cycleInterval = interval;
        }
        this.autoConfirm = this.normalizeBoolean(config['auto_confirm'], this.autoConfirm);
        this.allowlistText = this.formatList(config['allowlist']);
        this.blocklistText = this.formatList(config['blocklist']);
        this.maxActionsPerCycle = this.normalizeNumber(config['max_actions_per_cycle'], this.maxActionsPerCycle);
        this.maxSecondsPerCycle = this.normalizeNumber(config['max_seconds_per_cycle'], this.maxSecondsPerCycle);
    }

    private normalizeRiskValue(value: unknown): 'conservative' | 'balanced' | 'aggressive' | null {
        if (!value) {
            return null;
        }
        const candidate = String(value).toLowerCase();
        if (candidate === 'conservative' || candidate === 'balanced' || candidate === 'aggressive') {
            return candidate as 'conservative' | 'balanced' | 'aggressive';
        }
        return null;
    }

    private normalizeNumber(value: unknown, fallback: number | null): number | null {
        if (typeof value === 'number' && Number.isFinite(value)) {
            return value;
        }
        if (typeof value === 'string' && value.trim().length > 0) {
            const parsed = Number(value);
            return Number.isFinite(parsed) ? parsed : fallback;
        }
        return fallback;
    }

    private normalizeBoolean(value: unknown, fallback: boolean): boolean {
        if (typeof value === 'boolean') {
            return value;
        }
        if (typeof value === 'string') {
            if (value.toLowerCase() === 'true') return true;
            if (value.toLowerCase() === 'false') return false;
        }
        if (typeof value === 'number') {
            return value > 0;
        }
        return fallback;
    }

    private formatList(value: unknown): string {
        if (!value) return '';
        if (Array.isArray(value)) {
            return value.map((item) => String(item)).join(', ');
        }
        if (typeof value === 'string') {
            return value;
        }
        return '';
    }

    private parseTextList(text: string): string[] {
        return text
            .split(/[,\\n]+/g)
            .map((item) => item.trim())
            .filter((item) => item.length > 0);
    }

    getEffectiveRisk(): 'conservative' | 'balanced' | 'aggressive' {
        const risk = this.normalizeRiskValue(this.status?.config?.['risk_profile']);
        return risk || this.selectedRisk;
    }

    getRiskLabel(risk: string): string {
        switch (risk) {
            case 'conservative':
                return 'Conservador';
            case 'balanced':
                return 'Balanceado';
            case 'aggressive':
                return 'Agressivo';
            default:
                return 'Indefinido';
        }
    }

    getRiskBadge(risk: string): 'neutral' | 'success' | 'warning' | 'error' {
        switch (risk) {
            case 'conservative':
                return 'success';
            case 'balanced':
                return 'warning';
            case 'aggressive':
                return 'error';
            default:
                return 'neutral';
        }
    }

    getEffectiveInterval(): number {
        const interval = this.normalizeNumber(this.status?.config?.['interval_seconds'], null);
        return interval != null ? interval : this.cycleInterval;
    }

    getAutoConfirmLabel(): string {
        const flag = this.normalizeBoolean(this.status?.config?.['auto_confirm'], this.autoConfirm);
        return flag ? 'Ativo' : 'Inativo';
    }

    formatLastCycle(timestamp?: number | null): string {
        return this.formatTimestamp(timestamp);
    }

    formatPlanArgs(args?: Record<string, unknown>): string {
        if (!args || Object.keys(args).length === 0) {
            return 'Sem parametros';
        }
        const serialized = JSON.stringify(args);
        return serialized.length > 140 ? `${serialized.slice(0, 137)}...` : serialized;
    }

    private formatTimestamp(timestamp?: number | null): string {
        if (!timestamp) return 'n/a';
        const value = timestamp > 1_000_000_000_000 ? timestamp : timestamp * 1000;
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return 'n/a';
        return date.toLocaleString('pt-BR');
    }

    getRtStateLabel(state: string | null | undefined): string {
        if (!state) return 'DESCONHECIDO';
        switch (state) {
            case 'thinking': {
                return 'PENSANDO';
            }
            case 'executing': {
                return 'EXECUTANDO';
            }
            default:
                return state.toUpperCase();
        }
    }

    getToolNameFromLog(message: string | null | undefined): string | null {
        if (!message) {
            return null;
        }
        const prefix = 'Executando: ';
        if (!message.startsWith(prefix)) {
            return null;
        }
        return message.slice(prefix.length).trim();
    }

    getDisplayLogs(raw: any[] | null | undefined): { timestamp: number; level: string; message: string; count: number }[] {
        if (!raw || !Array.isArray(raw)) {
            return [];
        }
        const sorted = [...raw].sort((a, b) => {
            const ta = typeof a.timestamp === 'number' ? a.timestamp : 0;
            const tb = typeof b.timestamp === 'number' ? b.timestamp : 0;
            return ta - tb;
        });
        const acc: { timestamp: number; level: string; message: string; count: number }[] = [];
        for (const item of sorted) {
            const timestamp = typeof item.timestamp === 'number' ? item.timestamp : 0;
            const level = String(item.level || 'info');
            const message = String(item.message || '');
            const last = acc[acc.length - 1];
            if (last && last.message === message && last.level === level) {
                last.count += 1;
                last.timestamp = timestamp || last.timestamp;
            } else {
                acc.push({
                    timestamp,
                    level,
                    message,
                    count: 1
                });
            }
        }
        return acc.reverse();
    }
}
