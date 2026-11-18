import {ComponentFixture, TestBed} from '@angular/core/testing';
import {RouterTestingModule} from '@angular/router/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import {BehaviorSubject} from 'rxjs';
import { vi } from 'vitest';
import {AuthService} from '../../auth/auth.service';
import { Router } from '@angular/router';

import {Header} from './header';

describe('Header', () => {
  let component: Header;
  let fixture: ComponentFixture<Header>;
  let isAuthenticated$: BehaviorSubject<boolean>;
  const authMock = {
    get isAuthenticated$() {
      return isAuthenticated$;
    },
    logout: vi.fn().mockResolvedValue(undefined),
  };

  beforeEach(async () => {
    isAuthenticated$ = new BehaviorSubject<boolean>(false);
    authMock.logout.mockClear();
    await TestBed.configureTestingModule({
      imports: [Header, RouterTestingModule, HttpClientTestingModule],
      providers: [
        { provide: AuthService, useValue: authMock }
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

  it('should logout and navigate to login', async () => {
    const router = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    await component.logout();

    expect(authMock.logout).toHaveBeenCalled();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
  });
});
