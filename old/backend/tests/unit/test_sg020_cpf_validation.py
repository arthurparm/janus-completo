from app.core.security.cpf import is_valid_cpf, normalize_cpf


def test_normalize_cpf_keeps_only_digits():
    assert normalize_cpf("503.024.278-30") == "50302427830"


def test_is_valid_cpf_accepts_known_valid_values():
    assert is_valid_cpf("503.024.278-30") is True
    assert is_valid_cpf("52998224725") is True


def test_is_valid_cpf_rejects_invalid_values():
    assert is_valid_cpf(None) is False
    assert is_valid_cpf("") is False
    assert is_valid_cpf("123") is False
    assert is_valid_cpf("111.111.111-11") is False
    assert is_valid_cpf("50302427831") is False
