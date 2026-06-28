import { TestBed } from '@angular/core/testing';
import { HttpClientTestingModule, HttpTestingController } from '@angular/common/http/testing';

import { ObservabilityApiService } from './observability-api-service';

describe('ObservabilityApiService (contract)', () => {
  let http: HttpTestingController;
  let svc: ObservabilityApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
    });
    http = TestBed.inject(HttpTestingController);
    svc = TestBed.inject(ObservabilityApiService);
  });

  afterEach(() => {
    http.verify();
  });

  it('listPendingActions monta querystring sem user_id cliente-controlado', () => {
    svc
      .listPendingActions({
        include_sql: true,
        include_graph: false,
        pending_status: 'pending',
        limit: 25,
      })
      .subscribe();

    const req = http.expectOne(
      '/api/v1/pending_actions/?include_graph=false&include_sql=true&pending_status=pending&limit=25'
    );
    expect(req.request.method).toBe('GET');
    req.flush([]);
  });

  it('getPendingActionsLegacyResidue usa endpoint administrativo tipado do observability', () => {
    svc.getPendingActionsLegacyResidue(5).subscribe();

    const req = http.expectOne('/api/v1/observability/pending-actions/legacy-residue?limit=5');
    expect(req.request.method).toBe('GET');
    req.flush({
      total_without_owner: 1,
      pending_without_owner: 1,
      sample_limit: 5,
      legacy_runtime_fallback_enabled: false,
      message:
        'Operational legacy is extinct. Historical pending_actions without persisted owner remain blocked as administrative backlog until controlled sanitation; new ownerless records are rejected.',
      items: [],
    });
  });

  it('approvePendingAction usa endpoint SQL quando action_id estiver presente', () => {
    svc.approvePendingAction({ action_id: 42, status: 'pending' }).subscribe();

    const req = http.expectOne('/api/v1/pending_actions/action/42/approve');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({});
    req.flush({ action_id: 42, status: 'approved' });
  });

  it('approvePendingAction usa endpoint LangGraph quando houver apenas thread_id', () => {
    svc.approvePendingAction({ thread_id: 'thread-1', status: 'pending' }).subscribe();

    const req = http.expectOne('/api/v1/pending_actions/thread-1/approve');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({});
    req.flush({ thread_id: 'thread-1', status: 'approved' });
  });

  it('rejectPendingAction usa endpoint SQL quando action_id estiver presente', () => {
    svc.rejectPendingAction({ action_id: 7, status: 'pending' }).subscribe();

    const req = http.expectOne('/api/v1/pending_actions/action/7/reject');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({});
    req.flush({ action_id: 7, status: 'rejected' });
  });

  it('rejectPendingAction usa endpoint LangGraph quando houver apenas thread_id', () => {
    svc.rejectPendingAction({ thread_id: 'thread-9', status: 'pending' }).subscribe();

    const req = http.expectOne('/api/v1/pending_actions/thread-9/reject');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({});
    req.flush({ thread_id: 'thread-9', status: 'rejected' });
  });
});
