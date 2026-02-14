import { TestBed } from '@angular/core/testing'
import { LoginComponent } from './login'
import { AuthService } from '../../../core/auth/auth.service'
import { Router, ActivatedRoute, RouterLink } from '@angular/router'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { of } from 'rxjs'

describe('LoginComponent', () => {
  let comp: LoginComponent
  let authSpy: any
  let routerSpy: any

  beforeEach(() => {
    authSpy = {
      loginWithPassword: vi.fn(),
      loginWithProvider: vi.fn()
    }
    routerSpy = {
      navigate: vi.fn(),
      navigateByUrl: vi.fn(),
      createUrlTree: vi.fn().mockReturnValue({ toString: () => '/' }),
      serializeUrl: vi.fn(),
      events: of(null) // Mock events observable for RouterLink
    }

    TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        { provide: AuthService, useValue: authSpy },
        { provide: Router, useValue: routerSpy },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: {
              queryParams: { returnUrl: '/' }
            }
          }
        }
      ]
    })
    const fixture = TestBed.createComponent(LoginComponent)
    comp = fixture.componentInstance
  })

  it('deve invalidar email incorreto', () => {
    comp.form.setValue({ email: 'x', password: '123456', remember: true })
    expect(comp.form.invalid).toBe(true)
  })

  it('deve alternar exibição de senha', () => {
    expect(comp.showPassword).toBe(false)
    comp.togglePassword()
    expect(comp.showPassword).toBe(true)
  })

  it('deve logar com email/senha válidos', async () => {
    comp.form.setValue({ email: 'a@b.com', password: '123456', remember: true })
    authSpy.loginWithPassword.mockResolvedValue(true)
    await comp.loginEmailPassword()
    expect(authSpy.loginWithPassword).toHaveBeenCalled()
    expect(routerSpy.navigate).toHaveBeenCalledWith(['/'])
  })
})
