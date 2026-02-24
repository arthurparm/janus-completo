import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { API_BASE_URL } from './api.config';
import { map } from 'rxjs/operators';

export interface GraphNode {
    id: string;
    label: string;
    type: string; // Concept, Technology, Tool, Pattern, etc.
    properties: Record<string, unknown>;
}

export interface GraphEdge {
    id: string;
    source: string;
    target: string;
    label: string;
    properties: Record<string, unknown>;
}

export interface GraphData {
    nodes: GraphNode[];
    edges: GraphEdge[];
}

// Cytoscape format
export interface CytoscapeElement {
    data: {
        id: string;
        label?: string;
        source?: string;
        target?: string;
        type?: string;
        [key: string]: unknown;
    };
    classes?: string;
}

@Injectable({ providedIn: 'root' })
export class GraphApiService {
    private http = inject(HttpClient);

    /**
     * Fetch full graph or subgraph from Neo4j
     */
    getGraph(params?: { limit?: number; labels?: string[] }): Observable<CytoscapeElement[]> {
        const queryParams: Record<string, string> = {};
        if (params?.limit) queryParams['limit'] = String(params.limit);
        if (params?.labels) queryParams['labels'] = params.labels.join(',');

        return this.http
            .get<GraphData>(`${API_BASE_URL}/v1/knowledge/graph`, { params: queryParams })
            .pipe(map((data) => this.transformToCytoscape(data)));
    }

    /**
     * Get neighbors of a specific node
     */
    getNeighbors(nodeId: string, depth: number = 1): Observable<CytoscapeElement[]> {
        return this.http
            .get<GraphData>(`${API_BASE_URL}/v1/knowledge/concepts/${nodeId}/neighbors`, {
                params: { depth: String(depth) },
            })
            .pipe(map((data) => this.transformToCytoscape(data)));
    }

    /**
     * Transform backend graph format to Cytoscape format
     */
    private transformToCytoscape(graph: GraphData): CytoscapeElement[] {
        const elements: CytoscapeElement[] = [];

        // Nodes
        graph.nodes.forEach((node) => {
            elements.push({
                data: {
                    id: node.id,
                    label: node.label,
                    type: node.type,
                    ...node.properties,
                },
                classes: node.type.toLowerCase(),
            });
        });

        // Edges
        graph.edges.forEach((edge) => {
            elements.push({
                data: {
                    id: edge.id,
                    source: edge.source,
                    target: edge.target,
                    label: edge.label,
                    ...edge.properties,
                },
            });
        });

        return elements;
    }
}
