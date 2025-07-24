"""
スクレイピング用ユーティリティ関数

複雑な処理とよく使う例外処理パターンを集約
"""

import logging
import time
from typing import Any

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


class TabManager:
    """シンプルなタブ管理"""

    def __init__(self, driver, logger=None):
        self.driver = driver
        self.logger = logger or logging.getLogger(__name__)

    def click_and_get_url(self, element, timeout: int = 8) -> str | None:
        """要素をクリックして新しいタブのURLを取得 - 改良版"""
        original_tab = self.driver.current_window_handle
        original_tab_count = len(self.driver.window_handles)

        try:
            # 要素が有効かチェック
            try:
                _ = element.tag_name  # stale check
                is_displayed = element.is_displayed()
                if not is_displayed:
                    self.logger.info("❌ Element is not displayed")
                    return None
            except Exception as e:
                self.logger.info(f"❌ Element is stale: {e}")
                return None

            # 要素までスクロールして確実に表示
            try:
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", element
                )
                time.sleep(0.2)
            except Exception as e:
                self.logger.debug(f"Scroll failed: {e}")

            # クリック実行（JavaScriptクリック）
            self.driver.execute_script("arguments[0].click();", element)

            # 新しいタブの出現を待機
            try:
                WebDriverWait(self.driver, timeout).until(
                    lambda driver: len(driver.window_handles) > original_tab_count
                )
            except TimeoutException:
                self.logger.info("❌ Timeout: No new tab appeared")
                return None

            # 新しいタブに切り替え
            current_tabs = self.driver.window_handles
            new_tabs = [tab for tab in current_tabs if tab != original_tab]

            if not new_tabs:
                self.logger.info("❌ No new tab found")
                return None

            # 最新のタブに切り替え
            new_tab = new_tabs[-1]
            self.driver.switch_to.window(new_tab)

            # ページ読み込み待機（改良版）
            try:
                # 基本的なページ読み込み完了を待機
                WebDriverWait(self.driver, 5).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                # 追加で少し待機（外部サイトのリダイレクト処理を考慮）
                time.sleep(1)
            except TimeoutException:
                # タイムアウトしても続行（一部読み込みで十分な場合がある）
                self.logger.debug("Page load timeout, but proceeding to get URL")
                time.sleep(0.5)

            # URL取得
            url = self.driver.current_url

            # 新しいタブを即座に閉じる
            self.driver.close()

            # 元のタブに戻る
            self.driver.switch_to.window(original_tab)

            self.logger.info(f"✅ URL extracted: {url}")
            return url

        except Exception as e:
            self.logger.info(f"❌ Tab operation failed: {e}")
            try:
                # エラー時は元のタブに戻る
                if self.driver.current_window_handle != original_tab:
                    self.driver.switch_to.window(original_tab)
            except Exception:
                pass
            return None

    def batch_click_and_get_urls(self, elements: list, timeout: int = 3) -> dict[int, str]:
        """複数要素を同時クリックして効率的にURL取得 - 修正版"""
        original_tab = self.driver.current_window_handle
        results = {}

        try:
            self.logger.info(f"🚀 Batch processing {len(elements)} tabs...")

            # 個別にタブオープン処理（より確実）
            for i, element in enumerate(elements):
                try:
                    if not self._is_element_valid(element):
                        self.logger.debug(f"Element {i + 1} is invalid, skipping")
                        results[i] = None
                        continue

                    # 外部リンクアイコンを探す
                    link_icon = None
                    try:
                        link_icon = element.find_element(By.CSS_SELECTOR, ".open-link-icon, .si-external-link")
                    except Exception:
                        self.logger.debug(f"Element {i + 1}: No external link icon found")
                        results[i] = None
                        continue

                    if not link_icon:
                        self.logger.debug(f"Element {i + 1}: No link icon, skipping")
                        results[i] = None
                        continue

                    # タブ数を事前にカウント
                    tabs_before = len(self.driver.window_handles)

                    # 要素をスクロールして表示
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", link_icon
                    )
                    time.sleep(0.2)

                    # クリック実行
                    self.driver.execute_script("arguments[0].click();", link_icon)
                    self.logger.debug(f"Clicked link icon {i + 1}")

                    # 新しいタブの出現を待機
                    try:
                        WebDriverWait(self.driver, 2).until(
                            lambda driver, tabs=tabs_before: len(driver.window_handles) > tabs
                        )

                        # 新しいタブに切り替え
                        new_tabs = [tab for tab in self.driver.window_handles if tab != original_tab]
                        if new_tabs:
                            latest_tab = new_tabs[-1]
                            self.driver.switch_to.window(latest_tab)

                            # URL取得
                            time.sleep(0.5)  # ページ読み込み待機
                            url = self.driver.current_url
                            results[i] = url
                            self.logger.debug(f"Tab {i + 1}: {url}")

                            # タブを即座に閉じる
                            self.driver.close()

                            # 元のタブに戻る
                            self.driver.switch_to.window(original_tab)
                        else:
                            results[i] = None

                    except TimeoutException:
                        self.logger.debug(f"Element {i + 1}: Timeout waiting for new tab")
                        results[i] = None

                except Exception as e:
                    self.logger.debug(f"Failed to process element {i + 1}: {e}")
                    results[i] = None

                    # 安全に元のタブに戻る
                    try:
                        if self.driver.current_window_handle != original_tab:
                            self.driver.switch_to.window(original_tab)
                    except Exception:
                        pass

            success_count = len([url for url in results.values() if url])
            self.logger.info(f"✅ Batch completed: {success_count}/{len(elements)} URLs extracted")

            return results

        except Exception as e:
            self.logger.warning(f"❌ Batch tab operation failed: {e}")
            try:
                # エラー時は元のタブに戻る
                if self.driver.current_window_handle != original_tab:
                    self.driver.switch_to.window(original_tab)
            except Exception:
                pass
            return results

    def _is_element_valid(self, element) -> bool:
        """要素の有効性をチェック"""
        try:
            _ = element.tag_name  # stale check
            return element.is_displayed()
        except Exception:
            return False


