import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';

import { KnowledgeWidget } from './knowledge-widget';

describe('KnowledgeWidget', () => {
  let component: KnowledgeWidget;
  let fixture: ComponentFixture<KnowledgeWidget>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KnowledgeWidget],
      providers: [provideHttpClient()]
    })
    .compileComponents();

    fixture = TestBed.createComponent(KnowledgeWidget);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
