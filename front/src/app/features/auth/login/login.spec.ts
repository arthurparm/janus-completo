import { TestBed } from '@angular/core/testing'
import { LoginComponent } from './login'
import { AuthService } from '../../../core/auth/auth.service'
import { Router } from '@angular/router'
import { RouterTestingModule } from '@angular/router/testing'
import { vi } from 'vitest'

describe('LoginComponent', () => {
  let comp: LoginComponent
  let authSpy: { loginWithPassword: ReturnType<typeof vi.fn>; loginWithProvider: ReturnType<typeof vi.fn> }
  let routerSpy: { navigate: ReturnType<typeof vi.fn>; navigateByUrl: ReturnType<typeof vi.fn> }

  beforeEach(() => {
    authSpy = {
      loginWithPassword: vi.fn(),
      loginWithProvider: vi.fn()
    }
    routerSpy = {
      navigate: vi.fn(),
      navigateByUrl: vi.fn()
    }
    TestBed.configureTestingModule({
      imports: [LoginComponent, RouterTestingModule],
      providers: [
        { provide: AuthService, useValue: authSpy },
        // Router is provided by RouterTestingModule, but if we want to spy on it:
        // We can override the provider, or just rely on RouterTestingModule and spy on the injected instance.
        // But the existing code provides a mock for Router.
        // Providing Router manually usually overrides RouterTestingModule's provider.
        // However, ActivatedRoute is NOT provided by `{ provide: Router ... }`.
        // RouterTestingModule provides ActivatedRoute.
        { provide: Router, useValue: routerSpy },
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
