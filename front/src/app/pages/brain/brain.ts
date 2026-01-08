import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatTabsModule } from '@angular/material/tabs';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatFormFieldModule } from '@angular/material/form-field';
import { FormsModule } from '@angular/forms';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { JanusApiService, KnowledgeStats, EntityRelationshipItem, ReflexionLesson } from '../../services/janus-api.service';
import { MemoryComponent } from '../memory/memory';

@Component({
    selector: 'app-brain',
    standalone: true,
    imports: [
        CommonModule,
        MatTabsModule,
        MatCardModule,
        MatIconModule,
        MatButtonModule,
        MatInputModule,
        MatFormFieldModule,
        FormsModule,
        MatChipsModule,
        MatProgressBarModule,
        MemoryComponent
    ],
    templateUrl: './brain.html',
    styleUrl: './brain.scss'
})
export class BrainComponent implements OnInit {
    private api = inject(JanusApiService);

    // Tabs
    selectedTab = 0;

    // Graph State
    graphStats: KnowledgeStats | null = null;
    searchEntity = '';
    currentEntity = '';
    relationships: EntityRelationshipItem[] = [];
    loadingGraph = false;

    // Reflexion State
    lessons: ReflexionLesson[] = [];
    metaReport: Record<string, unknown> | null = null;
    loadingReflexion = false;

    ngOnInit() {
        this.loadGraphStats();
        this.loadReflexion();
    }

    // --- Knowledge Graph ---

    loadGraphStats() {
        this.api.getKnowledgeStats().subscribe({
            next: (stats) => this.graphStats = stats,
            error: (err) => console.error('Failed to load graph stats', err)
        });
    }

    exploreEntity() {
        if (!this.searchEntity.trim()) return;
        this.loadingGraph = true;
        this.currentEntity = this.searchEntity;

        this.api.getEntityRelationships(this.searchEntity).subscribe({
            next: (res) => {
                this.relationships = res.results || [];
                this.loadingGraph = false;
            },
            error: (err) => {
                console.error('Graph exploration failed', err);
                this.loadingGraph = false;
                this.relationships = [];
            }
        });
    }

    // --- Reflexion ---

    loadReflexion() {
        this.loadingReflexion = true;
        this.api.getReflexionSummary(15).subscribe({
            next: (res) => {
                this.lessons = res.lessons || [];
                this.metaReport = res.meta_report || null;
                this.loadingReflexion = false;
            },
            error: (err) => {
                console.error('Reflexion load failed', err);
                this.loadingReflexion = false;
            }
        });
    }

    getScoreColor(score?: number): string {
        if (!score) return 'accent';
        if (score > 0.8) return 'primary'; // Greenish in theme usually
        if (score < 0.4) return 'warn';
        return 'accent';
    }
}
