import { TestBed } from '@angular/core/testing'
import { LoginComponent } from './login'
import { AuthService } from '../../../core/auth/auth.service'
import { Router } from '@angular/router'

describe('LoginComponent', () => {
  let comp: LoginComponent
  let authSpy: jasmine.SpyObj<AuthService>
  let routerSpy: jasmine.SpyObj<Router>

  beforeEach(() => {
    authSpy = jasmine.createSpyObj('AuthService', ['loginWithPassword', 'loginWithProvider'])
    routerSpy = jasmine.createSpyObj('Router', ['navigateByUrl'])
    TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        { provide: AuthService, useValue: authSpy },
        { provide: Router, useValue: routerSpy },
      ]
    })
    const fixture = TestBed.createComponent(LoginComponent)
    comp = fixture.componentInstance
  })

  it('deve invalidar email incorreto', () => {
    comp.form.setValue({ email: 'x', password: '123456', remember: true })
    expect(comp.form.invalid).toBeTrue()
  })

  it('deve alternar exibição de senha', () => {
    expect(comp.showPassword).toBeFalse()
    comp.togglePassword()
    expect(comp.showPassword).toBeTrue()
  })

  it('deve logar com email/senha válidos', async () => {
    comp.form.setValue({ email: 'a@b.com', password: '123456', remember: true })
    authSpy.loginWithPassword.and.resolveTo(true)
    await comp.loginEmailPassword()
    expect(authSpy.loginWithPassword).toHaveBeenCalled()
    expect(routerSpy.navigateByUrl).toHaveBeenCalledWith('/')
  })
})