import { ComponentFixture, TestBed } from '@angular/core/testing'
import { HitlComponent } from './hitl'
import { JanusApiService } from '../../../services/janus-api.service'
import { of } from 'rxjs'
import { vi } from 'vitest'

describe('HitlComponent', () => {
  let fixture: ComponentFixture<HitlComponent>
  let component: HitlComponent
  let apiSpy: {
    listGraphQuarantine: ReturnType<typeof vi.fn>
    promoteQuarantine: ReturnType<typeof vi.fn>
    rejectQuarantine: ReturnType<typeof vi.fn>
    registerSynonym: ReturnType<typeof vi.fn>
    listAuditEvents: ReturnType<typeof vi.fn>
  }

  beforeEach(async () => {
    apiSpy = {
      listGraphQuarantine: vi.fn(),
      promoteQuarantine: vi.fn(),
      rejectQuarantine: vi.fn(),
      registerSynonym: vi.fn(),
      listAuditEvents: vi.fn()
    }
    await TestBed.configureTestingModule({
      imports: [HitlComponent],
      providers: [{ provide: JanusApiService, useValue: apiSpy }]
    }).compileComponents()
    fixture = TestBed.createComponent(HitlComponent)
    component = fixture.componentInstance
  })

  it('loads quarantine items on init', () => {
    apiSpy.listGraphQuarantine.mockReturnValue(
      of([{ node_id: 1, type: 'RELATES_TO', from_name: 'A', to_name: 'B', reason: 'low_confidence' }])
    )
    fixture.detectChanges()
    expect(component.items.length).toBe(1)
  })

  it('promotes with justification', () => {
    apiSpy.listGraphQuarantine.mockReturnValue(of([]))
    apiSpy.promoteQuarantine.mockReturnValue(of({ status: 'promoted' }))
    fixture.detectChanges()
    const item = { node_id: 2 } as any
    component.openPromote(item)
    component.modal.justification = 'ok'
    component.confirmPromote()
    expect(apiSpy.promoteQuarantine).toHaveBeenCalledWith(2)
  })
})
