import { TestBed } from '@angular/core/testing'
import { RouterTestingModule } from '@angular/router/testing'
import { AuthService } from '../../../core/auth/auth.service'
import { LoginComponent } from './login'

describe('LoginComponent A11y', () => {
  it('deve expor uma ação OIDC identificável e operável por teclado', () => {
    const fixture = TestBed.configureTestingModule({
      imports: [LoginComponent, RouterTestingModule],
      providers: [
        {
          provide: AuthService,
          useValue: {
            beginLogin: () => Promise.resolve(),
          }
        }
      ]
    }).createComponent(LoginComponent)
    fixture.detectChanges()
    const el: HTMLElement = fixture.nativeElement
    const oidcButton = el.querySelector<HTMLButtonElement>('button.glass-button.primary')
    expect(oidcButton).toBeTruthy()
    expect(oidcButton?.type).toBe('button')
    expect(oidcButton?.textContent).toContain('PROVEDOR DE IDENTIDADE')
  })
})
