import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AutonomyWidget } from './autonomy-widget';

describe('AutonomyWidget', () => {
  let component: AutonomyWidget;
  let fixture: ComponentFixture<AutonomyWidget>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AutonomyWidget]
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
