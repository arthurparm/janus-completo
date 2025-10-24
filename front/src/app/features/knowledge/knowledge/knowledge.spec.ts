import {ComponentFixture, TestBed} from '@angular/core/testing';

import {Knowledge} from './knowledge';

describe('Knowledge', () => {
  let component: Knowledge;
  let fixture: ComponentFixture<Knowledge>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Knowledge]
    })
      .compileComponents();

    fixture = TestBed.createComponent(Knowledge);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
