def test_budget_usage_and_priority():
    from app.services.resource_manager import (
        can_schedule_training,
        record_training_usage,
        get_user_gpu_usage,
        compute_job_priority,
    )

    uid = "u1"
    # Default budget not set: can schedule
    assert can_schedule_training(uid) is True
    record_training_usage(uid, 1.0)
    usage = get_user_gpu_usage(uid)
    assert usage["used"] >= 1.0
    assert compute_job_priority(uid, "classifier") in (2, 3, 5)
