"""
Test CryptoPanic Scraper
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

from src.models import DataSource
from src.scrapers.cryptopanic import CryptoPanicScraper


class MockWebElement:
    """モックWebElement"""

    def __init__(self, text="", href="", datetime_attr="", class_attr=""):
        self.text = text
        self._href = href
        self._datetime = datetime_attr
        self._class = class_attr
        self.tag_name = "div"

    def get_attribute(self, name):
        if name == "href":
            return self._href
        elif name == "datetime":
            return self._datetime
        elif name == "class":
            return self._class
        return ""

    def find_element(self, by, value):
        # 簡単なモック実装
        if ".title-text span" in value:
            return MockWebElement(text="Test Bitcoin News Title")
        elif "time[datetime]" in value:
            return MockWebElement(datetime_attr="Thu Jul 24 2025 20:52:42 GMT+0900 (Japan Standard Time)")
        elif ".si-source-domain" in value:
            return MockWebElement(text="coindesk.com")
        return MockWebElement()

    def find_elements(self, by, value):
        if "a.colored-link" in value:
            return [
                MockWebElement(text="BTC"),
                MockWebElement(text="ETH"),
            ]
        return []


class TestCryptoPanicScraper:
    """CryptoPanicスクレイパーのテスト"""

    def setup_method(self):
        """各テスト前のセットアップ"""
        self.mock_driver = Mock()
        self.mock_driver.driver = Mock()
        self.scraper = CryptoPanicScraper(self.mock_driver)

    def test_get_source_name(self):
        """ソース名取得テスト"""
        assert self.scraper.get_source_name() == "cryptopanic"

    def test_get_base_url(self):
        """ベースURL取得テスト"""
        assert self.scraper.get_base_url() == "https://cryptopanic.com/"

    @patch("time.sleep")
    def test_wait_for_page_load_success(self, mock_sleep):
        """ページ読み込み待機成功テスト"""
        mock_wait = Mock()
        mock_wait.until.return_value = True

        with patch("src.scrapers.cryptopanic.WebDriverWait", return_value=mock_wait):
            self.scraper._wait_for_page_load()

        mock_wait.until.assert_called_once()
        mock_sleep.assert_called_once_with(2)

    @patch("time.sleep")
    def test_wait_for_page_load_timeout(self, mock_sleep):
        """ページ読み込みタイムアウトテスト"""
        from selenium.common.exceptions import TimeoutException

        mock_wait = Mock()
        mock_wait.until.side_effect = TimeoutException()

        with patch("src.scrapers.cryptopanic.WebDriverWait", return_value=mock_wait):
            self.scraper._wait_for_page_load()

        mock_sleep.assert_called_once_with(3)

    def test_get_article_elements_success(self):
        """記事要素取得成功テスト"""
        mock_elements = [MockWebElement(), MockWebElement()]
        self.mock_driver.find_elements.return_value = mock_elements

        result = self.scraper._get_article_elements()

        assert len(result) == 2
        self.mock_driver.find_elements.assert_called()

    def test_get_article_elements_fallback(self):
        """記事要素取得フォールバックテスト"""
        # 最初の呼び出しは空のリストを返す
        mock_sponsored_element = MockWebElement(class_attr="news-row sponsored")
        mock_normal_element = MockWebElement(class_attr="news-row news-row-link")

        self.mock_driver.find_elements.side_effect = [
            [],  # 最初の呼び出し（.news-row.news-row-link）
            [mock_sponsored_element, mock_normal_element],  # フォールバック呼び出し
        ]

        result = self.scraper._get_article_elements()

        # sponsoredは除外される
        assert len(result) == 1

    def test_extract_title_and_url_success(self):
        """タイトル・URL抽出成功テスト"""
        mock_element = Mock()
        mock_title_cell = Mock()
        mock_title_text = MockWebElement(text="Test News Title")

        # a.nc-title要素のモック設定
        mock_title_cell.get_attribute.return_value = "https://cryptopanic.com/news/123"
        mock_title_cell.find_element.return_value = mock_title_text

        # 親要素のモック設定
        mock_element.find_element.return_value = mock_title_cell

        title, url = self.scraper._extract_title_and_url(mock_element)

        assert title == "Test News Title"
        assert url == "https://cryptopanic.com/news/123"

    def test_extract_published_time_success(self):
        """公開日時抽出成功テスト"""
        mock_element = Mock()
        mock_time_element = MockWebElement(datetime_attr="Thu Jul 24 2025 20:52:42 GMT+0900 (Japan Standard Time)")
        mock_element.find_element.return_value = mock_time_element

        result = self.scraper._extract_published_time(mock_element)

        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 7
        assert result.day == 24

    def test_extract_published_time_fallback(self):
        """公開日時抽出フォールバックテスト"""
        from selenium.common.exceptions import NoSuchElementException

        mock_element = Mock()
        mock_element.find_element.side_effect = NoSuchElementException()

        result = self.scraper._extract_published_time(mock_element)

        assert isinstance(result, datetime)
        # フォールバック（現在時刻）が返される

    def test_extract_currencies_success(self):
        """通貨抽出成功テスト"""
        mock_element = Mock()
        mock_currency_cell = Mock()
        mock_currency_links = [
            MockWebElement(text="BTC"),
            MockWebElement(text="ETH"),
            MockWebElement(text="BTC"),  # 重複
        ]

        mock_element.find_element.return_value = mock_currency_cell
        mock_currency_cell.find_elements.return_value = mock_currency_links

        result = self.scraper._extract_currencies(mock_element)

        assert result == ["BTC", "ETH"]  # 重複は除去される

    def test_extract_source_domain_success(self):
        """ソースドメイン抽出成功テスト"""
        mock_element = Mock()
        mock_source_element = MockWebElement(text="coindesk.com")
        mock_element.find_element.return_value = mock_source_element

        result = self.scraper._extract_source_domain(mock_element)

        assert result == "coindesk.com"

    def test_normalize_url_absolute(self):
        """絶対URL正規化テスト"""
        result = self.scraper._normalize_url("https://example.com/news/123")
        assert result == "https://example.com/news/123"

    def test_normalize_url_relative_with_slash(self):
        """相対URL（/付き）正規化テスト"""
        result = self.scraper._normalize_url("/news/123")
        assert result == "https://cryptopanic.com/news/123"

    def test_normalize_url_relative_without_slash(self):
        """相対URL（/なし）正規化テスト"""
        result = self.scraper._normalize_url("news/123")
        assert result == "https://cryptopanic.com/news/123"

    def test_extract_data_source_success(self):
        """DataSource抽出成功テスト"""
        mock_element = MockWebElement()

        # モック要素の設定を詳細に行う
        with patch.object(self.scraper, "_extract_title_and_url", return_value=("Test Title", "/news/123")):
            with patch.object(self.scraper, "_extract_published_time", return_value=datetime.now(UTC)):
                with patch.object(self.scraper, "_extract_currencies", return_value=["BTC"]):
                    with patch.object(self.scraper, "_extract_source_domain", return_value="coindesk.com"):
                        result = self.scraper._extract_data_source(mock_element)

        assert isinstance(result, DataSource)
        assert result.summary == "Test Title"
        assert result.url == "https://cryptopanic.com/news/123"
        assert result.raw_content["source"] == "cryptopanic"
        assert result.raw_content["currencies"] == ["BTC"]
        assert result.raw_content["source_domain"] == "coindesk.com"

    def test_extract_data_source_invalid(self):
        """無効なDataSource抽出テスト"""
        mock_element = MockWebElement()

        # タイトル・URLが取得できない場合
        with patch.object(self.scraper, "_extract_title_and_url", return_value=(None, None)):
            result = self.scraper._extract_data_source(mock_element)

        assert result is None
