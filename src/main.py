"""
Python Railway Template - Selenium Standalone Chromium Example

Remote WebDriver with Standalone Chromium を使用したスクレイピングアプリケーション
"""

import os
import sys
from datetime import datetime

from src.constants import (
    APP_TITLE,
    BANNER_LENGTH,
    DEFAULT_BROWSER,
    DEFAULT_REMOTE_URL_DOCKER,
    SEPARATOR_LENGTH,
    VNC_URL,
)
from src.scraper import create_scraper_from_env, scrape_test_page
from src.utils.logger import get_app_logger


def print_banner(logger, browser: str, remote_url: str) -> None:
    """アプリケーションバナーを表示"""
    logger.info(APP_TITLE)
    logger.info("=" * BANNER_LENGTH)
    logger.info(f"Remote WebDriver URL: {remote_url}")
    logger.info(f"Browser: {browser}")
    logger.info(f"Web UI: {remote_url}")
    logger.info(f"VNC Viewer: {VNC_URL}")
    logger.info("-" * SEPARATOR_LENGTH)


def main() -> None:
    """メインエントリーポイント"""
    logger = get_app_logger(__name__)

    try:
        # 環境変数取得と環境検出
        browser = os.getenv("SELENIUM_BROWSER", DEFAULT_BROWSER)

        # 環境に応じたデフォルトURL選択
        if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"):
            default_url = "wss://chrome.browserless.io"  # Railway環境
            logger.info("🚂 Running on Railway - Using external browser service")
        elif os.getenv("DOCKER_CONTAINER"):
            default_url = DEFAULT_REMOTE_URL_DOCKER  # Docker環境
            logger.info("🐳 Running in Docker - Using Selenium Standalone")
        else:
            default_url = "http://localhost:4444"  # ローカル環境
            logger.info("💻 Running locally - Using localhost Selenium")

        remote_url = os.getenv("SELENIUM_REMOTE_URL", default_url)

        # バナー表示
        print_banner(logger, browser, remote_url)

        # スクレイピング実行
        logger.info(f"Starting Selenium Standalone test with {browser}...")

        with create_scraper_from_env() as scraper:
            # テストページスクレイピング（外部関数を使用）
            result = scrape_test_page(scraper)

            # スクリーンショット保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = scraper.take_screenshot(f"test_screenshot_{timestamp}.png")

            # 結果表示
            logger.info("📊 Scraping Results:")
            for key, value in result.items():
                logger.info(f"  {key}: {value}")

            logger.info(f"📸 Screenshot: {screenshot_path}")
            logger.info("✅ Test completed successfully!")

    except KeyboardInterrupt:
        logger.warning("🛑 Operation cancelled by user")
        sys.exit(1)

    except Exception as e:
        logger.error(f"❌ Application failed: {e}")
        logger.info("")
        logger.info("🔧 Troubleshooting:")
        logger.info("- Check if Selenium Standalone is running (docker-compose up)")
        logger.info(f"- Verify server status at {remote_url}")
        logger.info("- Check if the specified browser node is available")
        logger.info("- Ensure proper network connectivity")

        sys.exit(1)


if __name__ == "__main__":
    main()
