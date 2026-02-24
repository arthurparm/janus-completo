import {ComponentFixture, TestBed} from '@angular/core/testing';
import {signal} from '@angular/core';
import {RouterTestingModule} from '@angular/router/testing';

import {Sidebar} from './sidebar';
import {GlobalStateStore} from '../../state/global-state.store';

class MockGlobalStateStore {
  apiHealthy = signal<'unknown' | 'ok'>('ok');
  services = signal<any[]>([]);
  workers = signal<any[]>([]);
}

describe('Sidebar', () => {
  let component: Sidebar;
  let fixture: ComponentFixture<Sidebar>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Sidebar, RouterTestingModule],
      providers: [
        { provide: GlobalStateStore, useClass: MockGlobalStateStore }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(Sidebar);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
