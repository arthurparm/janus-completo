import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';

import { AutonomyWidget } from './autonomy-widget';

describe('AutonomyWidget', () => {
  let component: AutonomyWidget;
  let fixture: ComponentFixture<AutonomyWidget>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AutonomyWidget],
      providers: [provideHttpClient()]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AutonomyWidget);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
