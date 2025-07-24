"""
Test DataSource Model
"""

from datetime import UTC, datetime

from src.models import DataSource


class TestDataSource:
    """DataSourceモデルのテスト"""

    def test_create_basic_data_source(self):
        """基本的なDataSource作成テスト"""
        ds = DataSource(
            url="https://example.com/news/1",
            summary="Test News Title",
        )

        assert ds.url == "https://example.com/news/1"
        assert ds.summary == "Test News Title"
        assert ds.type == "news"
        assert ds.id is not None
        assert ds.created_at is not None
        assert ds.raw_content == {}

    def test_create_data_source_with_all_fields(self):
        """全フィールド指定でのDataSource作成テスト"""
        published_at = datetime(2025, 1, 24, 12, 0, 0, tzinfo=UTC)
        raw_content = {"source": "test", "currencies": ["BTC"]}

        ds = DataSource(
            url="https://example.com/news/1",
            summary="Test News Title",
            published_at=published_at,
            raw_content=raw_content,
            type="news",
            id="test-id-123",
        )

        assert ds.url == "https://example.com/news/1"
        assert ds.summary == "Test News Title"
        assert ds.published_at == published_at
        assert ds.raw_content == raw_content
        assert ds.type == "news"
        assert ds.id == "test-id-123"

    def test_is_valid(self):
        """バリデーションテスト"""
        # 有効なDataSource
        valid_ds = DataSource(
            url="https://example.com/news/1",
            summary="Test News Title",
        )
        assert valid_ds.is_valid() is True

        # URLなし
        invalid_ds1 = DataSource(url="", summary="Test Title")
        assert invalid_ds1.is_valid() is False

        # サマリーなし
        invalid_ds2 = DataSource(url="https://example.com", summary="")
        assert invalid_ds2.is_valid() is False

        # 空白のみのサマリー
        invalid_ds3 = DataSource(url="https://example.com", summary="   ")
        assert invalid_ds3.is_valid() is False

    def test_to_dict(self):
        """辞書変換テスト"""
        published_at = datetime(2025, 1, 24, 12, 0, 0, tzinfo=UTC)
        raw_content = {"source": "test"}

        ds = DataSource(
            url="https://example.com/news/1",
            summary="Test News Title",
            published_at=published_at,
            raw_content=raw_content,
            id="test-id-123",
        )

        result = ds.to_dict()

        assert result["id"] == "test-id-123"
        assert result["type"] == "news"
        assert result["url"] == "https://example.com/news/1"
        assert result["summary"] == "Test News Title"
        assert result["published_at"] == published_at
        assert result["raw_content"] == raw_content
        assert "created_at" in result

    def test_from_cryptopanic_news(self):
        """CryptoPanicニュースからの作成テスト"""
        scraped_at = datetime(2025, 1, 24, 12, 30, 0, tzinfo=UTC)
        published_at = datetime(2025, 1, 24, 12, 0, 0, tzinfo=UTC)

        ds = DataSource.from_cryptopanic_news(
            title="Bitcoin Price Surges",
            url="https://cryptopanic.com/news/12345/Bitcoin-Price-Surges",
            published_at=published_at,
            currencies=["BTC", "ETH"],
            source_domain="coindesk.com",
            scraped_at=scraped_at,
        )

        assert ds.summary == "Bitcoin Price Surges"
        assert ds.url == "https://cryptopanic.com/news/12345/Bitcoin-Price-Surges"
        assert ds.published_at == published_at
        assert ds.type == "news"

        # raw_contentの検証
        assert ds.raw_content["source"] == "cryptopanic"
        assert ds.raw_content["currencies"] == ["BTC", "ETH"]
        assert ds.raw_content["source_domain"] == "coindesk.com"
        assert ds.raw_content["scraped_at"] == scraped_at.isoformat()

    def test_from_cryptopanic_news_minimal(self):
        """最小限のフィールドでのCryptoPanicニュース作成テスト"""
        ds = DataSource.from_cryptopanic_news(
            title="Test News",
            url="https://cryptopanic.com/news/123",
        )

        assert ds.summary == "Test News"
        assert ds.url == "https://cryptopanic.com/news/123"
        assert ds.raw_content["source"] == "cryptopanic"
        assert "currencies" not in ds.raw_content  # 空の値は除外される
        assert "source_domain" not in ds.raw_content
        assert "scraped_at" not in ds.raw_content

    def test_repr(self):
        """文字列表現テスト"""
        ds = DataSource(
            url="https://example.com/very-long-url-that-should-be-truncated",
            summary="Very long summary that should be truncated for display purposes",
            id="test-123",
        )

        repr_str = repr(ds)

        assert "DataSource" in repr_str
        assert "test-123" in repr_str
        assert "news" in repr_str
        assert "https://example.com/very-long-url-that-should-be-t" in repr_str
        assert "Very long summary that should" in repr_str
