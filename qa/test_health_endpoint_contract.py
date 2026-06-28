from app.main import is_public_api_key_exempt_path


def test_public_api_key_exempts_root_health_endpoints():
    assert is_public_api_key_exempt_path("/health") is True
    assert is_public_api_key_exempt_path("/healthz") is True


def test_public_api_key_health_exemption_is_not_prefix_based():
    assert is_public_api_key_exempt_path("/health/services") is False
    assert is_public_api_key_exempt_path("/healthz/details") is False


def test_public_api_key_keeps_static_prefix_exemption():
    assert is_public_api_key_exempt_path("/static/app.js") is True
