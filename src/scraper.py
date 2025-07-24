"""
Selenium Standalone Chromium Scraper

Remote WebDriver with Standalone Chromium を使用したウェブスクレイピング機能
"""

import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.constants import (
    CHROME_USER_AGENT,
    CHROME_WINDOW_SIZE,
    CONNECTION_FAILED_MSG,
    CONNECTION_SUCCESS_MSG,
    DEFAULT_BROWSER,
    DEFAULT_REMOTE_URL_BROWSERLESS,
    DEFAULT_REMOTE_URL_DOCKER,
    DEFAULT_REMOTE_URL_LOCAL,
    DEFAULT_SCREENSHOT_DIR,
    DEFAULT_TIMEOUT,
    ENV_SELENIUM_BROWSER,
    ENV_SELENIUM_REMOTE_URL,
    FIREFOX_WINDOW_HEIGHT,
    FIREFOX_WINDOW_WIDTH,
    RAILWAY_ENVIRONMENT,
    RAILWAY_PROJECT_ID,
    SCREENSHOT_SAVED_MSG,
    SUPPORTED_BROWSERS,
    TEST_URL,
    UNSUPPORTED_BROWSER_MSG,
    WEBDRIVER_NOT_CONNECTED_MSG,
)
from src.utils.logger import get_app_logger


class StandaloneChromiumScraper:
    """Selenium Standalone Chromium を使用したWebDriver管理クラス"""

    def __init__(
        self, browser: str = DEFAULT_BROWSER, remote_url: str = DEFAULT_REMOTE_URL_LOCAL, timeout: int = DEFAULT_TIMEOUT
    ):
        """
        Args:
            browser: ブラウザタイプ (chrome/firefox)
            remote_url: Selenium Standalone サーバーURL
            timeout: WebDriverタイムアウト (秒)
        """
        self.browser = browser.lower()
        self.remote_url = remote_url
        self.timeout = timeout
        self.driver: webdriver.Remote | None = None
        self.logger = get_app_logger(__name__)

    def _create_chrome_options(self) -> ChromeOptions:
        """Chrome用オプションを作成"""
        options = ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"--window-size={CHROME_WINDOW_SIZE}")
        options.add_argument(f"--user-agent={CHROME_USER_AGENT}")
        return options

    def _create_firefox_options(self) -> FirefoxOptions:
        """Firefox用オプションを作成"""
        options = FirefoxOptions()
        options.add_argument(f"--width={FIREFOX_WINDOW_WIDTH}")
        options.add_argument(f"--height={FIREFOX_WINDOW_HEIGHT}")
        return options

    def connect(self) -> None:
        """Remote WebDriver に接続"""
        self.logger.info(f"Connecting to Selenium Standalone {self.browser.title()}...")

        try:
            grid_url = f"{self.remote_url}/wd/hub"

            if self.browser == "chrome":
                options = self._create_chrome_options()
                self.driver = webdriver.Remote(command_executor=grid_url, options=options)

            elif self.browser == "firefox":
                options = self._create_firefox_options()
                self.driver = webdriver.Remote(command_executor=grid_url, options=options)

            else:
                supported_str = "', '".join(SUPPORTED_BROWSERS)
                raise ValueError(UNSUPPORTED_BROWSER_MSG.format(self.browser, f"'{supported_str}'"))

            # 接続確認
            browser_name = self.driver.capabilities.get("browserName", "unknown")
            browser_version = self.driver.capabilities.get("browserVersion", "unknown")

            self.logger.info(CONNECTION_SUCCESS_MSG.format(browser_name, browser_version))

        except Exception as e:
            self.logger.error(CONNECTION_FAILED_MSG.format(e))
            raise

    def disconnect(self) -> None:
        """WebDriver接続を切断"""
        if self.driver:
            try:
                self.driver.quit()
                self.logger.info("Remote WebDriver disconnected")
            except Exception as e:
                self.logger.warning(f"Error during disconnect: {e}")
            finally:
                self.driver = None

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

    def get_page(self, url: str) -> None:
        """指定URLのページを取得"""
        if not self.driver:
            raise RuntimeError(WEBDRIVER_NOT_CONNECTED_MSG)

        self.logger.info(f"Navigating to: {url}")
        self.driver.get(url)

    def wait_for_element(self, by: By, value: str, timeout: int = None) -> None:
        """要素の出現を待機"""
        if not self.driver:
            raise RuntimeError(WEBDRIVER_NOT_CONNECTED_MSG)

        wait_timeout = timeout or self.timeout
        WebDriverWait(self.driver, wait_timeout).until(EC.presence_of_element_located((by, value)))

    def find_element(self, by: By, value: str):
        """要素を検索"""
        if not self.driver:
            raise RuntimeError(WEBDRIVER_NOT_CONNECTED_MSG)

        return self.driver.find_element(by, value)

    def find_elements(self, by: By, value: str):
        """複数要素を検索"""
        if not self.driver:
            raise RuntimeError(WEBDRIVER_NOT_CONNECTED_MSG)

        return self.driver.find_elements(by, value)

    def get_page_info(self) -> dict[str, str]:
        """現在のページの基本情報を取得"""
        if not self.driver:
            raise RuntimeError(WEBDRIVER_NOT_CONNECTED_MSG)

        # ブラウザ情報
        browser_name = self.driver.capabilities.get("browserName", "unknown")
        browser_version = self.driver.capabilities.get("browserVersion", "unknown")

        return {
            "title": self.driver.title,
            "current_url": self.driver.current_url,
            "page_source_length": str(len(self.driver.page_source)),
            "browser_name": browser_name,
            "browser_version": browser_version,
        }

    def take_screenshot(self, filename: str = "screenshot.png", directory: str = DEFAULT_SCREENSHOT_DIR) -> str:
        """スクリーンショットを保存"""
        if not self.driver:
            raise RuntimeError(WEBDRIVER_NOT_CONNECTED_MSG)

        # ディレクトリ作成
        os.makedirs(directory, exist_ok=True)

        filepath = os.path.join(directory, filename)

        try:
            self.driver.save_screenshot(filepath)
            self.logger.info(SCREENSHOT_SAVED_MSG.format(filepath))
            return filepath
        except Exception as e:
            self.logger.error(f"Failed to save screenshot: {e}")
            raise


