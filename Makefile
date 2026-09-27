# Developer entry points. Every target is also what CI runs.
.DEFAULT_GOAL := help
PYTHON ?= python
export SECRET_KEY ?= test-only-secret-key-not-for-production-use

.PHONY: help install lint format typecheck security audit test test-fast cov migrate migrate-check run bench seed clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install the package with dev + test extras
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -e ".[dev,postgres,redis]"
	pre-commit install || true

lint: ## Ruff lint (no changes)
	ruff check .
	ruff format --check .

format: ## Auto-fix lint + format
	ruff check --fix .
	ruff format .

typecheck: ## mypy
	mypy

security: ## Bandit (medium+ severity fails)
	bandit -c pyproject.toml -r task_manager_pro -ll

audit: ## Known-vulnerability scan of installed dependencies
	pip-audit --desc on --skip-editable

test: ## Full test-suite with coverage gate
	pytest --cov --cov-report=term-missing --cov-report=xml

test-fast: ## Test-suite without coverage
	pytest -q

cov: test ## Alias

migrate: ## Apply migrations to $$DATABASE_URL
	alembic upgrade head

migrate-check: ## Fail if models and migrations disagree
	alembic upgrade head && alembic check

run: ## Start the API with auto-reload
	uvicorn task_manager_pro.api.main:app --reload --host 127.0.0.1 --port 8000

seed: ## Populate a database with a reproducible synthetic dataset
	$(PYTHON) scripts/seed_data.py --users 5 --tasks-per-user 40 --seed 42

bench: ## Latency benchmark against a running server (BASE_URL=http://localhost:8000)
	$(PYTHON) benchmarks/bench_api.py --base-url $${BASE_URL:-http://localhost:8000}

clean: ## Remove caches and build artefacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache .hypothesis htmlcov coverage.xml dist build *.egg-info
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
