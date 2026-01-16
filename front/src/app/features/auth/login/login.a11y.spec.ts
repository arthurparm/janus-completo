import { TestBed } from '@angular/core/testing'
import { Router } from '@angular/router'
import { AuthService } from '../../../core/auth/auth.service'
import { LoginComponent } from './login'

describe('LoginComponent A11y', () => {
  it('deve ter labels associados aos inputs', () => {
    const fixture = TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        { provide: AuthService, useValue: { loginWithPassword: () => Promise.resolve(true), loginWithProvider: () => Promise.resolve(true) } },
        { provide: Router, useValue: { navigate: () => Promise.resolve(true), navigateByUrl: () => Promise.resolve(true) } }
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