class ElementSearcher:
    """安全な要素検索クラス"""

    @staticmethod
    def safe_find_element(element, selector: str, by=By.CSS_SELECTOR) -> Any | None:
        """安全に単一要素を検索"""
        try:
            return element.find_element(by, selector)
        except Exception:
            return None

    @staticmethod
    def safe_find_elements(element, selector: str, by=By.CSS_SELECTOR) -> list:
        """安全に複数要素を検索"""
        try:
            return element.find_elements(by, selector)
        except Exception:
            return []

    @staticmethod
    def safe_get_attribute(element, attr: str) -> str:
        """安全に属性を取得"""
        try:
            return element.get_attribute(attr) or ""
        except Exception:
            return ""

    @staticmethod
    def safe_get_text(element) -> str:
        """安全にテキストを取得"""
        try:
            return element.text.strip()
        except Exception:
            return ""


class TextCleaner:
    """テキストクリーニングクラス"""

    EXCLUDED_WORDS = {"***", "Press", "Sponsored"}
    EXCLUDED_PREFIXES = {"@"}
    EXCLUDED_SUFFIXES = {"min"}

    @staticmethod
    def is_valid_title(text: str, min_length: int = 5, max_length: int = 200) -> bool:
        """有効なタイトルかどうかを判定"""
        if not text or len(text) < min_length or len(text) > max_length:
            return False

        if text.isdigit():
            return False

        if text in TextCleaner.EXCLUDED_WORDS:
            return False

        if any(text.startswith(prefix) for prefix in TextCleaner.EXCLUDED_PREFIXES):
            return False

        if any(text.endswith(suffix) for suffix in TextCleaner.EXCLUDED_SUFFIXES):
            return False

        # ドメイン名パターンをチェック（.com, .org など）
        stripped = text.strip()
        if len(stripped) < 30 and any(domain in stripped.lower() for domain in [".com", ".org", ".io", ".net"]):
            return False

        # 時間表示をチェック（"5min", "1h" など）
        if len(stripped) < 10 and any(
            time_indicator in stripped.lower() for time_indicator in ["min", "hour", "h", "ago"]
        ):
            return False

        return True

    @staticmethod
    def extract_valid_line(text: str) -> str | None:
        """複数行テキストから有効な行を抽出"""
        if not text:
            return None

        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if TextCleaner.is_valid_title(line):
                return line
        return None

    @staticmethod
    def is_source_name_class(class_attr: str) -> bool:
        """ソース名のクラスかどうか判定"""
        return "si-source-name" in class_attr or "hidden-mobile" in class_attr


class WebDriverUtils:
    """WebDriver操作ユーティリティ"""

    @staticmethod
    def is_press_article(element) -> bool:
        """Press記事（sponsored）かどうかを判定"""
        try:
            # class属性でチェック
            class_attr = ElementSearcher.safe_get_attribute(element, "class") or ""
            if "sponsored" in class_attr:
                return True

            # "Press"テキストの存在チェック
            press_elements = ElementSearcher.safe_find_elements(element, ".//*[contains(text(), 'Press')]", By.XPATH)
            if press_elements:
                return True

            # color-orangeクラスのチェック
            orange_elements = ElementSearcher.safe_find_elements(element, ".color-orange")
            for orange_el in orange_elements:
                if "Press" in ElementSearcher.safe_get_text(orange_el):
                    return True

        except Exception:
            pass

        return False

    @staticmethod
    def is_external_url(url: str, base_url: str) -> bool:
        """外部URLかどうか判定"""
        return url and url.startswith("http") and not url.startswith(base_url)
