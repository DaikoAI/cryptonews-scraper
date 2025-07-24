"""
Constants for Python Railway Template - Selenium Standalone Chromium

定数管理ファイル - 全ての設定値を一箇所で管理
"""

import logging

# ========================================
# Selenium Configuration
# ========================================

# デフォルト設定
DEFAULT_BROWSER = "chrome"
DEFAULT_REMOTE_URL_DOCKER = "http://selenium:4444"  # Docker環境用
DEFAULT_REMOTE_URL_LOCAL = "http://localhost:4444"  # ローカル環境用
DEFAULT_REMOTE_URL_BROWSERLESS = "wss://chrome.browserless.io"  # Browserless.io用
DEFAULT_TIMEOUT = 10  # 秒

# サポートブラウザ
SUPPORTED_BROWSERS = ["chrome", "firefox"]

# テスト用URL
TEST_URL = "https://httpbin.org/html"

# ========================================
# Environment Detection
# ========================================

# Railway環境検出用
RAILWAY_ENVIRONMENT = "RAILWAY_ENVIRONMENT"
RAILWAY_PROJECT_ID = "RAILWAY_PROJECT_ID"

# ========================================
# Browser Options
# ========================================

# Chrome設定
CHROME_WINDOW_SIZE = "1920,1080"
CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Firefox設定
FIREFOX_WINDOW_WIDTH = "1920"
FIREFOX_WINDOW_HEIGHT = "1080"

# ========================================
# Scraping Configuration
# ========================================

# 並列処理設定（環境変数: SCRAPING_MAX_WORKERS）
# 推奨値: 1-4（CPU使用量とメモリ使用量のバランス）
DEFAULT_SCRAPING_MAX_WORKERS = 2

# バッチサイズ設定（環境変数: SCRAPING_BATCH_SIZE）
# 推奨値: 2-5（小さいほど安定、大きいほど高速）
DEFAULT_SCRAPING_BATCH_SIZE = 5

# ========================================
# File and Directory Paths
# ========================================

DEFAULT_SCREENSHOT_DIR = "reports"
DEFAULT_SCREENSHOT_NAME = "screenshot.png"

# ========================================
# Web UI and Monitoring
# ========================================

VNC_URL = "http://localhost:7900"  # VNC接続URL

# ========================================
# Logging Configuration
# ========================================

# ログレベル
DEFAULT_LOG_LEVEL = logging.INFO

# ANSI色コード
LOG_COLORS = {
    "DEBUG": "\033[32m",  # 緑
    "INFO": "\033[36m",  # シアン
    "WARNING": "\033[33m",  # 黄
    "WARN": "\033[33m",  # 黄
    "ERROR": "\033[31m",  # 赤
    "CRITICAL": "\033[31m",  # 赤
    "LOG": "",  # 色なし
}

LOG_ICONS = {
    "DEBUG": "🔍",
    "INFO": "✅",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "CRITICAL": "💥",
}

# ANSI制御コード
ANSI_BOLD = "\033[1m"
ANSI_RESET = "\033[0m"
ANSI_GRAY = "\033[90m"

# ========================================
# Application Messages
# ========================================

APP_TITLE = "🚀 Python Railway Template - Selenium Remote WebDriver"
BANNER_LENGTH = 60
SEPARATOR_LENGTH = 60

# エラーメッセージ
UNSUPPORTED_BROWSER_MSG = "Unsupported browser: {}. Use {}"
CONNECTION_FAILED_MSG = "Failed to connect to Remote WebDriver: {}"
WEBDRIVER_NOT_CONNECTED_MSG = "WebDriver not connected. Call connect() first."

# 成功メッセージ
CONNECTION_SUCCESS_MSG = "Connected successfully! Browser: {} {}"
SCRAPING_SUCCESS_MSG = "Test page scraped successfully"
SCREENSHOT_SAVED_MSG = "Screenshot saved: {}"

# ========================================
# Environment Variables
# ========================================

ENV_SELENIUM_BROWSER = "SELENIUM_BROWSER"
ENV_SELENIUM_REMOTE_URL = "SELENIUM_REMOTE_URL"
ENV_BROWSERLESS_TOKEN = "BROWSERLESS_TOKEN"  # Browserless.io APIトークン
