from app.services.secret_memory_service import SecretMemoryService


def test_extract_secret_masks_and_classifies_value():
    svc = SecretMemoryService()

    result = svc.extract_secret("Minha senha do Wi-Fi é Abc12345")

    assert result is not None
    assert result["secret_type"] == "password"
    assert result["secret_scope"] == "network"
    assert result["secret_label"] == "senha do wi-fi"
    assert result["masked_value"].startswith("Ab")
    assert result["masked_value"].endswith("45")


def test_should_authorize_prompt_recall_requires_explicit_request():
    svc = SecretMemoryService()

    assert svc.should_authorize_prompt_recall("Qual é a minha senha do Wi-Fi?")
    assert not svc.should_authorize_prompt_recall("Guarde minha senha do Wi-Fi")
