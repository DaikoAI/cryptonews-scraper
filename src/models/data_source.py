"""
Data Source Model

data_sourceテーブル用のデータモデル
"""

import uuid
from datetime import UTC, datetime
from typing import Any


class DataSource:
    """data_sourceテーブル用データモデル"""

    def __init__(
        self,
        *,
        url: str,
        summary: str,  # タイトルを格納
        published_at: datetime | None = None,
        raw_content: dict[str, Any] | None = None,
        type: str = "news",
        id: str | None = None,
        created_at: datetime | None = None,
    ):
        """
        Args:
            url: 記事URL
            summary: 記事タイトル
            published_at: 公開日時
            raw_content: 追加メタデータ（辞書形式、JSONとして保存）
            type: データタイプ（デフォルト："news"）
            id: ユニークID（Noneの場合は自動生成）
            created_at: 作成日時（Noneの場合は現在時刻）
        """
        self.id = id or str(uuid.uuid4())
        self.type = type
        self.url = url
        self.summary = summary
        self.published_at = published_at
        self.raw_content = raw_content or {}
        self.created_at = created_at or datetime.now(UTC)

    def is_valid(self) -> bool:
        """基本的なバリデーション"""
        # URL の基本チェック
        if not self.url or not isinstance(self.url, str) or len(self.url.strip()) == 0:
            return False

        # URLが有効な形式かチェック
        url_stripped = self.url.strip()
        if not (url_stripped.startswith("http://") or url_stripped.startswith("https://")):
            return False

        # summary (タイトル) の基本チェック
        if not self.summary or not isinstance(self.summary, str) or len(self.summary.strip()) < 3:
            return False

        # typeの基本チェック
        if not self.type or not isinstance(self.type, str):
            return False

        # idの基本チェック
        if not self.id or not isinstance(self.id, str):
            return False

        return True

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "type": self.type,
            "url": self.url,
            "summary": self.summary,
            "published_at": self.published_at,
            "raw_content": self.raw_content,
            "created_at": self.created_at,
        }

    @classmethod
    def from_cryptopanic_news(
        cls,
        *,
        title: str,
        url: str,
        published_at: datetime | None = None,
        currencies: list[str] | None = None,
        source_domain: str | None = None,
        scraped_at: datetime | None = None,
    ) -> "DataSource":
        """CryptoPanicニュースからDataSourceを作成"""

        # raw_contentに追加メタデータを格納
        raw_content = {
            "source": "cryptopanic",
            "scraped_at": scraped_at.isoformat() if scraped_at else None,
            "currencies": currencies or [],
            "source_domain": source_domain,
        }

        # 空の値を除外（None、空文字列、空リスト）
        raw_content = {k: v for k, v in raw_content.items() if v is not None and v != "" and v != []}

        return cls(
            url=url,
            summary=title,
            published_at=published_at,
            raw_content=raw_content,
            type="news",
        )

    def __repr__(self) -> str:
        return (
            f"DataSource(id='{self.id}', type='{self.type}', "
            f"url='{self.url[:50]}...', summary='{self.summary[:30]}...')"
        )
