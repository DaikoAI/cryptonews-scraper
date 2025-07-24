"""
Base Scraper Class

全サイト共通のスクレイピング基底クラス
"""

from abc import ABC, abstractmethod

from src.models import DataSource
from src.utils.logger import get_app_logger
from src.webdriver import WebDriverManager


class BaseScraper(ABC):
    """基底スクレイパークラス"""

    def __init__(self, driver: WebDriverManager):
        """
        Args:
            driver: WebDriverインスタンス
        """
        self.driver = driver
        self.logger = get_app_logger(self.__class__.__name__)

    @abstractmethod
    def get_source_name(self) -> str:
        """ソース名を取得（サブクラスで実装）"""
        pass

    @abstractmethod
    def get_base_url(self) -> str:
        """ベースURLを取得（サブクラスで実装）"""
        pass

    @abstractmethod
    def scrape_articles(self) -> list[DataSource]:
        """記事をスクレイピング（サブクラスで実装）"""
        pass

    def run_scraping(self) -> list[DataSource]:
        """スクレイピングを実行"""
        self.logger.info(f"Starting scraping for {self.get_source_name()}")

        try:
            # ベースURLに移動
            self.driver.navigate_to(self.get_base_url())

            # 記事をスクレイピング
            data_sources = self.scrape_articles()

            # バリデーション
            valid_data_sources = [ds for ds in data_sources if ds.is_valid()]

            self.logger.info(f"Scraped {len(valid_data_sources)} valid data sources from {self.get_source_name()}")

            return valid_data_sources

        except Exception as e:
            self.logger.error(f"Scraping failed for {self.get_source_name()}: {e}")
            raise
