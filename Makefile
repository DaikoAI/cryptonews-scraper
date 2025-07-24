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
	@echo "  setup-hooks   Setup git pre-commit hooks for auto-formatting"
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

# コード品質チェック
check:
	uv run ruff check .
	uv run ruff format --check .

# コードフォーマット（自動修正）
format:
	uv run ruff check --fix --fix-only .
	uv run ruff format .

# リント実行（修正なし）
lint:
	uv run ruff check .

# リント実行（自動修正あり）
lint-fix:
	uv run ruff check --fix .

# Git pre-commitフックを設定（自動フォーマット）
setup-hooks:
	@echo "🪝 Setting up git pre-commit hooks..."
	@mkdir -p .git/hooks
	@echo '#!/bin/sh' > .git/hooks/pre-commit
	@echo 'echo "🧹 Auto-formatting code before commit..."' >> .git/hooks/pre-commit
	@echo 'make format' >> .git/hooks/pre-commit
	@echo 'git add -u' >> .git/hooks/pre-commit
	@chmod +x .git/hooks/pre-commit
	@echo "✅ Pre-commit hook installed! Code will be auto-formatted before each commit."

# テスト実行
test:
	uv run pytest tests/ -v

# アプリケーション実行
run:
	uv run python src/main.py

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

# レポートファイルクリーンアップ
clean:
	rm -rf reports/*.json

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
