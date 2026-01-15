import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UiButtonComponent } from '../../shared/components/ui/button/button.component';
import { UiIconComponent } from '../../shared/components/ui/icon/icon.component';
import { FormsModule } from '@angular/forms';
import { JanusApiService, DeploymentStageResponse } from '../../services/janus-api.service';

@Component({
    selector: 'app-ops',
    standalone: true,
    imports: [
        CommonModule,
        UiButtonComponent,
        UiIconComponent,
        FormsModule
    ],
    templateUrl: './ops.html',
    styleUrl: './ops.scss'
})
export class OpsComponent implements OnInit {
    // Deployment State
    activeModelId = 'gpt-4o-2024-05-13';
    stagingModelId = '';
    rolloutPercent = 0;
    isDeploying = false;
    deploymentLog: string[] = [];
    activeTab: 'deployment' | 'experiments' = 'deployment';

    // A/B Test State
    experiments = [
        { id: 101, name: 'Prompt Refinement v2', status: 'active', arms: ['Control', 'Few-Shot'], traffic: 50 },
        { id: 102, name: 'RAG Context Window', status: 'pending', arms: ['4k', '8k', '16k'], traffic: 0 }
    ];

    constructor(private api: JanusApiService) { }

    ngOnInit() {
        this.addLog('[OPS] LLMOps Console initialized.');
        this.addLog(`[PROD] Active Model: ${this.activeModelId}`);
    }

    // --- Deployment Actions ---

    stageModel() {
        if (!this.stagingModelId) return;
        this.isDeploying = true;
        this.addLog(`[STAGE] Initiating deployment for ${this.stagingModelId}...`);

        // Simulate API delay for UX
        setTimeout(() => {
            this.api.stageDeployment(this.stagingModelId, 0).subscribe({
                next: (res) => {
                    this.addLog(`[STAGE] Model ${res.model_id} loaded in sandbox.`);
                    this.addLog('[TEST] Running automated pre-checks...');
                    this.runPreChecks();
                },
                error: (err) => {
                    this.isDeploying = false;
                    this.addLog(`[ERROR] Staging failed: ${err.message}`);
                }
            });
        }, 1000);
    }

    runPreChecks() {
        setTimeout(() => {
            this.api.precheckDeployment(this.stagingModelId).subscribe({
                next: (res) => {
                    if (res.precheck_passed) {
                        this.addLog(`[PASS] Safety Checks passed. Bias Score: ${res.bias_score}`);
                        this.addLog('[READY] Model ready for promotion.');
                        this.rolloutPercent = 10; // Start with canary
                    } else {
                        this.addLog(`[FAIL] Safety warnings: ${res.safety_warnings}`);
                    }
                    this.isDeploying = false;
                }
            })
        }, 1500);
    }

    promote() {
        this.api.publishDeployment(this.stagingModelId).subscribe(() => {
            this.activeModelId = this.stagingModelId;
            this.stagingModelId = '';
            this.rolloutPercent = 0;
            this.addLog(`[PROD] Swap complete. ${this.activeModelId} is now live.`);
        });
    }

    rollback() {
        this.api.rollbackDeployment(this.activeModelId).subscribe(() => {
            this.addLog(`[ROLLBACK] Reverted to previous stable version.`);
        });
    }

    // --- Utils ---

    private addLog(msg: string) {
        const ts = new Date().toLocaleTimeString();
        this.deploymentLog.unshift(`[${ts}] ${msg}`);
    }
}
