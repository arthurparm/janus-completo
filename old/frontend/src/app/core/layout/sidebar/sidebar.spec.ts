import {ComponentFixture, TestBed} from '@angular/core/testing';
import {signal} from '@angular/core';
import {RouterTestingModule} from '@angular/router/testing';

import {Sidebar} from './sidebar';
import {AuthService} from '../../auth/auth.service';
import {GlobalStateStore} from '../../state/global-state.store';

class MockGlobalStateStore {
  apiHealthy = signal<'unknown' | 'ok'>('ok');
  services = signal<any[]>([]);
  workers = signal<any[]>([]);
}

const authMock = {
  isAdmin: signal(false)
};

describe('Sidebar', () => {
  let component: Sidebar;
  let fixture: ComponentFixture<Sidebar>;

  beforeEach(async () => {
    authMock.isAdmin.set(false);

    await TestBed.configureTestingModule({
      imports: [Sidebar, RouterTestingModule],
      providers: [
        { provide: AuthService, useValue: authMock },
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

  it('renders only links backed by application routes for a regular user', () => {
    const links = Array.from(
      fixture.nativeElement.querySelectorAll<HTMLAnchorElement>('a.side-link')
    ).map((link) => link.getAttribute('href'));

    expect(links).toEqual([
      '/',
      '/conversations',
      '/observability',
      '/tools',
      '/knowledge-graph'
    ]);
  });

  it('adds the real autonomy administration route for administrators', () => {
    authMock.isAdmin.set(true);
    fixture.detectChanges();

    const links = Array.from(
      fixture.nativeElement.querySelectorAll<HTMLAnchorElement>('a.side-link')
    ).map((link) => link.getAttribute('href'));

    expect(links).toContain('/admin/autonomia');
  });
});
