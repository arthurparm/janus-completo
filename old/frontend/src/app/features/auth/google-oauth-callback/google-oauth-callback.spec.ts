import { TestBed } from '@angular/core/testing'
import { ActivatedRoute, convertToParamMap, Router } from '@angular/router'
import { of, throwError } from 'rxjs'
import { vi } from 'vitest'

import { BackendApiService } from '../../../services/backend-api.service'
import { GoogleOAuthCallbackComponent } from './google-oauth-callback'

describe('GoogleOAuthCallbackComponent', () => {
  const navigate = vi.fn().mockResolvedValue(true)
  const callback = vi.fn()

  function configure(params: Record<string, string>) {
    navigate.mockClear()
    callback.mockClear()
    TestBed.configureTestingModule({
      imports: [GoogleOAuthCallbackComponent],
      providers: [
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap(params) } },
        },
        { provide: Router, useValue: { navigate } },
        {
          provide: BackendApiService,
          useValue: { productivity: { googleOAuthCallback: callback } },
        },
      ],
    })
  }

  it('troca código e state pelo vínculo local e remove os parâmetros da URL', async () => {
    callback.mockReturnValue(of({ status: 'ok' }))
    configure({ code: 'authorization-code', state: 'opaque-state' })

    const component = TestBed.createComponent(GoogleOAuthCallbackComponent).componentInstance
    await component.ngOnInit()

    expect(callback).toHaveBeenCalledTimes(1)
    expect(callback).toHaveBeenCalledWith('authorization-code', 'opaque-state')
    expect(navigate).toHaveBeenCalledWith(['/tools'], {
      queryParams: { google_oauth: 'connected' },
      replaceUrl: true,
    })
  })

  it('retorna erro controlado sem chamar o backend quando o provedor nega acesso', async () => {
    callback.mockReturnValue(throwError(() => new Error('must not run')))
    configure({ error: 'access_denied' })

    const component = TestBed.createComponent(GoogleOAuthCallbackComponent).componentInstance
    await component.ngOnInit()

    expect(callback).not.toHaveBeenCalled()
    expect(navigate).toHaveBeenCalledWith(['/tools'], {
      queryParams: {
        google_oauth: 'error',
        message: 'O Google não autorizou a integração solicitada.',
      },
      replaceUrl: true,
    })
  })
})
