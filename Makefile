.PHONY: help install test clean docker-build docker-up docker-down deploy logs health

# Default target
help:
	@echo "AI Voice Form Filling Agent - Production Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install       - Install dependencies"
	@echo "  make test          - Run tests with coverage"
	@echo "  make dev           - Run development server"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-up     - Start all services"
	@echo "  make docker-down   - Stop all services"
	@echo "  make logs          - View application logs"
	@echo ""
	@echo "Production:"
	@echo "  make deploy        - Deploy to production"
	@echo "  make health        - Check application health"
	@echo "  make backup        - Backup Redis data"
	@echo "  make clean         - Clean temporary files"

# Development
install:
	pip install -r requirements.txt

test:
	pytest tests/ --cov=src --cov-report=html --cov-report=term-missing -v

dev:
	python -m uvicorn src.api:app --reload --host 0.0.0.0 --port 8000

# Docker
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d
	@echo "Services started. Access API at http://localhost:8000"
	@echo "API docs at http://localhost:8000/docs"

docker-down:
	docker-compose down

logs:
	docker-compose logs -f app

# Production
deploy:
	@echo "Deploying to production..."
	docker-compose build
	docker-compose up -d
	@echo "Waiting for services to start..."
	@sleep 5
	@make health

health:
	@echo "Checking application health..."
	@curl -f http://localhost:8000/health || echo "Health check failed!"
	@echo ""
	@docker-compose ps

backup:
	@mkdir -p backups
	docker exec $$(docker-compose ps -q redis) redis-cli SAVE
	docker cp $$(docker-compose ps -q redis):/data/dump.rdb backups/redis-$$(date +%Y%m%d-%H%M%S).rdb
	@echo "Backup created in backups/"

restore:
	@echo "Restoring latest backup..."
	@ls -t backups/*.rdb | head -1 | xargs -I {} docker cp {} $$(docker-compose ps -q redis):/data/dump.rdb
	docker-compose restart redis

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	rm -rf htmlcov/ .coverage

# Testing
test-integration:
	pytest tests/ -v -m integration

test-unit:
	pytest tests/ -v -m unit

test-api:
	pytest tests/ -v -m api

# Monitoring
monitor:
	@echo "=== Docker Stats ==="
	docker stats --no-stream
	@echo ""
	@echo "=== Disk Usage ==="
	docker system df
	@echo ""
	@echo "=== Service Status ==="
	docker-compose ps

# Security
security-scan:
	@echo "Scanning for security vulnerabilities..."
	pip-audit
	docker scan voice-form-agent:latest || true

# Update dependencies
update-deps:
	pip list --outdated
	@echo "Run 'pip install --upgrade <package>' to update"
