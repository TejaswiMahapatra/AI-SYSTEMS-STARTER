.PHONY: help init dev down clean logs test seed backend frontend

# Default target
.DEFAULT_GOAL := help

# Colors for output
CYAN := \033[0;36m
RESET := \033[0m

help: ## Show this help message
	@echo "$(CYAN)AI Systems Starter - Available Commands:$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-15s$(RESET) %s\n", $$1, $$2}'
	@echo ""

init: ## Initial setup (run once)
	@echo "$(CYAN)Initializing AI Systems Starter...$(RESET)"
	@echo ""
	@echo "$(CYAN)Step 1: Checking dependencies...$(RESET)"
	@command -v docker >/dev/null 2>&1 || { echo "Docker required but not installed. Visit https://docs.docker.com/get-docker/"; exit 1; }
	@command -v docker-compose >/dev/null 2>&1 || command -v docker compose >/dev/null 2>&1 || { echo "Docker Compose required"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "Python 3.11+ required"; exit 1; }
	@echo "Dependencies OK"
	@echo ""
	@echo "$(CYAN)Step 2: Creating .env file...$(RESET)"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo ".env created from .env.example"; \
		echo "Please edit .env and add your OPENAI_API_KEY"; \
	else \
		echo ".env already exists, skipping"; \
	fi
	@echo ""
	@echo "$(CYAN)Step 3: Starting Docker services...$(RESET)"
	@cd infra/docker && docker-compose up -d
	@echo "Waiting for services to be ready..."
	@sleep 10
	@echo "Services started"
	@echo ""
	@echo "$(CYAN)Step 4: Installing Python dependencies...$(RESET)"
	@if [ -f backend/pyproject.toml ]; then \
		cd backend && pip install -e .; \
		echo "Backend dependencies installed"; \
	else \
		echo "pyproject.toml not found yet, skipping"; \
	fi
	@echo ""
	@echo "$(CYAN)Setup complete!$(RESET)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env and add your OPENAI_API_KEY"
	@echo "  2. Run: make dev"
	@echo "  3. Visit: http://localhost:8000/docs (API)"
	@echo ""

dev: ## Start development environment
	@echo "$(CYAN)Starting development environment...$(RESET)"
	@cd infra/docker && docker-compose up

dev-detached: ## Start development environment in background
	@echo "$(CYAN)Starting development environment (detached)...$(RESET)"
	@cd infra/docker && docker-compose up -d
	@echo "Services running in background"
	@echo ""
	@make status

down: ## Stop all services
	@echo "$(CYAN)Stopping services...$(RESET)"
	@cd infra/docker && docker-compose down
	@echo "Services stopped"

clean: ## Stop services and remove volumes (fresh start)
	@echo "$(CYAN)Cleaning up (this will DELETE all data)...$(RESET)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd infra/docker && docker-compose down -v; \
		echo "All data removed"; \
	else \
		echo "Cancelled"; \
	fi

logs: ## View logs from all services
	@cd infra/docker && docker-compose logs -f

logs-postgres: ## View PostgreSQL logs
	@cd infra/docker && docker-compose logs -f postgres

logs-weaviate: ## View Weaviate logs
	@cd infra/docker && docker-compose logs -f weaviate

logs-redis: ## View Redis logs
	@cd infra/docker && docker-compose logs -f redis

status: ## Show status of all services
	@echo "$(CYAN)Service Status:$(RESET)"
	@cd infra/docker && docker-compose ps

test: ## Run all tests
	@echo "$(CYAN)Running tests...$(RESET)"
	@if [ -d backend/tests ]; then \
		cd backend && pytest -v; \
	else \
		echo "Tests not set up yet"; \
	fi

test-unit: ## Run unit tests only
	@echo "$(CYAN)Running unit tests...$(RESET)"
	@cd backend && pytest tests/unit -v

test-integration: ## Run integration tests
	@echo "$(CYAN)Running integration tests...$(RESET)"
	@cd backend && pytest tests/integration -v

seed: ## Load sample data
	@echo "$(CYAN)Seeding sample data...$(RESET)"
	@if [ -f scripts/seed.py ]; then \
		python scripts/seed.py; \
		echo "Sample data loaded"; \
	else \
		echo "Seed script not created yet"; \
	fi

backend: ## Run backend server (for development)
	@echo "$(CYAN)Starting backend server...$(RESET)"
	@cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

worker: ## Run ingestion worker (for development)
	@echo "$(CYAN)Starting ingestion worker...$(RESET)"
	@python -m backend.workers.ingestion_worker

run: ## Start complete system (infra + backend + worker)
	@echo "$(CYAN)Starting complete Clause.AI system...$(RESET)"
	@echo ""
	@echo "$(CYAN)Step 1: Starting infrastructure...$(RESET)"
	@cd infra/docker && docker-compose up -d
	@echo "Waiting for services..."
	@sleep 10
	@echo ""
	@echo "$(CYAN)Step 2: Pulling Ollama model (if needed)...$(RESET)"
	@docker exec ai-systems-ollama ollama list | grep -q llama3.1:8b || docker exec ai-systems-ollama ollama pull llama3.1:8b
	@echo ""
	@echo "$(CYAN)Step 3: Starting backend & worker...$(RESET)"
	@echo "Backend will start on http://localhost:8000"
	@echo "Worker will process documents in background"
	@echo ""
	@echo "Press Ctrl+C to stop"
	@echo ""
	@trap 'kill 0' INT; \
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload & \
	python -m backend.workers.ingestion_worker & \
	wait

dev-full: ## Start everything in separate terminals (tmux)
	@command -v tmux >/dev/null 2>&1 || { echo "tmux required. Install: brew install tmux"; exit 1; }
	@echo "$(CYAN)Starting in tmux session 'clauseai'...$(RESET)"
	@tmux new-session -d -s clauseai -n infra 'cd infra/docker && docker-compose up'
	@tmux new-window -t clauseai -n backend 'source venv/bin/activate && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload'
	@tmux new-window -t clauseai -n worker 'source venv/bin/activate && python -m backend.workers.ingestion_worker'
	@tmux attach -t clauseai

stop-all: ## Stop all running processes (backend, worker, docker)
	@echo "$(CYAN)Stopping all processes...$(RESET)"
	@pkill -f "uvicorn backend.main:app" || true
	@pkill -f "ingestion_worker" || true
	@cd infra/docker && docker-compose down
	@echo "All processes stopped"

frontend: ## Run frontend (for development)
	@echo "$(CYAN)Starting frontend server...$(RESET)"
	@cd frontend && npm run dev

shell-postgres: ## Open PostgreSQL shell
	@docker exec -it ai-systems-postgres psql -U postgres -d ai_systems

shell-redis: ## Open Redis CLI
	@docker exec -it ai-systems-redis redis-cli

reset-weaviate: ## Reset Weaviate (delete all data)
	@echo "$(CYAN)Resetting Weaviate...$(RESET)"
	@cd infra/docker && docker-compose restart weaviate
	@echo "Weaviate reset"


ollama-pull: ## Pull Ollama model (default: llama3.1:8b)
	@echo "$(CYAN)Pulling Ollama model...$(RESET)"
	@docker exec -it ai-systems-ollama ollama pull llama3.1:8b
	@echo "Model downloaded"

ollama-list: ## List downloaded Ollama models
	@docker exec -it ai-systems-ollama ollama list

ollama-shell: ## Open Ollama interactive shell
	@docker exec -it ai-systems-ollama ollama run llama3.1:8b
URLs: ## Show all service URLs
	@echo "Service URLs:"
	@echo ""
	@echo "  Frontend:      http://localhost:3000"
	@echo "  Backend API:   http://localhost:8000"
	@echo "  API Docs:      http://localhost:8000/docs"
	@echo "  Ollama (LLM):  http://localhost:11434"
	@echo "  Weaviate:      http://localhost:8080"
	@echo "  MinIO Console: http://localhost:9001 (admin/minioadmin)"
	@echo "  Grafana:       http://localhost:3001 (admin/admin)"
	@echo "  Prometheus:    http://localhost:9090"
	@echo ""
