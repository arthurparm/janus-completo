import { TestBed } from '@angular/core/testing'
import { LoginComponent } from './login'
import { AuthService } from '../../../core/auth/auth.service'
import { Router, provideRouter } from '@angular/router'
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
      imports: [LoginComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authSpy },
        // Router is already provided by provideRouter, but we want to spy on it.
        // We can override the specific methods or inject the router and spy on it.
        // Or keep the mock but it conflicts with provideRouter potentially.
        // Actually, provideRouter provides the Router service.
        // If we want to spy on it, we can get it from TestBed.
      ]
    })

    // We need to spy on the Router provided by provideRouter or override it.
    // Let's override the router instance for simplicity if needed, or better,
    // just spy on the injected router.
    const router = TestBed.inject(Router)
    vi.spyOn(router, 'navigate')

    // Update routerSpy to point to the actual router methods being spied on
    routerSpy.navigate = router.navigate as any

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
    // Check if navigate was called on the injected router
    expect(TestBed.inject(Router).navigate).toHaveBeenCalledWith(['/'])
  })
})
