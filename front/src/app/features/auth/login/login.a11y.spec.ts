import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { LoginComponent } from './login';
import { ActivatedRoute, Router } from '@angular/router'; // Import Router
import { AuthService } from '../../../core/auth/auth.service';
import { vi } from 'vitest';
import { of } from 'rxjs';

describe('LoginComponent A11y', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginComponent, HttpClientTestingModule],
      providers: [
        { provide: ActivatedRoute, useValue: { snapshot: { queryParams: {} } } },
        {
          provide: Router, // Provide Router mock
          useValue: {
            createUrlTree: vi.fn().mockReturnValue({ toString: () => '/' }),
            navigate: vi.fn(),
            serializeUrl: vi.fn(),
            events: of(null)
          }
        },
        {
          provide: AuthService,
          useValue: {
            loginWithPassword: vi.fn(),
            loginWithProvider: vi.fn()
          }
        }
      ]
    })
    .compileComponents();

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('deve ter labels associados aos inputs', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    // Ensure change detection runs to update DOM
    fixture.detectChanges();

    const inputs = compiled.querySelectorAll('input');
    inputs.forEach(input => {
      const id = input.getAttribute('id');
      if (id) {
          const label = compiled.querySelector(`label[for="${id}"]`);
          expect(label).toBeTruthy();
      }
    });
  });
});
