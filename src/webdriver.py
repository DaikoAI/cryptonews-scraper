"""
WebDriver Manager

Remote WebDriver with Standalone Chromium を使用したWebDriver管理クラス
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config import Config
from src.constants import (
    CHROME_USER_AGENT,
    CHROME_WINDOW_SIZE,
    CONNECTION_FAILED_MSG,
    CONNECTION_SUCCESS_MSG,
    DEFAULT_BROWSER,
    DEFAULT_TIMEOUT,
    FIREFOX_WINDOW_HEIGHT,
    FIREFOX_WINDOW_WIDTH,
    SUPPORTED_BROWSERS,
    UNSUPPORTED_BROWSER_MSG,
    WEBDRIVER_NOT_CONNECTED_MSG,
)
from src.utils.logger import get_app_logger


class WebDriverManager:
    """WebDriver管理クラス - Selenium Remote WebDriverの統一インターフェース"""

    def __init__(self, browser: str = DEFAULT_BROWSER, remote_url: str | None = None, timeout: int = DEFAULT_TIMEOUT):
        """
        Args:
            browser: ブラウザタイプ (chrome/firefox)
            remote_url: Selenium Standalone サーバーURL (Noneの場合は環境から自動選択)
            timeout: WebDriverタイムアウト (秒)
        """
        self.browser = browser.lower()
        self.remote_url = remote_url or self._get_default_remote_url()
        self.timeout = timeout
        self.driver: webdriver.Remote | None = None
        self.logger = get_app_logger(__name__)

    def _get_default_remote_url(self) -> str:
        """環境に応じたデフォルトRemote URLを取得"""
        return Config.get_selenium_remote_url()

    def _create_chrome_options(self) -> ChromeOptions:
        """Chrome用オプションを作成"""
        options = ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--headless")  # ヘッドレスモード追加
        options.add_argument(f"--window-size={CHROME_WINDOW_SIZE}")
        options.add_argument(f"--user-agent={CHROME_USER_AGENT}")
        return options

    def _create_firefox_options(self) -> FirefoxOptions:
        """Firefox用オプションを作成"""
        options = FirefoxOptions()
        options.add_argument("--headless")  # ヘッドレスモード追加
        options.add_argument(f"--width={FIREFOX_WINDOW_WIDTH}")
        options.add_argument(f"--height={FIREFOX_WINDOW_HEIGHT}")
        return options

    def connect(self) -> None:
        """Remote WebDriver に接続"""
        self.logger.info(f"Connecting to Selenium {self.browser.title()}...")

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
                self.logger.info("WebDriver disconnected")
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

    def navigate_to(self, url: str) -> None:
        """指定URLのページに移動"""
        if not self.driver:
            raise RuntimeError(WEBDRIVER_NOT_CONNECTED_MSG)

        self.logger.info(f"Navigating to: {url}")
        self.driver.get(url)

    def wait_for_element(self, by: By, value: str, timeout: int | None = None) -> None:
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

    @property
    def page_source(self) -> str:
        """現在のページソースを取得"""
        if not self.driver:
            raise RuntimeError(WEBDRIVER_NOT_CONNECTED_MSG)
        return self.driver.page_source

    @property
    def current_url(self) -> str:
        """現在のURLを取得"""
        if not self.driver:
            raise RuntimeError(WEBDRIVER_NOT_CONNECTED_MSG)
        return self.driver.current_url

    @property
    def title(self) -> str:
        """現在のページタイトルを取得"""
        if not self.driver:
            raise RuntimeError(WEBDRIVER_NOT_CONNECTED_MSG)
        return self.driver.title


def create_webdriver_from_env() -> WebDriverManager:
    """環境変数からWebDriverを作成"""
    return WebDriverManager(
        browser=Config.SELENIUM_BROWSER,
        remote_url=Config.SELENIUM_REMOTE_URL,
    )
