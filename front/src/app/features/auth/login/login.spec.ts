import { TestBed } from '@angular/core/testing'
import { LoginComponent } from './login'
import { AuthService } from '../../../core/auth/auth.service'
import { provideRouter, Router } from '@angular/router'
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
    // We can spy on the Router service itself if we inject it,
    // or use a mock provider.
    // If we use provideRouter([]), the Router is available.
    // We can verify calls by injecting Router and spying on it.

    TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: authSpy }
      ]
    })
    const fixture = TestBed.createComponent(LoginComponent)
    comp = fixture.componentInstance

    // Inject Router to spy on it
    const router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate');
    vi.spyOn(router, 'navigateByUrl');
    routerSpy = router as any; // Cast to use in expectations
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
