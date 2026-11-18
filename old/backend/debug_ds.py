from app.config import settings
from app.core.llm.factory import _validate_deepseek_key
from app.core.llm.resilience import _circuit_closed
from app.core.llm.pricing import _budget_allows

ds_key = getattr(settings.DEEPSEEK_API_KEY, 'get_secret_value', lambda: None)()
print('=== DeepSeek Debug ===')
print('Key valid:', _validate_deepseek_key(ds_key))
print('Circuit closed:', _circuit_closed('deepseek'))
print('Budget allows:', _budget_allows('deepseek'))
print('DEEPSEEK_MODELS:', settings.DEEPSEEK_MODELS)

print()
print('=== Checking if candidates map works ===')
role_candidates = settings.LLM_CLOUD_MODEL_CANDIDATES.get('orchestrator', [])
print('Role candidates for orchestrator:', role_candidates)

role_candidates_map = {}
for spec in role_candidates:
    try:
        provider_key, model_name = spec.split(':', 1)
        role_candidates_map.setdefault(provider_key.strip(), set()).add(model_name.strip())
    except Exception as e:
        print('Error parsing', spec, ':', e)
print('role_candidates_map:', role_candidates_map)
print('Models for deepseek:', list(role_candidates_map.get('deepseek', set())))
