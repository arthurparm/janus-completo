import { TestBed } from '@angular/core/testing'
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing'
import { AuthService } from './auth.service'
import { SupabaseService } from './supabase.service'
import { API_BASE_URL, AUTH_TOKEN_KEY } from '../../services/api.config'

describe('AuthService', () => {
  let svc: AuthService
  let http: HttpTestingController
  const supaMock: any = {
    signInWithPassword: jasmine.createSpy('signInWithPassword').and.resolveTo({}),
    signInWithProvider: jasmine.createSpy('signInWithProvider').and.resolveTo({}),
    getSession: jasmine.createSpy('getSession').and.resolveTo({ access_token: 'supabase.jwt' })
  }

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [{ provide: SupabaseService, useValue: supaMock }]
    })
    svc = TestBed.inject(AuthService)
    http = TestBed.inject(HttpTestingController)
  })

  it('deve realizar exchange e salvar token Janus', async () => {
    const p = svc.loginWithPassword('a@b.com', '123456', true)
    const req = http.expectOne(`${API_BASE_URL}/v1/auth/supabase/exchange`)
    req.flush({ token: 'janus.jwt' })
    const ok = await p
    expect(ok).toBeTrue()
    expect(localStorage.getItem(AUTH_TOKEN_KEY)).toBe('janus.jwt')
  })
})
