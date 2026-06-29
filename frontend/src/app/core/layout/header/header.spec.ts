import {ComponentFixture, TestBed} from '@angular/core/testing';
import {RouterTestingModule} from '@angular/router/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import {BehaviorSubject} from 'rxjs';
import { vi } from 'vitest';
import {AuthService} from '../../auth/auth.service';
import {Database} from '@angular/fire/database';
import { Router } from '@angular/router';

import {Header} from './header';

describe('Header', () => {
  let component: Header;
  let fixture: ComponentFixture<Header>;
  let isAuthenticated$: BehaviorSubject<boolean>;
  let isVisitor$: BehaviorSubject<boolean>;
  const authMock = {
    get isAuthenticated$() {
      return isAuthenticated$;
    },
    get isVisitor$() {
      return isVisitor$;
    },
    logout: vi.fn().mockResolvedValue(undefined),
  };

  beforeEach(async () => {
    isAuthenticated$ = new BehaviorSubject<boolean>(false);
    isVisitor$ = new BehaviorSubject<boolean>(false);
    authMock.logout.mockClear();
    await TestBed.configureTestingModule({
      imports: [Header, RouterTestingModule, HttpClientTestingModule],
      providers: [
        { provide: AuthService, useValue: authMock },
        { provide: Database, useValue: {} }
      ]
    })
      .compileComponents();

    fixture = TestBed.createComponent(Header);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should keep the system health HUD available in the header', () => {
    const hud = fixture.nativeElement.querySelector('app-system-hud');

    expect(hud).toBeTruthy();
  });

  it('deve sinalizar modo visitante quando a sessao for visitante', () => {
    isAuthenticated$.next(true);
    isVisitor$.next(true);
    fixture.detectChanges();

    const badge = fixture.nativeElement.querySelector('.visitor-badge');
    expect(badge?.textContent).toContain('Visitante');
  });

  it('should logout and navigate to login', async () => {
    const router = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    await component.logout();

    expect(authMock.logout).toHaveBeenCalled();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
  });
});
