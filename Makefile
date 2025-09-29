# Makefile for Janus 1.0 - common developer tasks
# Usage: make <target>

.PHONY: help run test lint format install-dev

PROJECT=janus
UVICORN?=uvicorn
PYTHON?=python
PIP?=pip
SRC=app

help:
	@echo "Available targets:"
	@echo "  make run          - Start the API with uvicorn (reload)"
	@echo "  make test         - Run tests (pytest if available)"
	@echo "  make lint         - Lint code using ruff/flake8/pyflakes or fallback syntax check"
	@echo "  make format       - Auto-format (ruff/black if available)"
	@echo "  make install-dev  - Install dev tools (ruff, black, pytest)"

run:
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

# Test: prefer pytest if installed; otherwise print a hint
test:
	@if command -v pytest >/dev/null 2>&1; then \
		echo "[test] Running pytest"; \
		pytest -q; \
	else \
		echo "[test] pytest not found. Install with: pip install pytest"; \
		echo "[test] Skipping tests."; \
	fi

# Lint: prefer ruff, then flake8, then pyflakes; fallback to syntax check
lint:
	@if command -v ruff >/dev/null 2>&1; then \
		echo "[lint] Running ruff"; \
		ruff check $(SRC); \
	elif command -v flake8 >/dev/null 2>&1; then \
		echo "[lint] Running flake8"; \
		flake8 $(SRC); \
	elif command -v pyflakes >/dev/null 2>&1; then \
		echo "[lint] Running pyflakes"; \
		pyflakes $(SRC); \
	else \
		echo "[lint] No linter found. Performing syntax check..."; \
		$(PYTHON) -m compileall -q $(SRC); \
	fi

# Format: try ruff, then black
format:
	@if command -v ruff >/dev/null 2>&1; then \
		echo "[format] Running ruff format"; \
		ruff format $(SRC); \
	elif command -v black >/dev/null 2>&1; then \
		echo "[format] Running black"; \
		black $(SRC); \
	else \
		echo "[format] No formatter found. Install ruff or black."; \
	fi

# Install common dev tools
install-dev:
	$(PIP) install --upgrade pip
	$(PIP) install ruff black pytest
