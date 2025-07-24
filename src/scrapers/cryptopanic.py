"""
CryptoPanic専用スクレイパー

docs/target.htmlの構造に最適化されたスクレイピング実装
"""

import re
import time
from datetime import UTC, datetime
from urllib.parse import urljoin

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.models import DataSource
from src.scrapers.base import BaseScraper


class CryptoPanicScraper(BaseScraper):
    """CryptoPanic専用スクレイパー"""

    BASE_URL = "https://cryptopanic.com"

    def get_source_name(self) -> str:
        """ソース名を取得"""
        return "cryptopanic"

    def get_base_url(self) -> str:
        """ベースURLを取得"""
        return f"{self.BASE_URL}/"

    def scrape_articles(self) -> list[DataSource]:
        """CryptoPanicから記事をスクレイピング"""
        try:
            self._wait_for_page_load()
            article_elements = self._get_article_elements()
            if not article_elements:
                self.logger.warning("No article elements found")
                return []
            self.logger.info(f"Found {len(article_elements)} article elements")
            return self._process_article_elements(article_elements)
        except Exception as e:
            self.logger.error(f"Failed to scrape articles: {e}")
            raise

    def _process_article_elements(self, elements: list) -> list[DataSource]:
        """記事要素を処理してDataSourceリストを生成"""
        data_sources = []
        for element in elements:
            try:
                data_source = self._extract_data_source(element)
                if data_source and data_source.is_valid():
                    data_sources.append(data_source)
            except Exception as e:
                self.logger.debug(f"Failed to process element: {e}")
                continue

        self.logger.info(f"Successfully extracted {len(data_sources)} valid data sources")
        return data_sources

    def _wait_for_page_load(self) -> None:
        """ページの読み込み完了を待機"""
        try:
            # ニュース記事コンテナの出現を待機
            wait = WebDriverWait(self.driver.driver, 15)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".news-row")))
            self.logger.info("CryptoPanic page loaded successfully")
            time.sleep(2)  # 追加読み込み待機

        except TimeoutException:
            self.logger.warning("Timeout waiting for news elements, continuing anyway")
            time.sleep(3)

    def _get_article_elements(self) -> list:
        """ニュース記事要素を取得"""
        try:
            # .news-row でニュース記事を取得（広告・スポンサーを除外）
            elements = self.driver.find_elements(By.CSS_SELECTOR, ".news-row.news-row-link")

            if not elements:
                # フォールバック: 全ての.news-rowを取得
                elements = self.driver.find_elements(By.CSS_SELECTOR, ".news-row")
                # sponsored を除外
                elements = [el for el in elements if "sponsored" not in el.get_attribute("class")]

            self.logger.info(f"Found {len(elements)} news elements")
            return elements

        except Exception as e:
            self.logger.error(f"Failed to get article elements: {e}")
            return []

    def _extract_data_source(self, element) -> DataSource | None:
        """記事要素からDataSourceを抽出"""
        try:
            title, url = self._extract_title_and_url(element)
            if not title or not url:
                return None

            return DataSource.from_cryptopanic_news(
                title=title.strip(),
                url=self._normalize_url(url),
                published_at=self._extract_published_time(element),
                currencies=self._extract_currencies(element),
                source_domain=self._extract_source_domain(element),
                scraped_at=datetime.now(UTC),
            )

        except Exception as e:
            self.logger.debug(f"Failed to extract data source: {e}")
            return None

    def _extract_title_and_url(self, element) -> tuple[str | None, str | None]:
        """タイトルとURLを抽出"""
        try:
            # .nc-title 内のリンクとタイトルテキストを取得
            title_cell = element.find_element(By.CSS_SELECTOR, ".nc-title")
            link_element = title_cell.find_element(By.CSS_SELECTOR, "a")

            # 正しいタイトルテキストの抽出
            title_text_element = title_cell.find_element(By.CSS_SELECTOR, ".title-text > span:first-child")

            title = title_text_element.text.strip()
            url = link_element.get_attribute("href")

            return title, url

        except NoSuchElementException as e:
            self.logger.debug(f"Failed to extract title/URL: {e}")
            return None, None

    def _extract_published_time(self, element) -> datetime | None:
        """公開時刻を抽出"""
        try:
            # time要素のdatetime属性から時刻を取得
            time_element = element.find_element(By.CSS_SELECTOR, ".nc-date time")
            datetime_attr = time_element.get_attribute("datetime")

            if not datetime_attr:
                return None

            # JavaScriptのDateコンストラクタ形式をパース
            # 例: "Thu Jul 24 2025 20:52:42 GMT+0900 (Japan Standard Time)"
            try:
                # GMT+0900 部分を削除してパース
                cleaned_datetime = re.sub(r"\s+GMT[+-]\d{4}\s+\([^)]+\)", "", datetime_attr)
                return datetime.strptime(cleaned_datetime, "%a %b %d %Y %H:%M:%S")
            except ValueError:
                # フォールバック: 現在時刻を使用
                self.logger.debug(f"Could not parse datetime: {datetime_attr}")
                return datetime.now(UTC)

        except NoSuchElementException:
            return None

    def _extract_currencies(self, element) -> list[str]:
        """関連通貨を抽出"""
        try:
            currencies = []

            # .nc-currency 内のリンクから通貨を取得
            currency_cell = element.find_element(By.CSS_SELECTOR, ".nc-currency")
            currency_links = currency_cell.find_elements(By.CSS_SELECTOR, "a.colored-link")

            for link in currency_links:
                currency_text = link.text.strip()
                if currency_text and currency_text not in currencies:
                    currencies.append(currency_text)

            return currencies

        except NoSuchElementException:
            return []

    def _extract_source_domain(self, element) -> str:
        """ソースドメインを抽出"""
        try:
            # .si-source-domain 要素を探す
            source_element = element.find_element(By.CSS_SELECTOR, ".si-source-domain")
            return source_element.text.strip()

        except NoSuchElementException:
            return None

    def _normalize_url(self, url: str) -> str:
        """URLを正規化"""
        if url.startswith("http"):
            return url
        elif url.startswith("/"):
            return urljoin(self.BASE_URL, url)
        else:
            return urljoin(self.BASE_URL, "/" + url)
