"""
CryptoPanic News Scraper

CryptoPanicサイトからニュース記事をスクレイピングするクラス
"""

import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from urllib.parse import urljoin

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.config import Config
from src.models import DataSource
from src.scrapers.base import BaseScraper
from src.utils.scraping_utils import (
    ElementSearcher,
    TabManager,
    TextCleaner,
    WebDriverUtils,
)


class CryptoPanicScraper(BaseScraper):
    """CryptoPanic専用スクレイパー - 高速並列版"""

    BASE_URL = "https://cryptopanic.com"

    def __init__(self, driver):
        super().__init__(driver)
        self.tab_manager = TabManager(driver.driver, self.logger)

        # URL設定
        self.url = f"{self.BASE_URL}/"

        # 並列処理設定
        self.max_workers = Config.SCRAPING_MAX_WORKERS
        self.batch_size = Config.SCRAPING_BATCH_SIZE
        self.driver_lock = threading.Lock()  # WebDriver操作のロック

        self.logger.info(f"🚀 Parallel processing: {self.max_workers} workers, batch size: {self.batch_size}")

    def get_source_name(self) -> str:
        return "cryptopanic"

    def get_base_url(self) -> str:
        """ベースURLを取得"""
        return self.url

    def scrape_articles(self) -> list[DataSource]:
        """全記事をスクレイピング（BaseScraper用）"""
        # フィルタリングなしで全記事を取得
        all_elements = self.get_filtered_elements_by_date(None)
        return self.scrape_filtered_articles(all_elements)

    def get_filtered_elements_by_date(self, last_published_at: datetime | None) -> list:
        """日時フィルタリング済みのelementリストを取得"""
        self.logger.info("🔍 Loading news page and filtering articles...")

        # ページ読み込み
        self.driver.driver.get(self.url)
        self.driver.driver.set_window_size(1920, 1080)

        # 全要素の取得
        self._scroll_to_load_all_elements()
        all_elements = self._get_article_elements()

        # 日時でフィルタリング
        filtered_elements = self._filter_elements_by_published_date(all_elements, last_published_at)

        self.logger.info(f"📊 Found {len(filtered_elements)}/{len(all_elements)} new articles")

        return filtered_elements

    def _filter_elements_by_published_date(self, elements: list, last_published_at: datetime | None) -> list:
        """elementを公開日時でフィルタリング"""
        if not last_published_at:
            self.logger.info("No last_published_at provided, returning all elements")
            return elements

        self.logger.info(f"🕰️ Filtering articles newer than: {last_published_at}")

        filtered_elements = []
        same_count = 0
        older_count = 0
        newer_count = 0
        invalid_count = 0

        for i, element in enumerate(elements):
            try:
                published_at = self._extract_published_at(element)

                # デバッグ情報（最初の5個のみ）
                if i < 5:
                    title_preview = self._extract_title_from_element(element)
                    title_preview = (
                        title_preview[:30] + "..." if title_preview and len(title_preview) > 30 else title_preview
                    )
                    self.logger.debug(f"Element {i + 1}: '{title_preview}' -> published_at={published_at}")

                # 時間情報が取得できない記事は新しい記事として扱う（安全サイド）
                if not published_at:
                    filtered_elements.append(element)
                    invalid_count += 1
                    if i < 5:
                        self.logger.debug(f"Element {i + 1}: No published_at, treating as new article")
                elif published_at > last_published_at:
                    filtered_elements.append(element)
                    newer_count += 1
                elif published_at == last_published_at:
                    same_count += 1
                    if i < 5:
                        self.logger.debug(f"Element {i + 1}: Same time as last article, skipping")
                else:
                    older_count += 1
                    if i < 5:
                        self.logger.debug(f"Element {i + 1}: Older than last article, skipping")

            except Exception as e:
                # エラーの場合も新しい記事として扱う（安全サイド）
                filtered_elements.append(element)
                invalid_count += 1
                self.logger.debug(f"Failed to parse date for element {i + 1}: {e}, treating as new article")
                continue

        self.logger.info(
            f"📊 Filtering results: {newer_count} newer, {same_count} same, {older_count} older, {invalid_count} no-time (treated as new)"
        )

        # 新しい順にソート（タイムゾーン問題を解決）
        filtered_elements.sort(
            key=lambda x: self._extract_published_at(x) or datetime.min.replace(tzinfo=UTC), reverse=True
        )

        return filtered_elements

    def scrape_filtered_articles(self, filtered_elements: list) -> list[DataSource]:
        """フィルタリング済みのelementのみをスクレイピング"""
        if not filtered_elements:
            return []

        self.logger.info(f"🔄 Scraping {len(filtered_elements)} articles...")

        result = self._process_article_elements(filtered_elements)

        self.logger.info(f"✅ Successfully scraped {len(result)} articles")

        return result

    def _scroll_to_load_all_elements(self) -> None:
        """ページを最下部までスクロールして全要素をロード"""
        try:
            self.logger.info("   🔄 Scrolling to load all elements...")

            last_height = self.driver.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_attempts = 10

            while scroll_attempts < max_attempts:
                # ページ最下部までスクロール
                self.driver.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

                # 動的コンテンツのロードを待機
                time.sleep(2)

                # 新しいコンテンツがロードされたかチェック
                new_height = self.driver.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break

                last_height = new_height
                scroll_attempts += 1
                self.logger.debug(f"   📏 Scroll attempt {scroll_attempts}/{max_attempts}, height: {new_height}")

            # 最後にページトップに戻る
            self.driver.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

            self.logger.info(f"   ✅ Scrolling completed after {scroll_attempts} attempts")

        except Exception as e:
            self.logger.warning(f"   ⚠️ Scrolling failed: {e}")

    def _process_article_elements(self, elements: list) -> list[DataSource]:
        """記事要素を並列処理でスクレイピング"""
        if not elements:
            return []

        max_workers = self.max_workers
        batch_size = self.batch_size

        data_sources = []
        total_count = len(elements)

        # バッチ処理
        for i in range(0, total_count, batch_size):
            batch_elements = elements[i : i + batch_size]
            batch_results = self._process_elements_batch(batch_elements, max_workers)

            # 結果をマージ
            for result in batch_results:
                if result["success"] and result["data_source"]:
                    data_sources.append(result["data_source"])

        return data_sources

    def _process_elements_batch(self, elements: list, max_workers: int) -> list[dict]:
        """要素のバッチを並列処理"""
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 各elementを並列で処理
            future_to_element = {
                executor.submit(self._process_single_element, element): element for element in elements
            }

            # 完了順に結果を収集
            for future in as_completed(future_to_element):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    self.logger.warning(f"Element processing failed: {e}")
                    results.append({"success": False, "data_source": None, "error": str(e)})

        return results

    def _process_single_element(self, element) -> dict:
        """単一elementを安全に処理"""
        try:
            # WebDriverアクセスは慎重にロック
            with self.driver_lock:
                # 基本チェック
                try:
                    _ = element.tag_name  # stale check
                    if not element.is_displayed():
                        return {
                            "success": False,
                            "data_source": None,
                            "error": "Element not displayed",
                        }
                except Exception as e:
                    return {
                        "success": False,
                        "data_source": None,
                        "error": f"Element stale: {e}",
                    }

                # タイトルとCryptoPanic URLを取得
                title = self._extract_title_from_element(element)
                cryptopanic_url = self._extract_cryptopanic_url(element)

                if not title or not cryptopanic_url:
                    return {
                        "success": False,
                        "data_source": None,
                        "error": "Title or URL not found",
                    }

                # 外部URL抽出を試行
                final_url = self._extract_external_url_safe(element, cryptopanic_url)

                # DataSource作成
                try:
                    published_at = self._extract_published_at(element)

                    # 入力データの前処理バリデーション
                    if not title or len(title.strip()) < 3:
                        return {
                            "success": False,
                            "data_source": None,
                            "error": f"Invalid title: '{title}'",
                        }

                    if not final_url or not (final_url.startswith("http://") or final_url.startswith("https://")):
                        return {
                            "success": False,
                            "data_source": None,
                            "error": f"Invalid URL: '{final_url}'",
                        }

                    data_source = DataSource.from_cryptopanic_news(
                        title=title.strip(),
                        url=final_url.strip(),
                        published_at=published_at,
                        scraped_at=datetime.now(UTC),
                    )
                except Exception as e:
                    return {
                        "success": False,
                        "data_source": None,
                        "error": f"DataSource creation failed: {e}",
                    }

            # ロック外で検証
            if data_source and data_source.is_valid():
                return {"success": True, "data_source": data_source, "error": None}
            else:
                error_msg = "Invalid data source"
                if data_source:
                    error_msg += f" - URL: '{data_source.url}', Title: '{data_source.summary}'"
                return {
                    "success": False,
                    "data_source": None,
                    "error": error_msg,
                }

        except Exception as e:
            return {"success": False, "data_source": None, "error": str(e)}

    def _extract_title_and_url(self, element) -> tuple[str | None, str | None]:
        """記事からタイトルとCryptoPanic URLを抽出"""
        try:
            # タイトル抽出
            title = self._extract_title_from_element(element)

            # CryptoPanic URL抽出
            cryptopanic_url = self._extract_cryptopanic_url(element)

            return title, cryptopanic_url

        except Exception as e:
            self.logger.debug(f"Failed to extract title and URL: {e}")
            return None, None

    def _extract_title_from_element(self, element) -> str | None:
        """要素からタイトルを抽出 - 堅牢版"""
        try:
            # Method 1: .nc-title .title-text
            title_element = ElementSearcher.safe_find_element(element, ".nc-title .title-text")
            if title_element:
                title_text = self._extract_title_text(title_element)
                if title_text:
                    return title_text

            # Method 2: .nc-title直接
            title_element = ElementSearcher.safe_find_element(element, ".nc-title")
            if title_element:
                title_text = self._extract_title_text(title_element)
                if title_text:
                    return title_text

            # Method 3: a[href*='/news/']のテキスト
            url_link = ElementSearcher.safe_find_element(element, "a[href*='/news/']")
            if url_link:
                title_text = self._extract_title_text(url_link)
                if title_text:
                    return title_text

            # Method 4: span要素から検索
            span_elements = ElementSearcher.safe_find_elements(element, "span")
            for span in span_elements:
                span_text = ElementSearcher.safe_get_text(span)
                if span_text and len(span_text.strip()) > 10:
                    span_class = ElementSearcher.safe_get_attribute(span, "class") or ""
                    if not TextCleaner.is_source_name_class(span_class):
                        cleaned_text = TextCleaner.extract_valid_line(span_text)
                        if cleaned_text:
                            return cleaned_text

            return None

        except Exception as e:
            self.logger.debug(f"Title extraction failed: {e}")
            return None

    def _extract_cryptopanic_url(self, element) -> str | None:
        """要素からCryptoPanic URLを抽出"""
        try:
            url_link = ElementSearcher.safe_find_element(element, "a[href*='/news/']")
            if url_link:
                href = ElementSearcher.safe_get_attribute(url_link, "href")
                if href:
                    return href if href.startswith("http") else f"{self.BASE_URL}{href}"
            return None
        except Exception as e:
            self.logger.debug(f"CryptoPanic URL extraction error: {e}")
            return None

    def _extract_published_at(self, element) -> datetime | None:
        """記事の発行日時を抽出"""
        try:
            # 時間要素を探す
            time_elements = ElementSearcher.safe_find_elements(element, ".nc-date time, time, .time, [datetime]")

            for time_elem in time_elements:
                # datetime属性を確認
                datetime_attr = ElementSearcher.safe_get_attribute(time_elem, "datetime")
                if datetime_attr:
                    try:
                        # CryptoPanic特有の形式を処理
                        parsed_dt = self._parse_cryptopanic_datetime(datetime_attr)
                        if parsed_dt:
                            self.logger.debug(f"Parsed datetime from attribute: {parsed_dt}")
                            return parsed_dt
                    except Exception as e:
                        self.logger.debug(f"Failed to parse datetime attribute '{datetime_attr}': {e}")

                # テキストから相対時間を抽出・計算
                time_text = ElementSearcher.safe_get_text(time_elem)
                if time_text:
                    relative_time = self._parse_relative_time(time_text)
                    if relative_time:
                        self.logger.debug(f"Parsed relative time '{time_text}' -> {relative_time}")
                        return relative_time

            # 時間情報が見つからない場合はNoneを返す（フィルタリングされない）
            self.logger.debug("No valid time information found")
            return None

        except Exception as e:
            self.logger.debug(f"Failed to extract published_at: {e}")
            return None

    def _parse_cryptopanic_datetime(self, datetime_str: str) -> datetime | None:
        """CryptoPanic特有のdatetime形式を解析"""
        try:
            import re

            # 形式: "Thu Jul 24 2025 19:27:23 GMT+0000 (Coordinated Universal Time)"
            # 正規表現でdate/time部分を抽出
            pattern = r"(\w+)\s+(\w+)\s+(\d+)\s+(\d+)\s+(\d+):(\d+):(\d+)\s+GMT([+-]\d{4})"
            match = re.match(pattern, datetime_str)

            if not match:
                # dateutilで試行
                try:
                    from dateutil import parser

                    # GMT部分以降を除去して解析
                    cleaned = re.sub(r"\s+GMT.*$", "", datetime_str)
                    return parser.parse(cleaned).replace(tzinfo=UTC)
                except Exception:
                    pass
                return None

            # マッチした場合、構造化して解析
            day_name, month_name, day, year, hour, minute, second, tz_offset = match.groups()

            # 月名を数値に変換
            month_map = {
                "Jan": 1,
                "Feb": 2,
                "Mar": 3,
                "Apr": 4,
                "May": 5,
                "Jun": 6,
                "Jul": 7,
                "Aug": 8,
                "Sep": 9,
                "Oct": 10,
                "Nov": 11,
                "Dec": 12,
            }
            month_num = month_map.get(month_name, 1)

            # datetimeオブジェクトを作成
            dt = datetime(int(year), month_num, int(day), int(hour), int(minute), int(second), tzinfo=UTC)

            return dt

        except Exception as e:
            self.logger.debug(f"Failed to parse CryptoPanic datetime '{datetime_str}': {e}")
            return None

    def _parse_relative_time(self, time_text: str) -> datetime | None:
        """相対時間テキストを実際のdatetimeに変換"""
        try:
            import re
            from datetime import timedelta

            text = time_text.lower().strip()
            now = datetime.now(UTC)

            # 分前 (5min, 10min ago, 30 minutes ago)
            min_match = re.search(r"(\d+)\s*(?:min|minute)s?(?:\s+ago)?", text)
            if min_match:
                minutes = int(min_match.group(1))
                return now - timedelta(minutes=minutes)

            # 時間前 (2h, 5h ago, 3 hours ago)
            hour_match = re.search(r"(\d+)\s*(?:h|hour)s?(?:\s+ago)?", text)
            if hour_match:
                hours = int(hour_match.group(1))
                return now - timedelta(hours=hours)

            # 日前 (1d, 2 days ago)
            day_match = re.search(r"(\d+)\s*(?:d|day)s?(?:\s+ago)?", text)
            if day_match:
                days = int(day_match.group(1))
                return now - timedelta(days=days)

            # "ago"が含まれる場合は相対時間として扱うが、具体的な数値がない場合は1時間前とする
            if "ago" in text:
                self.logger.debug(f"Relative time text '{text}' detected but no specific time found, assuming 1h ago")
                return now - timedelta(hours=1)

            return None

        except Exception as e:
            self.logger.debug(f"Failed to parse relative time '{time_text}': {e}")
            return None

    def _extract_external_url_safe(self, element, fallback_url: str) -> str:
        """安全な外部URL抽出（改良版）"""
        try:
            # Press記事は外部URL抽出をスキップ
            if WebDriverUtils.is_press_article(element):
                self.logger.debug("Press article detected, using CryptoPanic URL")
                return fallback_url

            # まず、データ属性から直接取得を試行
            direct_url = self._extract_url_from_attributes(element)
            if direct_url:
                self.logger.debug(f"✅ Direct URL found: {direct_url}")
                return direct_url

            # 外部リンクアイコンを探す（より多くのパターンを試行）
            link_icon = None
            icon_selectors = [
                ".open-link-icon",
                ".si-external-link",
                ".external-link",
                "a[title*='external']",
                "a[aria-label*='external']",
                ".link-icon",
                "[data-testid*='external']",
            ]

            for selector in icon_selectors:
                try:
                    link_icon = element.find_element(By.CSS_SELECTOR, selector)
                    self.logger.debug(f"✅ Found external link icon with selector: {selector}")
                    break
                except Exception:
                    continue

            if not link_icon:
                self.logger.debug("❌ No external link icon found with any selector, using CryptoPanic URL")
                return fallback_url

            # タブ操作で外部URL取得（タイムアウト延長）
            external_url = self.tab_manager.click_and_get_url(link_icon, timeout=8)

            if external_url and self._is_valid_external_url(external_url):
                self.logger.debug(f"✅ External URL extracted via tab: {external_url}")
                return external_url
            else:
                self.logger.debug(f"❌ External URL extraction failed (url={external_url}), using CryptoPanic URL")
                return fallback_url

        except Exception as e:
            self.logger.debug(f"❌ External URL extraction error: {e}, using fallback")
            return fallback_url

    def _extract_original_url_robust(self, element) -> str | None:
        """外部URL取得 - シンプル版"""
        # Press記事は外部URLなし
        if WebDriverUtils.is_press_article(element):
            return None

        # Method 1: データ属性から直接取得
        direct_url = self._extract_url_from_attributes(element)
        if direct_url:
            return direct_url

        # Method 2: .open-link-iconをクリック
        icon_elements = ElementSearcher.safe_find_elements(element, ".open-link-icon")
        if icon_elements:
            return self._extract_original_url_improved(icon_elements[0])

        return None

    def _extract_url_from_attributes(self, element) -> str | None:
        """データ属性から直接URL取得 - 改良版"""
        try:
            # Method 1: data属性から取得
            data_attrs = [
                "data-url",
                "data-href",
                "data-link",
                "data-external-url",
                "data-original-url",
            ]
            for attr in data_attrs:
                url = ElementSearcher.safe_get_attribute(element, attr)
                if self._is_valid_external_url(url):
                    self.logger.debug(f"📊 Found URL in {attr}: {url}")
                    return url

            # Method 2: 直接的な外部リンク
            links = ElementSearcher.safe_find_elements(element, "a[href]")
            for link in links:
                href = ElementSearcher.safe_get_attribute(link, "href")
                if self._is_valid_external_url(href):
                    self.logger.debug(f"🔗 Direct external link: {href}")
                    return href

            # Method 3: click-area要素（特別処理）
            click_areas = ElementSearcher.safe_find_elements(element, "a.click-area")
            for area in click_areas:
                href = ElementSearcher.safe_get_attribute(area, "href")
                if self._is_valid_external_url(href):
                    self.logger.debug(f"🎯 Click-area external URL: {href}")
                    return href

            # Method 4: 隠れたリンク要素
            all_links = ElementSearcher.safe_find_elements(element, "a")
            for link in all_links:
                href = ElementSearcher.safe_get_attribute(link, "href")
                # より寛容な条件
                if href and href.startswith("http") and not href.startswith(self.BASE_URL):
                    # 広告やリダイレクトでない場合
                    if not any(
                        skip in href
                        for skip in [
                            "/redirect/",
                            "javascript:",
                            "#",
                            "cryptopanic.com",
                        ]
                    ):
                        self.logger.debug(f"🔍 Hidden external link: {href}")
                        return href

        except Exception as e:
            self.logger.debug(f"❌ Attribute URL extraction error: {e}")

        return None

    def _is_valid_external_url(self, url: str) -> bool:
        """有効な外部URLかどうか判定 - 改良版"""
        if not url:
            return False

        return (
            url.startswith("http")
            and not url.startswith(self.BASE_URL)
            and "/redirect/" not in url
            and not url.startswith("javascript:")
            and not url.startswith("#")
            and len(url) > 10  # 最小長チェック
        )

    def _extract_original_url_improved(self, icon_element) -> str | None:
        """アイコンクリックでURL取得 - シンプル版"""
        try:
            url = self.tab_manager.click_and_get_url(icon_element)

            # CryptoPanic内部URLは除外
            if url and not url.startswith(self.BASE_URL):
                return url

        except Exception as e:
            self.logger.debug(f"Click extraction failed: {e}")

        return None

    def _extract_data_source(self, element) -> DataSource | None:
        """記事要素からDataSourceを抽出 - 診断強化版"""
        try:
            # 要素のclass情報をログ出力（診断用）
            element_class = ElementSearcher.safe_get_attribute(element, "class") or ""
            self.logger.debug(f"Processing element with class: {element_class}")

            # タイトルとCryptoPanic URLを取得
            title, cryptopanic_url = self._extract_title_and_url_robust(element)
            if not title:
                self.logger.debug("❌ FAIL: No title found")
                return None

            self.logger.debug(f"✅ Title: {title[:30]}...")
            self.logger.debug(f"✅ CryptoPanic URL: {cryptopanic_url}")

            # Press記事は内部URLのみ使用
            if WebDriverUtils.is_press_article(element):
                self.logger.debug("📰 Press article detected")
                if cryptopanic_url:
                    original_url = self._normalize_url(cryptopanic_url)
                    self.logger.debug(f"✅ Using Press internal URL: {original_url}")
                else:
                    self.logger.debug("❌ FAIL: Press article but no internal URL")
                    return None
            else:
                # 外部URL取得を試行
                self.logger.debug("🔗 Attempting external URL extraction")
                original_url = self._extract_original_url_robust(element)
                if original_url:
                    self.logger.debug(f"✅ External URL found: {original_url}")
                else:
                    # 外部URL取得失敗時は内部URLにフォールバック
                    if cryptopanic_url:
                        original_url = self._normalize_url(cryptopanic_url)
                        self.logger.debug(f"⚠️  Using fallback internal URL: {original_url}")
                    else:
                        self.logger.debug("❌ FAIL: No URL found (external or internal)")
                        return None

            # その他の情報を取得
            published_at = self._extract_published_time(element)
            currencies = self._extract_currencies(element)
            source_domain = self._extract_source_domain(element)

            # DataSource作成
            data_source = DataSource.from_cryptopanic_news(
                title=title.strip(),
                url=original_url,
                published_at=published_at,
                currencies=currencies,
                source_domain=source_domain,
                scraped_at=datetime.now(UTC),
            )

            if data_source.is_valid():
                self.logger.debug("✅ DataSource validation passed")
                return data_source
            else:
                self.logger.debug("❌ FAIL: DataSource validation failed")
                return None

        except Exception as e:
            self.logger.warning(f"Extract error: {e}")
            return None

    def _extract_title_text(self, title_element) -> str | None:
        """タイトルテキストを抽出 - 改良版"""
        try:
            # 直接的なテキスト取得
            direct_text = ElementSearcher.safe_get_text(title_element)
            if direct_text and len(direct_text.strip()) > 3:
                cleaned_text = TextCleaner.extract_valid_line(direct_text)
                if cleaned_text and len(cleaned_text) > 3:
                    self.logger.debug(f"✅ Direct title text: {cleaned_text[:30]}...")
                    return cleaned_text
                else:
                    self.logger.debug(f"❌ Direct text failed cleaning: '{direct_text[:30]}...'")

            # span要素内のテキスト取得
            span_elements = ElementSearcher.safe_find_elements(title_element, "span")
            self.logger.debug(f"Found {len(span_elements)} span elements")

            for i, span in enumerate(span_elements):
                span_class = ElementSearcher.safe_get_attribute(span, "class") or ""
                span_text = ElementSearcher.safe_get_text(span)

                self.logger.debug(
                    f"  Span {i + 1}: class='{span_class}', text='{span_text[:30] if span_text else None}...'"
                )

                # si-source-nameクラスはスキップ（ドメイン名など）
                if TextCleaner.is_source_name_class(span_class):
                    self.logger.debug("  Skipping source name span")
                    continue

                # より寛容な条件
                if span_text and len(span_text.strip()) > 3:
                    cleaned_text = TextCleaner.extract_valid_line(span_text)
                    if cleaned_text and len(cleaned_text) > 3:
                        self.logger.debug(f"✅ Span title text: {cleaned_text[:30]}...")
                        return cleaned_text

            # 最後の手段：より寛容な検証でテキストを取得
            all_text = ElementSearcher.safe_get_text(title_element)
            if all_text:
                # 複数行に分かれている場合の処理
                lines = [line.strip() for line in all_text.split("\n") if line.strip()]
                for line in lines:
                    if len(line) > 5 and not self._is_likely_domain_or_source(line):
                        # 通常の検証が失敗した場合、より寛容な検証を試行
                        cleaned_text = TextCleaner.extract_valid_line(line)
                        if cleaned_text:
                            self.logger.debug(f"✅ Fallback title text: {cleaned_text[:30]}...")
                            return cleaned_text
                        # 基本的な検証のみでタイトルを許可
                        elif self._is_basic_valid_title(line):
                            self.logger.debug(f"✅ Basic valid title text: {line[:30]}...")
                            return line

            self.logger.debug("❌ No valid title text found")
            return None

        except Exception as e:
            self.logger.debug(f"❌ Title text extraction error: {e}")
            return None

    def _is_basic_valid_title(self, text: str) -> bool:
        """基本的なタイトル検証（より寛容）"""
        if not text or len(text.strip()) < 5:
            return False

        text = text.strip()

        # 明らかに無効なパターンのみ除外
        if text.isdigit():
            return False

        # 時間表示のみの場合は除外
        if len(text) < 10 and any(indicator in text.lower() for indicator in ["min", "h", "ago", "hour"]):
            return False

        # ドメイン名のみの場合は除外
        if len(text) < 20 and any(domain in text.lower() for domain in [".com", ".org", ".io"]):
            return False

        return True

    def _is_likely_domain_or_source(self, text: str) -> bool:
        """ドメイン名やソース名らしいテキストを判定"""
        text_lower = text.lower()
        # ドメイン名のパターン
        if "." in text and len(text) < 30:
            return True
        # 一般的なソース名パターン
        source_indicators = [
            "coinpedia",
            "cointelegraph",
            "crypto",
            "bitcoin",
            ".com",
            ".org",
            ".io",
        ]
        return any(indicator in text_lower for indicator in source_indicators)

    def _extract_title_text_robust(self, element) -> str | None:
        """堅牢なタイトルテキスト抽出"""
        if not element:
            return None

        # Method 1: .title-text内のメインスパン
        title_text_elements = ElementSearcher.safe_find_elements(element, ".title-text")
        if title_text_elements:
            title_spans = ElementSearcher.safe_find_elements(title_text_elements[0], "span")
            for span in title_spans:
                class_attr = ElementSearcher.safe_get_attribute(span, "class")
                text = ElementSearcher.safe_get_text(span)

                if not TextCleaner.is_source_name_class(class_attr) and TextCleaner.is_valid_title(text):
                    return text

            # 直接テキストも試行
            direct_text = ElementSearcher.safe_get_text(title_text_elements[0])
            valid_line = TextCleaner.extract_valid_line(direct_text)
            if valid_line:
                return valid_line

        # Method 2: 要素の直接テキスト（フィルタリング強化）
        text = ElementSearcher.safe_get_text(element)
        return TextCleaner.extract_valid_line(text)

    def _extract_published_time(self, element) -> datetime | None:
        """公開時刻を抽出"""
        time_element = ElementSearcher.safe_find_element(element, ".nc-date time")
        if not time_element:
            return datetime.now(UTC)

        datetime_attr = ElementSearcher.safe_get_attribute(time_element, "datetime")
        if not datetime_attr:
            return datetime.now(UTC)

        # GMT+0900 部分を削除してパース
        cleaned = re.sub(r"\s+GMT[+-]\d{4}\s+\([^)]+\)", "", datetime_attr)
        try:
            parsed_dt = datetime.strptime(cleaned, "%a %b %d %Y %H:%M:%S")
            return parsed_dt.replace(tzinfo=UTC)
        except ValueError:
            return datetime.now(UTC)

    def _extract_currencies(self, element) -> list[str]:
        """関連通貨を抽出"""
        currency_links = ElementSearcher.safe_find_elements(element, ".nc-currency a.colored-link")
        return [ElementSearcher.safe_get_text(link) for link in currency_links if ElementSearcher.safe_get_text(link)]

    def _extract_source_domain(self, element) -> str | None:
        """ソースドメインを抽出"""
        source_element = ElementSearcher.safe_find_element(element, ".si-source-domain")
        if source_element:
            return ElementSearcher.safe_get_text(source_element)
        return None

    def _get_article_elements(self) -> list:
        """ニュース記事要素を取得"""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, ".news-row")

            # 有効な記事のみフィルタリング
            filtered_elements = []
            for el in elements:
                if ElementSearcher.safe_find_elements(el, ".nc-title, a[href*='/news/']"):
                    filtered_elements.append(el)

            self.logger.info(f"Found {len(filtered_elements)} news elements (filtered from {len(elements)} total)")
            return filtered_elements

        except Exception as e:
            self.logger.error(f"Failed to get article elements: {e}")
            return []

    def _wait_for_page_load(self) -> None:
        """ページの読み込み完了を待機"""
        try:
            wait = WebDriverWait(self.driver.driver, 15)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".news-row")))
            self.logger.info("CryptoPanic page loaded successfully")
            time.sleep(2)

        except TimeoutException:
            self.logger.warning("Timeout waiting for news elements, continuing anyway")
            time.sleep(3)

    def _normalize_url(self, url: str) -> str:
        """URLを正規化"""
        if url.startswith("http"):
            return url
        return urljoin(self.BASE_URL, url)
