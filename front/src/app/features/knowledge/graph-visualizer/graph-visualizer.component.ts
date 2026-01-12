import { Component, OnInit, OnDestroy, AfterViewInit, ElementRef, ViewChild, signal, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { GraphApiService, CytoscapeElement } from '../../../services/graph-api.service';
import cytoscape, { Core, NodeSingular } from 'cytoscape';

@Component({
  selector: 'app-graph-visualizer',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './graph-visualizer.component.html',
  styleUrl: './graph-visualizer.component.scss'
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
