import { TestBed } from '@angular/core/testing'
import { RouterTestingModule } from '@angular/router/testing'
import { AuthService } from '../../../core/auth/auth.service'
import { LoginComponent } from './login'

describe('LoginComponent A11y', () => {
  it('deve ter labels associados aos inputs', () => {
    const fixture = TestBed.configureTestingModule({
      imports: [LoginComponent, RouterTestingModule],
      providers: [
        { provide: AuthService, useValue: { loginWithPassword: () => Promise.resolve(true), loginWithProvider: () => Promise.resolve(true) } }
      ]
    }).createComponent(LoginComponent)
    fixture.detectChanges()
    const el: HTMLElement = fixture.nativeElement
    const emailLabel = el.querySelector('label[for="email"]')
    const emailInput = el.querySelector('#email')
    const passwordLabel = el.querySelector('label[for="password"]')
    const passwordInput = el.querySelector('#password')
    expect(emailLabel).toBeTruthy()
    expect(emailInput).toBeTruthy()
    expect(passwordLabel).toBeTruthy()
    expect(passwordInput).toBeTruthy()
  })
})
