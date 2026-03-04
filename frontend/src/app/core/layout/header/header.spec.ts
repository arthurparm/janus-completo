import {ComponentFixture, TestBed} from '@angular/core/testing';
import {RouterTestingModule} from '@angular/router/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import {of} from 'rxjs';
import { vi } from 'vitest';
import {AuthService} from '../../auth/auth.service';
import {Database} from '@angular/fire/database';
import { Router } from '@angular/router';

import {Header} from './header';

describe('Header', () => {
  let component: Header;
  let fixture: ComponentFixture<Header>;
  const authMock = {
    isAuthenticated$: of(false),
    logout: vi.fn().mockResolvedValue(undefined),
  };

  beforeEach(async () => {
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

  it('should logout and navigate to login', async () => {
    const router = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);

    await component.logout();

    expect(authMock.logout).toHaveBeenCalled();
    expect(navigateSpy).toHaveBeenCalledWith(['/login']);
  });
});
