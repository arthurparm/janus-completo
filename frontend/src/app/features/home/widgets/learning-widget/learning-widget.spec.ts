import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { RouterTestingModule } from '@angular/router/testing';

import { LearningWidget } from './learning-widget';

describe('LearningWidget', () => {
  let component: LearningWidget;
  let fixture: ComponentFixture<LearningWidget>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LearningWidget, HttpClientTestingModule, RouterTestingModule]
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
