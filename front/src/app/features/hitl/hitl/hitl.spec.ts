import {ComponentFixture, TestBed} from '@angular/core/testing'
import {HitlComponent} from './hitl'
import {JanusApiService} from '../../../services/janus-api.service'
import {of} from 'rxjs'

describe('HitlComponent', () => {
  let fixture: ComponentFixture<HitlComponent>
  let component: HitlComponent
  let apiSpy: jasmine.SpyObj<JanusApiService>

  beforeEach(async () => {
    apiSpy = jasmine.createSpyObj('JanusApiService', ['listGraphQuarantine','promoteQuarantine','rejectQuarantine','registerSynonym','listAuditEvents'])
    await TestBed.configureTestingModule({
      imports: [HitlComponent],
      providers: [{ provide: JanusApiService, useValue: apiSpy }]
    }).compileComponents()
    fixture = TestBed.createComponent(HitlComponent)
    component = fixture.componentInstance
  })

  it('loads quarantine items on init', () => {
    apiSpy.listGraphQuarantine.and.returnValue(of([{ node_id: 1, type: 'RELATES_TO', from_name: 'A', to_name: 'B', reason: 'low_confidence'}]))
    fixture.detectChanges()
    expect(component.items.length).toBe(1)
  })

  it('promotes with justification', () => {
    apiSpy.listGraphQuarantine.and.returnValue(of([]))
    apiSpy.promoteQuarantine.and.returnValue(of({ status: 'promoted' }))
    fixture.detectChanges()
    const item = { node_id: 2 } as any
    component.openPromote(item)
    component.modal.justification = 'ok'
    component.confirmPromote()
    expect(apiSpy.promoteQuarantine).toHaveBeenCalledWith(2)
  })
})