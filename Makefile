# nvision Project Makefile
# Development automation and task management

.PHONY: help install install-dev test test-unit test-integration test-e2e
.PHONY: lint format type-check security-check quality-check
.PHONY: clean clean-cache clean-build clean-test clean-all
.PHONY: docker-build docker-run docker-test docker-clean
.PHONY: docs docs-serve pre-commit setup-dev
.PHONY: db-start db-stop db-reset db-migrate
.PHONY: run run-dev run-prod coverage-report

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3.9
PIP := pip
PYTEST := pytest
BLACK := black
ISORT := isort
FLAKE8 := flake8
MYPY := mypy
BANDIT := bandit
DOCKER := docker
DOCKER_COMPOSE := docker-compose

# Project directories
SRC_DIR := src
TEST_DIR := tests
DOCS_DIR := docs
BUILD_DIR := build
DIST_DIR := dist

# Docker configuration
DOCKER_IMAGE := nvision
DOCKER_TAG := latest
COMPOSE_FILE := docker-compose.yml
COMPOSE_DEV_FILE := docker-compose.dev.yml

help: ## Show this help message
	@echo "nvision Project - Development Commands"
	@echo "======================================"
	@echo ""
	@echo "Setup Commands:"
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo "  setup-dev        Complete development environment setup"
	@echo ""
	@echo "Code Quality:"
	@echo "  format           Format code with black and isort"
	@echo "  lint             Run linting with flake8"
	@echo "  type-check       Run type checking with mypy"
	@echo "  security-check   Run security scanning with bandit"
	@echo "  quality-check    Run all quality checks"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-e2e         Run end-to-end tests only"
	@echo "  coverage-report  Generate coverage report"
	@echo ""
	@echo "Development:"
	@echo "  run              Run application in development mode"
	@echo "  run-dev          Run with auto-reload"
	@echo "  run-prod         Run in production mode"
	@echo ""
	@echo "Database:"
	@echo "  db-start         Start database services"
	@echo "  db-stop          Stop database services"
	@echo "  db-reset         Reset database data"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build     Build Docker image"
	@echo "  docker-run       Run application in Docker"
	@echo "  docker-test      Run tests in Docker"
	@echo "  docker-clean     Clean Docker resources"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean            Clean cache and temporary files"
	@echo "  clean-all        Clean everything including build artifacts"
	@echo "  pre-commit       Run pre-commit hooks"
	@echo ""

# Setup and Installation
install: ## Install production dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-dev: ## Install development dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev,test]"
	pre-commit install

setup-dev: install-dev ## Complete development environment setup
	@echo "Setting up development environment..."
	pre-commit install --hook-type commit-msg
	@echo "Creating .env file from template..."
	@if [ ! -f .env ]; then cp .env.example .env; fi
	@echo "Development environment setup complete!"

# Code Quality
format: ## Format code with black and isort
	@echo "Formatting code..."
	$(BLACK) $(SRC_DIR) $(TEST_DIR)
	$(ISORT) $(SRC_DIR) $(TEST_DIR)
	@echo "Code formatting complete!"

lint: ## Run linting with flake8
	@echo "Running linting..."
	$(FLAKE8) $(SRC_DIR) $(TEST_DIR)
	@echo "Linting complete!"

type-check: ## Run type checking with mypy
	@echo "Running type checking..."
	$(MYPY) $(SRC_DIR) --ignore-missing-imports
	@echo "Type checking complete!"

security-check: ## Run security scanning with bandit
	@echo "Running security scan..."
	$(BANDIT) -r $(SRC_DIR) -f json -o bandit-report.json || true
	$(BANDIT) -r $(SRC_DIR)
	@echo "Security scan complete!"

quality-check: format lint type-check security-check ## Run all quality checks
	@echo "All quality checks complete!"

# Testing
test: ## Run all tests
	@echo "Running all tests..."
	$(PYTEST) -v --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=html

test-unit: ## Run unit tests only
	@echo "Running unit tests..."
	$(PYTEST) -v -m "unit" --cov=$(SRC_DIR) --cov-report=term-missing

test-integration: ## Run integration tests only
	@echo "Running integration tests..."
	$(PYTEST) -v -m "integration" --cov=$(SRC_DIR) --cov-report=term-missing

