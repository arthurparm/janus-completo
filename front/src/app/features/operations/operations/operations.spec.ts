import {ComponentFixture, TestBed} from '@angular/core/testing';

import {Operations} from './operations';

describe('Operations', () => {
  let component: Operations;
  let fixture: ComponentFixture<Operations>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Operations]
    })
      .compileComponents();

    fixture = TestBed.createComponent(Operations);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
