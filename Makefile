.PHONY: install dev lint test test-all build clean docker helmdocs format check

PYTHON ?= python3
PIP ?= pip

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install package (editable)
	$(PIP) install -e .

dev: ## Install with dev + server + otel dependencies
	$(PIP) install -e ".[dev,server,otel]"

lint: ## Run ruff lint + format check + mypy
	ruff check src/ tests/
	ruff format --check src/ tests/
	mypy src/ --ignore-missing-imports

format: ## Auto-fix lint and format
	ruff check --fix src/ tests/
	ruff format src/ tests/

test: ## Run test suite
	$(PYTHON) -m pytest tests/ -v --tb=short

test-all: ## Run tests with coverage
	$(PYTHON) -m pytest tests/ -v --tb=short --cov=picowatch --cov-report=term-missing

test-determinism: ## Verify determinism (10-run check)
	$(PYTHON) -m pytest tests/test_determinism.py -v

build: ## Build wheel and sdist
	$(PYTHON) -m build

clean: ## Remove build artifacts
	rm -rf build/ dist/ *.egg-info .mypy_cache/ .pytest_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

docker: ## Build Docker image
	docker build -t picowatch:latest .

docker-up: ## Start PicoWatch stack (docker-compose)
	docker-compose up -d

docker-down: ## Stop PicoWatch stack
	docker-compose down

sbom: ## Generate CycloneDX SBOM
	$(PYTHON) scripts/generate_sbom.py

check: lint test ## Run lint + test (CI equivalent)
