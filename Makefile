.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help install fmt lint typecheck test test-all cov run worker sandbox-image up down eval clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

install: ## Create venv and install with dev extras
	uv venv --python 3.12 .venv
	uv pip install -e ".[dev]"

fmt: ## Auto-format
	ruff format atlas tests
	ruff check --fix atlas tests

lint: ## Lint + format check
	ruff check atlas tests
	ruff format --check atlas tests

typecheck: ## Static type check
	mypy atlas

test: ## Run unit tests
	pytest -m "not integration and not eval"

test-all: ## Run every test (needs Postgres + Docker)
	pytest

cov: ## Unit tests with coverage report
	pytest -m "not integration and not eval" --cov=atlas --cov-report=term-missing --cov-report=html

run: ## Run the API locally with reload
	uvicorn atlas.main:app --reload --host 0.0.0.0 --port 8000

sandbox-image: ## Build the code-execution sandbox image
	docker build -f deploy/docker/Dockerfile.sandbox -t atlas-sandbox:latest .

up: ## Start the full stack with docker compose
	docker compose -f deploy/docker/docker-compose.yml up --build

down: ## Tear down the stack
	docker compose -f deploy/docker/docker-compose.yml down -v

eval: ## Run the benchmark suite
	atlas eval run --suite atlas/eval/suites/core.yaml

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml dist build
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
