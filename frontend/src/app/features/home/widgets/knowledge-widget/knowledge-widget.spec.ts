import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';

import { KnowledgeWidget } from './knowledge-widget';

describe('KnowledgeWidget', () => {
  let component: KnowledgeWidget;
  let fixture: ComponentFixture<KnowledgeWidget>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KnowledgeWidget, HttpClientTestingModule, RouterTestingModule]
    })
    .compileComponents();

    fixture = TestBed.createComponent(KnowledgeWidget);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('deve usar node_types quando labels nao vierem no payload de stats', () => {
    const labels = component.getTopLabels({
      total_nodes: 42,
      total_relationships: 7,
      node_types: [
        { type: 'RelationshipType', count: 36 },
        { type: 'Entity', count: 4 },
        { type: 'Experience', count: 2 },
      ],
      relationship_types: [{ type: 'RELATED_TO', count: 3 }],
    });

    expect(labels).toEqual([
      { label: 'RelationshipType', count: 36 },
      { label: 'Entity', count: 4 },
      { label: 'Experience', count: 2 },
    ]);
  });

  it('deve priorizar labels quando o backend enviar labels legados', () => {
    const labels = component.getTopLabels({
      total_nodes: 3,
      total_relationships: 1,
      labels: { Entity: 2, Experience: 1 },
      node_types: [{ type: 'RelationshipType', count: 36 }],
    });

    expect(labels).toEqual([
      { label: 'Entity', count: 2 },
      { label: 'Experience', count: 1 },
    ]);
  });
});
