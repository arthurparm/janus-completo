import {ComponentFixture, TestBed} from '@angular/core/testing';

import {Observability} from './observability';

describe('Observability', () => {
  let component: Observability;
  let fixture: ComponentFixture<Observability>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Observability]
    })
      .compileComponents();

    fixture = TestBed.createComponent(Observability);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
