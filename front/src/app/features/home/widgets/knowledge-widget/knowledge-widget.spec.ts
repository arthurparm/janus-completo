import { ComponentFixture, TestBed } from '@angular/core/testing';

import { KnowledgeWidget } from './knowledge-widget';

describe('KnowledgeWidget', () => {
  let component: KnowledgeWidget;
  let fixture: ComponentFixture<KnowledgeWidget>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [KnowledgeWidget]
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
