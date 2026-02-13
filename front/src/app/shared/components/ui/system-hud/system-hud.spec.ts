import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SystemHud } from './system-hud';

describe('SystemHud', () => {
  let component: SystemHud;
  let fixture: ComponentFixture<SystemHud>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SystemHud]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SystemHud);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
