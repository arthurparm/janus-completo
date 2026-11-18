from app.core.governance.data_classification import (
    DataClassification,
    classify_text,
    default_retention_decision,
)


def test_classify_text_detects_secret_patterns():
    assert classify_text("token: sk-abcdefghijklmnopqrstuvwxyz") == DataClassification.SECRET


def test_classify_text_detects_pii_patterns():
    assert classify_text("email user@example.com") == DataClassification.PII


def test_classify_text_defaults_internal():
    assert classify_text("hello world") == DataClassification.INTERNAL


def test_default_retention_decision_sets_expected_policy():
    pii = default_retention_decision(DataClassification.PII)
    assert pii.retention_policy == "days"
    assert pii.retention_days == 30

    internal = default_retention_decision(DataClassification.INTERNAL)
    assert internal.retention_policy == "days"
    assert internal.retention_days == 180

    secret = default_retention_decision(DataClassification.SECRET)
    assert secret.retention_policy == "persistent"
    assert secret.retention_days is None

