# Python Railway Template - Development Commands
# Modern Python template with uv, Ruff, and Selenium Grid

# Help command
.PHONY: help
help:
	@echo "🚀 Python Railway Template with Selenium Grid"
	@echo "============================================="
	@echo ""
	@echo "📦 Setup Commands:"
	@echo "  install       Install dependencies"
	@echo "  dev           Install dev dependencies"
	@echo ""
	@echo "🧹 Code Quality:"
	@echo "  format        Format code with ruff"
	@echo "  lint          Lint code with ruff"
	@echo "  lint-fix      Auto-fix lint issues"
	@echo "  check         Run both lint and format check"
	@echo ""
	@echo "🧪 Testing & Running:"
	@echo "  test          Run tests"
	@echo "  run           Run the application"
	@echo ""
	@echo "🌐 Selenium Grid Commands:"
	@echo "  grid-up       Start Selenium Grid (docker-compose up -d)"
	@echo "  grid-down     Stop Selenium Grid (docker-compose down)"
	@echo "  grid-logs     View Grid logs"
	@echo "  grid-status   Check Grid status"
	@echo ""
	@echo "🕷️ Scraping Commands:"
	@echo "  scrape        Run scraping and show logs (ONE COMMAND!)"
	@echo "  scrape-logs   Show scraping logs only"
	@echo "  scrape-build  Build and run scraping with fresh build"
	@echo "  logs          Show all container logs"
	@echo ""
	@echo "🐳 Docker Commands:"
	@echo "  docker-build  Build app Docker image"
	@echo "  docker-up     Start full stack with docker-compose"
	@echo "  docker-down   Stop full stack"
	@echo ""
	@echo "🚂 Deployment:"
	@echo "  railway-deploy Deploy to Railway"
	@echo ""
	@echo "🧹 Cleanup:"
	@echo "  clean         Clean Python cache + Docker resources"
	@echo "  clean-python  Clean Python cache files only"
	@echo "  clean-docker  Clean Docker containers/images only"
	@echo "  clean-all     🔥 Deep clean ALL Docker resources (WARNING)"

# Development setup
.PHONY: install
install:
	uv sync

.PHONY: dev
dev:
	uv sync --group dev

# Code formatting and linting
.PHONY: format
format:
	uv run ruff format src/

.PHONY: lint
lint:
	uv run ruff check src/

.PHONY: lint-fix
lint-fix:
	uv run ruff check --fix src/

.PHONY: check
check: lint format

# Testing
.PHONY: test
test:
	uv run python -m pytest

# Selenium Grid management
.PHONY: grid-up
grid-up:
	@echo "🚀 Starting Selenium Grid..."
	docker-compose up -d selenium
	@echo "⏳ Waiting for Grid to be ready..."
	@sleep 10
	@echo "✅ Grid started! Access it at:"
	@echo "   Grid Console: http://localhost:4444"
	@echo "   Chrome VNC:   http://localhost:7900 (password: secret)"

.PHONY: grid-down
grid-down:
	@echo "🛑 Stopping Selenium Grid..."
	docker-compose down

.PHONY: grid-logs
grid-logs:
	docker-compose logs -f selenium

.PHONY: grid-status
grid-status:
	@echo "🔍 Checking Selenium Grid status..."
	@curl -s http://localhost:4444/status | jq . || echo "Grid not available or jq not installed"
	@echo ""
	@echo "📊 Grid Console: http://localhost:4444"

# Run application
.PHONY: run
run:
	@echo "🔍 Checking if Selenium Grid is running..."
	@if ! curl -s http://localhost:4444/status > /dev/null 2>&1; then \
		echo "❌ Selenium Grid is not running"; \
		echo "💡 Start it with: make grid-up"; \
		exit 1; \
	fi
	@echo "✅ Grid is running!"
	uv run python src/main.py

# Scraping commands
.PHONY: scrape
scrape:
	@echo "🕷️ Running scraping with logs..."
	@echo "📋 Starting Selenium Grid if not running..."
	@docker-compose up -d selenium
	@echo "⏳ Waiting for Grid to be ready..."
	@sleep 5
	@echo "🚀 Running scraping application..."
	@docker-compose up --build selenium-scraper

.PHONY: scrape-logs
scrape-logs:
	@echo "📋 Showing scraping logs..."
	@docker-compose logs -f selenium-scraper

.PHONY: scrape-build
scrape-build:
	@echo "🔨 Building and running scraping with fresh build..."
	@docker-compose up -d selenium
	@echo "⏳ Waiting for Grid to be ready..."
	@sleep 5
	@docker-compose up --build --force-recreate selenium-scraper

.PHONY: logs
logs:
	@echo "📋 Showing all container logs..."
	@docker-compose logs -f

# Docker commands
.PHONY: docker-build
docker-build:
	docker build -t python-railway-template .

.PHONY: docker-up
docker-up:
	@echo "🚀 Starting full stack with docker-compose..."
	docker-compose up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 15
	@echo "✅ Stack started! Services:"
	@echo "   Grid Console: http://localhost:4444"
	@echo "   Chrome VNC:   http://localhost:7900 (password: secret)"

.PHONY: docker-down
docker-down:
	@echo "🛑 Stopping full stack..."
	docker-compose down

# Railway deployment
.PHONY: railway-deploy
railway-deploy:
	railway up

# Cleanup
.PHONY: clean
clean: clean-python clean-docker
	@echo "🧹 Complete cleanup finished!"

.PHONY: clean-python
clean-python:
	@echo "🐍 Cleaning Python cache files..."
	@find . -type d -name "__pycache__" -delete 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -delete 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -delete 2>/dev/null || true
	@rm -rf .coverage htmlcov/ 2>/dev/null || true
	@echo "✅ Python cleanup completed"

.PHONY: clean-docker
clean-docker:
	@echo "🐳 Cleaning Docker resources..."
	@echo "  📦 Stopping and removing containers..."
	@docker-compose down --remove-orphans 2>/dev/null || true
	@docker stop selenium-chrome selenium-scraper-app 2>/dev/null || true
	@docker rm selenium-chrome selenium-scraper-app 2>/dev/null || true
	@echo "  🖼️  Removing project images..."
	@docker rmi python-railway-template-selenium-scraper 2>/dev/null || true
	@docker rmi selenium-scraper 2>/dev/null || true
	@echo "  🗂️  Removing dangling images and build cache..."
	@docker image prune -f 2>/dev/null || true
	@docker builder prune -f 2>/dev/null || true
	@echo "  🔗 Cleaning unused networks..."
	@docker network prune -f 2>/dev/null || true
	@echo "✅ Docker cleanup completed"

.PHONY: clean-all
clean-all: clean
	@echo "🔥 Performing deep Docker cleanup..."
	@echo "  ⚠️  This will remove ALL unused Docker resources"
	@docker system prune -af --volumes 2>/dev/null || true
	@echo "🧹 Deep cleanup completed!"
