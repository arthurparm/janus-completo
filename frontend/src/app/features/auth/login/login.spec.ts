import { TestBed } from '@angular/core/testing'
import { LoginComponent } from './login'
import { AuthService } from '../../../core/auth/auth.service'
import { Router } from '@angular/router'
import { RouterTestingModule } from '@angular/router/testing'
import { vi } from 'vitest'

describe('LoginComponent', () => {
  let comp: LoginComponent
  let authSpy: {
    loginWithPassword: ReturnType<typeof vi.fn>
    loginWithProvider: ReturnType<typeof vi.fn>
    requestPasswordReset: ReturnType<typeof vi.fn>
    resetPassword: ReturnType<typeof vi.fn>
  }
  let router: Router

  beforeEach(() => {
    authSpy = {
      loginWithPassword: vi.fn(),
      loginWithProvider: vi.fn(),
      requestPasswordReset: vi.fn(),
      resetPassword: vi.fn()
    }

    TestBed.configureTestingModule({
      imports: [LoginComponent, RouterTestingModule],
      providers: [{ provide: AuthService, useValue: authSpy }]
    })

    const fixture = TestBed.createComponent(LoginComponent)
    comp = fixture.componentInstance
    router = TestBed.inject(Router)
  })

  it('deve invalidar email incorreto', () => {
    comp.form.setValue({ email: 'x', password: '123456', remember: true })
    expect(comp.form.invalid).toBe(true)
  })

  it('deve alternar exibicao de senha', () => {
    expect(comp.showPassword).toBe(false)
    comp.togglePassword()
    expect(comp.showPassword).toBe(true)
  })

  it('deve logar com email/senha validos', async () => {
    comp.form.setValue({ email: 'a@b.com', password: '123456', remember: true })
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true)
    authSpy.loginWithPassword.mockResolvedValue({ ok: true })

    await comp.loginEmailPassword()

    expect(authSpy.loginWithPassword).toHaveBeenCalledWith('a@b.com', '123456', true)
    expect(navigateSpy).toHaveBeenCalledWith(['/'])
  })

  it('deve exibir hint de recuperacao em erro 401', async () => {
    comp.form.setValue({ email: 'a@b.com', password: 'bad-pass', remember: true })
    authSpy.loginWithPassword.mockResolvedValue({
      ok: false,
      statusCode: 401,
      reason: 'invalid_credentials',
      error: 'Email/usuario ou senha invalidos.'
    })

    await comp.loginEmailPassword()

    expect(comp.error).toContain('invalidos')
    expect(comp.showRecoveryHint).toBe(true)
    expect(comp.notice).toContain('Recuperar acesso')
  })
})
