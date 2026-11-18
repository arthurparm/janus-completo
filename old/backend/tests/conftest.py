"""Defaults seguros para coleta de testes a partir da raiz do monorepo."""

import os

_TEST_ENV_DEFAULTS = {
    "TESTING": "true",
    "APP_ENV": "test",
    "SECURITY_PROFILE": "test",
    "SECRET_KEY": "test-secret-key-32-bytes-minimum-security!!",
    "POSTGRES_HOST": "127.0.0.1",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "janus_test",
    "POSTGRES_USER": "test",
    "POSTGRES_PASSWORD": "test",
    "NEO4J_PASSWORD": "test",
}

for _name, _value in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_name, _value)
