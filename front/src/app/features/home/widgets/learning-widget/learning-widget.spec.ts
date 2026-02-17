import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';

import { LearningWidget } from './learning-widget';

describe('LearningWidget', () => {
  let component: LearningWidget;
  let fixture: ComponentFixture<LearningWidget>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LearningWidget],
      providers: [provideHttpClient()]
    })
    .compileComponents();

    fixture = TestBed.createComponent(LearningWidget);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
