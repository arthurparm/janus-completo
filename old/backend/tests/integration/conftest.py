import sys
from unittest.mock import MagicMock


def _install_mock_module(name):
    if name not in sys.modules:
        sys.modules[name] = MagicMock()


# Only mock packages that are truly not installed in the test environment.
# These are imported at module level by kernel.py and its dependencies.
_missing_packages = [
    "aio_pika",
    "aio_pika.abc",
    "aiormq",
    "aiormq.exceptions",
]

for pkg in _missing_packages:
    _install_mock_module(pkg)
