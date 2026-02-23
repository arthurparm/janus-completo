from app.core.llm import pricing


def test_register_usage_updates_provider_and_tenant_spend(monkeypatch):
    monkeypatch.setattr(pricing, "get_redis_usage_tracker", lambda: None)
    pricing._provider_spend_usd.clear()
    pricing._provider_spend_usd.update({"openai": 0.0})
    pricing._tenant_user_spend_usd.clear()
    pricing._tenant_project_spend_usd.clear()
    pricing.register_usage("openai", "user-1", "project-1", 1.5)
    assert pricing._provider_spend_usd["openai"] == 1.5
    assert pricing._tenant_user_spend_usd["user-1"]["usd"] == 1.5
    assert pricing._tenant_project_spend_usd["project-1"]["usd"] == 1.5