test-e2e: ## Run end-to-end tests only
	@echo "Running end-to-end tests..."
	$(PYTEST) -v -m "e2e" --cov=$(SRC_DIR) --cov-report=term-missing

coverage-report: ## Generate coverage report
	@echo "Generating coverage report..."
	$(PYTEST) --cov=$(SRC_DIR) --cov-report=html --cov-report=xml
	@echo "Coverage report generated in htmlcov/"

# Development
run: ## Run application in development mode
	@echo "Starting nvision application..."
	$(PYTHON) -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000

run-dev: ## Run with auto-reload
	@echo "Starting nvision application with auto-reload..."
	$(PYTHON) -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

run-prod: ## Run in production mode
	@echo "Starting nvision application in production mode..."
	$(PYTHON) -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# Database Management
db-start: ## Start database services
	@echo "Starting database services..."
	$(DOCKER_COMPOSE) up -d neo4j chroma

db-stop: ## Stop database services
	@echo "Stopping database services..."
	$(DOCKER_COMPOSE) stop neo4j chroma

db-reset: ## Reset database data
	@echo "Resetting database data..."
	$(DOCKER_COMPOSE) down -v
	$(DOCKER_COMPOSE) up -d neo4j chroma
	@echo "Waiting for services to be ready..."
	sleep 30

# Docker Commands
docker-build: ## Build Docker image
	@echo "Building Docker image..."
	$(DOCKER) build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

docker-run: docker-build ## Run application in Docker
	@echo "Running application in Docker..."
	$(DOCKER_COMPOSE) up --build app

docker-test: ## Run tests in Docker
	@echo "Running tests in Docker..."
	$(DOCKER_COMPOSE) -f $(COMPOSE_FILE) run --rm app pytest

docker-clean: ## Clean Docker resources
	@echo "Cleaning Docker resources..."
	$(DOCKER_COMPOSE) down -v --remove-orphans
	$(DOCKER) system prune -f

# Maintenance
clean-cache: ## Clean Python cache files
	@echo "Cleaning Python cache..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +

clean-build: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	rm -rf $(BUILD_DIR)
	rm -rf $(DIST_DIR)
	rm -rf *.egg-info

clean-test: ## Clean test artifacts
	@echo "Cleaning test artifacts..."
	rm -rf htmlcov/
	rm -f coverage.xml
	rm -f .coverage
	rm -f bandit-report.json

clean: clean-cache clean-test ## Clean cache and temporary files
	@echo "Cleaning complete!"

clean-all: clean clean-build ## Clean everything including build artifacts
	@echo "Deep cleaning complete!"

# Pre-commit
pre-commit: ## Run pre-commit hooks
	@echo "Running pre-commit hooks..."
	pre-commit run --all-files

# Documentation
docs: ## Build documentation
	@echo "Building documentation..."
	@if [ -d "$(DOCS_DIR)" ]; then \
		cd $(DOCS_DIR) && make html; \
	else \
		echo "Documentation directory not found"; \
	fi

docs-serve: docs ## Serve documentation locally
	@echo "Serving documentation..."
	@if [ -d "$(DOCS_DIR)/_build/html" ]; then \
		cd $(DOCS_DIR)/_build/html && $(PYTHON) -m http.server 8080; \
	else \
		echo "Documentation not built. Run 'make docs' first."; \
	fi

# Development workflow shortcuts
dev-setup: setup-dev db-start ## Complete development setup
	@echo "Development environment ready!"

dev-test: quality-check test ## Run quality checks and tests
	@echo "Development testing complete!"

dev-reset: clean-all db-reset install-dev ## Reset development environment
	@echo "Development environment reset complete!"

# CI/CD simulation
ci-test: ## Simulate CI testing pipeline
	@echo "Simulating CI pipeline..."
	$(MAKE) quality-check
	$(MAKE) test
	$(MAKE) docker-build
	@echo "CI simulation complete!"

# Quick commands for daily development
quick-test: format lint test-unit ## Quick development test cycle
	@echo "Quick test cycle complete!"

quick-check: format lint type-check ## Quick quality check
	@echo "Quick quality check complete!"