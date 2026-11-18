def test_compute_winner_no_data():
    from app.services.ab_testing_service import ABTestingService
    
    class DummySession:
        def query(self, *args, **kwargs):
            class _Q:
                def filter(self, *a, **kw): return self
                def all(self): return []
            return _Q()
        def close(self): pass

    class DummyRepo:
        def __init__(self):
            self._session = None
        def _get_session(self):
            return DummySession()

    svc = ABTestingService(repo=DummyRepo())
    res = svc.compute_winner(experiment_id=0)
    assert "winner" in res