def scrape_test_page(scraper: StandaloneChromiumScraper) -> dict[str, str]:
    """テストページをスクレイピング（クラス外関数）"""
    logger = get_app_logger(__name__)

    try:
        # テストページに移動
        scraper.get_page(TEST_URL)

        # ページロード待機
        scraper.wait_for_element(By.TAG_NAME, "h1")

        # 基本ページ情報取得
        page_info = scraper.get_page_info()

        # H1テキスト取得
        try:
            h1_element = scraper.find_element(By.TAG_NAME, "h1")
            h1_text = h1_element.text
        except Exception:
            h1_text = "N/A"

        # 結果をまとめる
        result = {
            "status": "success",
            "title": page_info["title"],
            "h1_text": h1_text,
            "page_source_length": page_info["page_source_length"],
            "url": page_info["current_url"],
            "browser_name": page_info["browser_name"],
            "browser_version": page_info["browser_version"],
            "execution_mode": "selenium_standalone_chromium",
        }

        logger.info("Test page scraped successfully")
        logger.debug(f"Scraping result: {result}")

        return result

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        raise


def create_scraper_from_env() -> StandaloneChromiumScraper:
    """環境変数からスクレイパーを作成"""
    browser = os.getenv(ENV_SELENIUM_BROWSER, DEFAULT_BROWSER)

    # Railway環境の検出と適切なデフォルトURL選択
    if os.getenv(RAILWAY_ENVIRONMENT) or os.getenv(RAILWAY_PROJECT_ID):
        # Railway環境: Browserless.ioまたは外部サービスを使用
        default_url = DEFAULT_REMOTE_URL_BROWSERLESS
    elif os.getenv("DOCKER_CONTAINER"):
        # Docker環境: selenium サービスを使用
        default_url = DEFAULT_REMOTE_URL_DOCKER
    else:
        # ローカル環境: localhost を使用
        default_url = DEFAULT_REMOTE_URL_LOCAL

    remote_url = os.getenv(ENV_SELENIUM_REMOTE_URL, default_url)

    return StandaloneChromiumScraper(browser=browser, remote_url=remote_url)
