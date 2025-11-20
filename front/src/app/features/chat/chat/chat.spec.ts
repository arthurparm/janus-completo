import { ComponentFixture, TestBed } from '@angular/core/testing'
import { of, throwError } from 'rxjs'
import { ChatComponent } from './chat'
import { JanusApiService } from '../../../services/janus-api.service'

class JanusApiServiceMock {
  listAttachments(conversation_id: string) { return of({ items: [] }) }
}

describe('ChatComponent', () => {
  let component: ChatComponent
  let fixture: ComponentFixture<ChatComponent>
  let api: JanusApiServiceMock

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChatComponent],
      providers: [{ provide: JanusApiService, useClass: JanusApiServiceMock }]
    }).compileComponents()

    fixture = TestBed.createComponent(ChatComponent)
    component = fixture.componentInstance
    api = TestBed.inject(JanusApiService) as any
    fixture.detectChanges()
  })

  it('should create', () => {
    expect(component).toBeTruthy()
  })

  it('should set error when conversationId invalid', () => {
    component.conversationId = '!!'
    component.loadAttachments()
    expect(component.attachmentsError).toBeTruthy()
  })

  it('should handle 404 on listAttachments', () => {
    component.conversationId = 'abc123'
    spyOn(api, 'listAttachments').and.returnValue(throwError(() => ({ status: 404 })))
    component.loadAttachments()
    expect(component.attachmentsLoading).toBeFalse()
    expect(component.attachmentsError).toBeTruthy()
  })
})
