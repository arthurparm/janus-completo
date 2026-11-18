import { ComponentFixture, TestBed } from '@angular/core/testing'
import { HttpClientTestingModule } from '@angular/common/http/testing'
import { of, throwError } from 'rxjs'
import { RouterTestingModule } from '@angular/router/testing'
import { vi } from 'vitest'

import { KnowledgeGraphComponent } from './knowledge-graph'
import { BackendApiService } from '../../services/backend-api.service'

describe('KnowledgeGraphComponent', () => {
  let fixture: ComponentFixture<KnowledgeGraphComponent>
  let component: KnowledgeGraphComponent

  const apiStub = {
    knowledge: {
      getKnowledgeStats: vi.fn().mockReturnValue(
        of({
          total_nodes: 42,
          total_relationships: 7,
          node_types: [
            { type: 'Entity', count: 4 },
            { type: 'RelationshipType', count: 36 },
          ],
          relationship_types: [{ type: 'RELATED_TO', count: 3 }],
        })
      ),
      getKnowledgeNodeTypes: vi.fn().mockReturnValue(
        of({ types: ['Entity', 'RelationshipType'] })
      ),
    },
  }

  beforeEach(async () => {
    apiStub.knowledge.getKnowledgeStats.mockReset()
    apiStub.knowledge.getKnowledgeNodeTypes.mockReset()
    apiStub.knowledge.getKnowledgeStats.mockReturnValue(
      of({
        total_nodes: 42,
        total_relationships: 7,
        node_types: [
          { type: 'Entity', count: 4 },
          { type: 'RelationshipType', count: 36 },
        ],
        relationship_types: [{ type: 'RELATED_TO', count: 3 }],
      })
    )
    apiStub.knowledge.getKnowledgeNodeTypes.mockReturnValue(of({ types: ['Entity', 'RelationshipType'] }))

    await TestBed.configureTestingModule({
      imports: [KnowledgeGraphComponent, RouterTestingModule, HttpClientTestingModule],
      providers: [{ provide: BackendApiService, useValue: apiStub }],
    }).compileComponents()

    fixture = TestBed.createComponent(KnowledgeGraphComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  })

  it('deve carregar resumo do grafo pelos endpoints reais', () => {
    expect(apiStub.knowledge.getKnowledgeStats).toHaveBeenCalled()
    expect(apiStub.knowledge.getKnowledgeNodeTypes).toHaveBeenCalled()
    expect(component.loading()).toBe(false)
    expect(component.stats()?.total_nodes).toBe(42)
    expect(component.nodeTypeMetrics()).toEqual([
      { type: 'RelationshipType', count: 36 },
      { type: 'Entity', count: 4 },
    ])
    expect(component.relationshipTypeMetrics()).toEqual([{ type: 'RELATED_TO', count: 3 }])
  })

  it('deve mostrar erro quando stats falhar', () => {
    apiStub.knowledge.getKnowledgeStats.mockReturnValue(throwError(() => new Error('stats unavailable')))
    apiStub.knowledge.getKnowledgeNodeTypes.mockReturnValue(of({ types: ['Entity'] }))

    component.loadGraphSummary()

    expect(component.loading()).toBe(false)
    expect(component.error()).toBe('Nao foi possivel carregar o grafo de conhecimento.')
    expect(component.nodeTypeMetrics()).toEqual([{ type: 'Entity', count: 0 }])
  })
})
