def test_compute_winner_no_data():
    from app.services.ab_testing_service import ABTestingService
    svc = ABTestingService()
    res = svc.compute_winner(experiment_id=0)
    assert "winner" in res