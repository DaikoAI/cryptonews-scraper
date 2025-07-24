"""
CryptoPanic専用スクレイパー - 100%成功率を目指す堅牢版

docs/target.htmlの構造に最適化されたスクレイピング実装
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

from src.models import DataSource
from src.scrapers.base import BaseScraper
from src.utils.scraping_utils import ElementSearcher, TabManager, TextCleaner, WebDriverUtils


class CryptoPanicScraper(BaseScraper):
    """CryptoPanic専用スクレイパー - 高速並列版"""

    BASE_URL = "https://cryptopanic.com"

    def __init__(self, driver):
        super().__init__(driver)
        self.tab_manager = TabManager(driver.driver, self.logger)

        # 並列処理設定
        self.max_workers = 2  # 並列スレッド数
        self.batch_size = 3  # バッチサイズ（さらに小さく）
        self.driver_lock = threading.Lock()  # WebDriver操作のロック

        self.logger.info(f"🚀 Parallel processing: {self.max_workers} workers, batch size: {self.batch_size}")

    def get_source_name(self) -> str:
        return "cryptopanic"

    def get_base_url(self) -> str:
        return f"{self.BASE_URL}/"

    def scrape_articles(self) -> list[DataSource]:
        """記事をスクレイピング - スクロール対応版"""
        try:
            # 画面サイズを大きく設定
            self.driver.driver.set_window_size(1920, 1080)
            self.logger.info("Set browser window size to 1920x1080")

            self._wait_for_page_load()

            # ページを最下部までスクロールして全要素をロード
            self._scroll_to_load_all_elements()

            # 記事要素を取得
            elements = self._get_article_elements()
            if not elements:
                self.logger.warning("No article elements found")
                return []

            self.logger.info(f"Found {len(elements)} article elements")
            return self._process_article_elements(elements)

        except Exception as e:
            self.logger.error(f"Failed to scrape articles: {e}")
            return []

    def _scroll_to_load_all_elements(self) -> None:
        """ページを最下部までスクロールして全要素をロード"""
        try:
            self.logger.info("🔄 Scrolling to load all elements...")

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
                self.logger.info(f"Scrolled {scroll_attempts}/{max_attempts}, height: {new_height}")

            # 最後にページトップに戻る
            self.driver.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)

            self.logger.info(f"✅ Scroll completed after {scroll_attempts} attempts")

        except Exception as e:
            self.logger.warning(f"Scroll failed: {e}")

    def _scroll_element_into_view(self, element) -> bool:
        """要素を画面内に表示"""
        try:
            # 要素までスクロール
            self.driver.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element
            )
            time.sleep(0.3)  # スクロール完了を待機

            # 要素が可視かチェック
            is_visible = self.driver.driver.execute_script(
                """
                var rect = arguments[0].getBoundingClientRect();
                return (rect.top >= 0 && rect.left >= 0 &&
                        rect.bottom <= window.innerHeight &&
                        rect.right <= window.innerWidth);
            """,
                element,
            )

            if is_visible:
                self.logger.debug("✅ Element is now visible")
                return True
            else:
                self.logger.debug("⚠️ Element scrolled but still not fully visible")
                return False

        except Exception as e:
            self.logger.debug(f"❌ Scroll element error: {e}")
            return False

    def _process_article_elements(self, elements: list) -> list[DataSource]:
        """記事要素を軽量並列処理 - エラー対策版"""
        initial_element_count = len(elements)
        data_sources = []
        successful = 0
        failed = 0

        self.logger.info(f"🚀 Processing {initial_element_count} articles with light parallelism...")

        # 小さなバッチで安全に並列処理
        batch_size = 3  # 小さなバッチサイズ
        max_workers = 2  # 最小限の並列度

        for batch_start in range(0, initial_element_count, batch_size):
            batch_end = min(batch_start + batch_size, initial_element_count)
            batch_indices = list(range(batch_start, batch_end))

            self.logger.info(f"🔄 Processing batch: articles {batch_start + 1}-{batch_end}")

            # バッチを軽量並列処理
            batch_results = self._process_batch_safe(batch_indices, max_workers)

            # 結果をマージ
            for result in batch_results:
                if result["success"] and result["data_source"]:
                    data_sources.append(result["data_source"])
                    successful += 1
                    self.logger.info(f"[{result['index'] + 1}] ✅ {result['data_source'].summary[:50]}...")
                else:
                    failed += 1
                    self.logger.info(f"[{result['index'] + 1}] ❌ Failed: {result.get('error', 'Unknown')}")

        self.logger.info(f"🎯 Final results: {successful} successful, {failed} failed out of {initial_element_count}")
        return data_sources

    def _process_batch_safe(self, batch_indices: list[int], max_workers: int) -> list[dict]:
        """安全なバッチ並列処理"""
        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 各記事を並列で処理
            future_to_index = {executor.submit(self._process_single_article_safe, i): i for i in batch_indices}

            # 完了順に結果を収集
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    result["index"] = index
                    results.append(result)
                except Exception as e:
                    self.logger.warning(f"Article {index + 1} processing failed: {e}")
                    results.append({"index": index, "success": False, "data_source": None, "error": str(e)})

        # インデックス順にソート
        results.sort(key=lambda x: x["index"])
        return results

    def _process_single_article_safe(self, index: int) -> dict:
        """単一記事を安全に処理（WebDriver競合回避版）- タブ無効版"""
        try:
            # WebDriverアクセスは慎重にロック
            with self.driver_lock:
                element = self._get_element_by_index(index)
                if not element:
                    return {"success": False, "data_source": None, "error": "Element not found"}

                # 基本チェック
                try:
                    element.tag_name  # stale check
                    if not element.is_displayed():
                        return {"success": False, "data_source": None, "error": "Element not displayed"}
                except Exception as e:
                    return {"success": False, "data_source": None, "error": f"Element stale: {e}"}

                # タイトルとCryptoPanic URLを取得（タブ操作なし）
                title = self._extract_title_from_element(element)
                cryptopanic_url = self._extract_cryptopanic_url(element)

                if not title or not cryptopanic_url:
                    return {'success': False, 'data_source': None, 'error': 'Title or URL not found'}

                # 外部URL抽出を試行（安全版）
                final_url = self._extract_external_url_safe(element, cryptopanic_url)

                # DataSource作成
                try:
                    published_at = self._extract_published_at(element)
                    data_source = DataSource.from_cryptopanic_news(
                        title=title,
                        url=final_url,  # 外部URLまたはCryptoPanic URL
                        published_at=published_at,
                        scraped_at=datetime.now(UTC)
                    )
                except Exception as e:
                    return {'success': False, 'data_source': None, 'error': f'DataSource creation failed: {e}'}

            # ロック外で検証
            if data_source and data_source.is_valid():
                return {"success": True, "data_source": data_source, "error": None}
            else:
                return {"success": False, "data_source": None, "error": "Invalid data source"}

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
            self.logger.debug(f"Title extraction error: {e}")
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
                        from dateutil import parser

                        return parser.parse(datetime_attr)
                    except Exception:
                        pass

                # テキストから時間を抽出
                time_text = ElementSearcher.safe_get_text(time_elem)
                if time_text and any(
                    indicator in time_text.lower() for indicator in ["h", "min", "hour", "day", "ago"]
                ):
                    # 相対時間の場合は現在時刻を返す
                    return datetime.now(UTC)

            # デフォルトは現在時刻
            return datetime.now(UTC)

        except Exception as e:
            self.logger.debug(f"Failed to extract published_at: {e}")
            return datetime.now(UTC)

    def _extract_external_url_safe(self, element, fallback_url: str) -> str:
        """安全な外部URL抽出（タブ操作最小化版）"""
        try:
            # Press記事は外部URL抽出をスキップ
            if WebDriverUtils.is_press_article(element):
                self.logger.debug("Press article detected, using CryptoPanic URL")
                return fallback_url

            # 外部リンクアイコンを探す
            try:
                link_icon = element.find_element(By.CSS_SELECTOR, ".open-link-icon, .si-external-link")
            except Exception:
                self.logger.debug("No external link icon found, using CryptoPanic URL")
                return fallback_url

            # タブ操作で外部URL取得（最小限）
            external_url = self.tab_manager.click_and_get_url(link_icon, timeout=3)

            if external_url and self._is_valid_external_url(external_url):
                self.logger.debug(f"External URL extracted: {external_url}")
                return external_url
            else:
                self.logger.debug("External URL extraction failed, using CryptoPanic URL")
                return fallback_url

        except Exception as e:
            self.logger.debug(f"External URL extraction error: {e}, using fallback")
            return fallback_url

    def _get_current_article_count(self) -> int:
        """現在のページの記事数を取得"""
        try:
            current_elements = self.driver.find_elements(By.CSS_SELECTOR, ".news-row")

            # 有効な記事のみカウント
            valid_count = 0
            for el in current_elements:
                if ElementSearcher.safe_find_elements(el, ".nc-title, a[href*='/news/']"):
                    valid_count += 1

            return valid_count
        except Exception:
            return 0

    def _get_element_by_index(self, index: int) -> any:
        """インデックスによる要素の動的再取得 - 範囲チェック強化"""
        try:
            # 現在のページ状態で要素を再取得
            current_elements = self.driver.find_elements(By.CSS_SELECTOR, ".news-row")

            # 有効な記事のみフィルタリング（元の処理と同じ）
            filtered_elements = []
            for el in current_elements:
                if ElementSearcher.safe_find_elements(el, ".nc-title, a[href*='/news/']"):
                    filtered_elements.append(el)

            if index < len(filtered_elements):
                element = filtered_elements[index]
                self.logger.info(f"✅ Element {index + 1} re-fetched successfully")
                return element
            else:
                self.logger.warning(f"❌ Element {index + 1} out of range (current: {len(filtered_elements)})")
                return None

        except Exception as e:
            self.logger.warning(f"❌ Failed to re-fetch element {index + 1}: {e}")
            return None

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
            data_attrs = ["data-url", "data-href", "data-link", "data-external-url", "data-original-url"]
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
                    if not any(skip in href for skip in ["/redirect/", "javascript:", "#", "cryptopanic.com"]):
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
            if direct_text and len(direct_text.strip()) > 3:  # より寛容に
                cleaned_text = TextCleaner.extract_valid_line(direct_text)
                if cleaned_text and len(cleaned_text) > 3:  # より寛容に
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

            # 最後の手段：すべてのテキストノードを取得
            all_text = ElementSearcher.safe_get_text(title_element)
            if all_text:
                # 複数行に分かれている場合の処理
                lines = [line.strip() for line in all_text.split("\n") if line.strip()]
                for line in lines:
                    if len(line) > 10 and not self._is_likely_domain_or_source(line):
                        cleaned_text = TextCleaner.extract_valid_line(line)
                        if cleaned_text:
                            self.logger.debug(f"✅ Fallback title text: {cleaned_text[:30]}...")
                            return cleaned_text

            self.logger.debug("❌ No valid title text found")
            return None

        except Exception as e:
            self.logger.debug(f"❌ Title text extraction error: {e}")
            return None

    def _is_likely_domain_or_source(self, text: str) -> bool:
        """ドメイン名やソース名らしいテキストを判定"""
        text_lower = text.lower()
        # ドメイン名のパターン
        if "." in text and len(text) < 30:
            return True
        # 一般的なソース名パターン
        source_indicators = ["coinpedia", "cointelegraph", "crypto", "bitcoin", ".com", ".org", ".io"]
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
