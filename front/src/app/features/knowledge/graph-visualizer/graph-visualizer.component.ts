import { Component, OnInit, OnDestroy, AfterViewInit, ElementRef, ViewChild, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { GraphApiService, CytoscapeElement } from '../../../services/graph-api.service';
import cytoscape, { Core, NodeSingular } from 'cytoscape';

@Component({
    selector: 'app-graph-visualizer',
    standalone: true,
    imports: [CommonModule],
    template: `
    <div class="graph-container">
      <div class="graph-header">
        <h2>Knowledge Graph</h2>
        <div class="graph-controls">
          <button (click)="loadGraph()" [disabled]="loading()">
            {{ loading() ? 'Loading...' : 'Reload' }}
          </button>
          <button (click)="resetZoom()">Reset View</button>
          <select [(ngModel)]="selectedLayout" (change)="changeLayout()">
            <option value="cose">Force-Directed</option>
            <option value="circle">Circle</option>
            <option value="grid">Grid</option>
            <option value="breadthfirst">Hierarchical</option>
          </select>
        </div>
      </div>
      
      @if (error()) {
        <div class="error-message">{{ error() }}</div>
      }
      
      <div #cytoscapeContainer class="cytoscape-canvas"></div>
      
      @if (selectedNode()) {
        <div class="node-info-panel">
          <h3>{{ selectedNode()?.data('label') }}</h3>
          <p><strong>Type:</strong> {{ selectedNode()?.data('type') }}</p>
          <button (click)="expandNode(selectedNode()!)">Expand Neighbors</button>
          <button (click)="closePanel()">Close</button>
        </div>
      }
    </div>
  `,
    styles: [`
    .graph-container {
      width: 100%;
      height: 100vh;
      display: flex;
      flex-direction: column;
      background: var(--bg-primary, #1a1a2e);
      color: var(--text-primary, #eee);
    }

    .graph-header {
      padding: 1rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border-color, #333);
    }

    .graph-controls {
      display: flex;
      gap: 0.5rem;
    }

    .cytoscape-canvas {
      flex: 1;
      background: linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 100%);
    }

    .node-info-panel {
      position: absolute;
      right: 20px;
      top: 100px;
      width: 300px;
      padding: 1.5rem;
      background: rgba(26, 26, 46, 0.95);
      border: 1px solid #4a90e2;
      border-radius: 8px;
      box-shadow: 0 8px 32px rgba(74, 144, 226, 0.3);
    }

    .error-message {
      padding: 1rem;
      background: #ff4444;
      color: white;
      margin: 1rem;
      border-radius: 4px;
    }

    button {
      padding: 0.5rem 1rem;
      background: #4a90e2;
      color: white;
      border: none;
      border-radius: 4px;
      cursor: pointer;
      transition: background 0.2s;
    }

    button:hover:not(:disabled) {
      background: #357abd;
    }

    button:disabled {
      opacity: 0.5;
      cursor: not-allowed;
    }

    select {
      padding: 0.5rem;
      background: #2a2a3e;
      color: white;
      border: 1px solid #4a90e2;
      border-radius: 4px;
    }
  `]
})
export class GraphVisualizerComponent implements AfterViewInit, OnDestroy {
    @ViewChild('cytoscapeContainer', { static: false }) cytoscapeContainer!: ElementRef;

    private graphApi = inject(GraphApiService);
    private cy?: Core;

    loading = signal(false);
    error = signal<string | null>(null);
    selectedNode = signal<NodeSingular | null>(null);
    selectedLayout = 'cose';

    ngAfterViewInit() {
        this.initializeCytoscape();
        this.loadGraph();
    }

    ngOnDestroy() {
        this.cy?.destroy();
    }

    private initializeCytoscape() {
        this.cy = cytoscape({
            container: this.cytoscapeContainer.nativeElement,
            style: [
                {
                    selector: 'node',
                    style: {
                        'background-color': '#4a90e2',
                        'label': 'data(label)',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'color': '#fff',
                        'font-size': '12px',
                        'width': '60px',
                        'height': '60px'
                    }
                },
                {
                    selector: 'node.concept',
                    style: { 'background-color': '#4a90e2' }
                },
                {
                    selector: 'node.technology',
                    style: { 'background-color': '#e74c3c' }
                },
                {
                    selector: 'node.tool',
                    style: { 'background-color': '#f39c12' }
                },
                {
                    selector: 'node.pattern',
                    style: { 'background-color': '#9b59b6' }
                },
                {
                    selector: 'edge',
                    style: {
                        'width': 2,
                        'line-color': '#666',
                        'target-arrow-color': '#666',
                        'target-arrow-shape': 'triangle',
                        'curve-style': 'bezier',
                        'label': 'data(label)',
                        'font-size': '10px',
                        'color': '#999'
                    }
                }
            ]
        });

        // Node click handler
        this.cy.on('tap', 'node', (evt) => {
            const node = evt.target;
            this.selectedNode.set(node);
        });

        // Background click to deselect
        this.cy.on('tap', (evt) => {
            if (evt.target === this.cy) {
                this.selectedNode.set(null);
            }
        });
    }

    loadGraph() {
        this.loading.set(true);
        this.error.set(null);

        this.graphApi.getGraph({ limit: 100 }).subscribe({
            next: (elements) => {
                if (this.cy) {
                    this.cy.elements().remove();
                    this.cy.add(elements);
                    this.applyLayout();
                }
                this.loading.set(false);
            },
            error: (err) => {
                this.error.set('Failed to load graph: ' + err.message);
                this.loading.set(false);
            }
        });
    }

    expandNode(node: NodeSingular) {
        const nodeId = node.data('id');
        this.graphApi.getNeighbors(nodeId, 1).subscribe({
            next: (elements) => {
                if (this.cy) {
                    this.cy.add(elements);
                    this.applyLayout();
                }
            },
            error: (err) => {
                this.error.set('Failed to expand node: ' + err.message);
            }
        });
    }

    changeLayout() {
        this.applyLayout();
    }

    private applyLayout() {
        if (!this.cy) return;
        this.cy.layout({ name: this.selectedLayout as any } as any).run();
    }

    resetZoom() {
        this.cy?.fit();
    }

    closePanel() {
        this.selectedNode.set(null);
    }
}
