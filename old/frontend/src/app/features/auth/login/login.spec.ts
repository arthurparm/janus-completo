import { TestBed } from '@angular/core/testing'
import { ActivatedRoute } from '@angular/router'
import { convertToParamMap } from '@angular/router'
import { BehaviorSubject } from 'rxjs'
import { vi } from 'vitest'
import { AuthService } from '../../../core/auth/auth.service'
import { LoginComponent } from './login'

describe('LoginComponent OIDC', () => {
  it('redireciona exclusivamente pelo fluxo OIDC com o returnUrl validado', async () => {
    const beginLogin = vi.fn().mockResolvedValue(undefined)
    const params = new BehaviorSubject(convertToParamMap({ returnUrl: '/conversations' }))
    TestBed.configureTestingModule({
      imports: [LoginComponent],
      providers: [
        { provide: AuthService, useValue: { beginLogin } },
        {
          provide: ActivatedRoute,
          useValue: {
            queryParamMap: params.asObservable(),
            snapshot: { queryParamMap: convertToParamMap({ returnUrl: '/conversations' }) }
          }
        }
      ]
    })

    const component = TestBed.createComponent(LoginComponent).componentInstance
    await component.beginLogin()

    expect(beginLogin).toHaveBeenCalledWith('/conversations')
  })
})
