import {ComponentFixture, TestBed} from '@angular/core/testing';
import {RouterTestingModule} from '@angular/router/testing';
import {provideHttpClient} from '@angular/common/http';
import {of} from 'rxjs';
import {AuthService} from '../../auth/auth.service';
import {Database} from '@angular/fire/database';

import {Header} from './header';

describe('Header', () => {
  let component: Header;
  let fixture: ComponentFixture<Header>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Header, RouterTestingModule],
      providers: [
        provideHttpClient(),
        { provide: AuthService, useValue: { isAuthenticated$: of(false), logout: () => {} } },
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
});
