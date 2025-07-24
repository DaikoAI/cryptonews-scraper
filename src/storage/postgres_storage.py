"""
PostgreSQL Storage Implementation

Drizzle ORMのdata_sourceテーブルに対応したストレージ実装
"""

import json
from datetime import datetime

import asyncpg

from src.models import DataSource

# BaseStorageを削除し、直接実装
from src.utils.logger import get_app_logger


class PostgresStorage:
    """PostgreSQL用ストレージ実装 - Drizzle ORMのdata_sourceテーブル対応"""

    def __init__(self, connection_string: str | None = None):
        """
        Args:
            connection_string: PostgreSQL接続文字列 (Noneの場合は環境変数から取得)
        """
        from src.config import Config

        self.connection_string = connection_string or Config.DATABASE_URL
        if not self.connection_string:
            raise ValueError("DATABASE_URL environment variable is required")

        self.pool: asyncpg.Pool | None = None
        self.logger = get_app_logger(__name__)

    async def connect(self) -> None:
        """データベース接続プールを作成"""
        if self.pool is None:
            self.logger.info("Creating PostgreSQL connection pool...")
            self.pool = await asyncpg.create_pool(self.connection_string, min_size=1, max_size=10, command_timeout=60)
            self.logger.info("PostgreSQL connection pool created successfully")

    async def save_data_sources(self, data_sources: list[DataSource]) -> int:
        """データソースをdata_sourceテーブルに保存"""
        if not self.pool:
            await self.connect()

        saved_count = 0

        async with self.pool.acquire() as conn:
            async with conn.transaction():
                for data_source in data_sources:
                    try:
                        # 重複チェック (URL基準)
                        if await self._data_source_exists_in_db(conn, data_source.url):
                            self.logger.debug(f"Data source already exists: {data_source.url}")
                            continue

                        # data_sourceテーブルに挿入
                        await self._insert_data_source(conn, data_source)
                        saved_count += 1

                    except Exception as e:
                        self.logger.error(f"Failed to save data source {data_source.url}: {e}")
                        continue

        self.logger.info(f"Saved {saved_count} new data sources to PostgreSQL")
        return saved_count

    async def _data_source_exists_in_db(self, conn: asyncpg.Connection, url: str) -> bool:
        """データソースがdata_sourceテーブルに既に存在するかチェック"""
        result = await conn.fetchval("SELECT 1 FROM data_source WHERE url = $1 LIMIT 1", url)
        return result is not None

    async def _insert_data_source(self, conn: asyncpg.Connection, data_source: DataSource) -> None:
        """データソースをdata_sourceテーブルに挿入"""
        # Drizzleスキーマに合わせた最小限のinsert処理
        # published_atのタイムゾーン情報を削除（PostgreSQLのtimestamp型に合わせる）
        published_at = data_source.published_at
        if published_at and published_at.tzinfo:
            # タイムゾーン情報を削除してナイーブなdatetimeに変換
            published_at = published_at.replace(tzinfo=None)

        # data_sourceテーブルに挿入
        await conn.execute(
            """
            INSERT INTO data_source (
                id, type, url, summary, published_at, raw_content
            ) VALUES ($1, $2, $3, $4, $5, $6)
            """,
            data_source.id,  # id
            data_source.type,  # type
            data_source.url,  # url
            data_source.summary,  # summary
            published_at,  # published_at (タイムゾーンナイーブ)
            (json.dumps(data_source.raw_content) if data_source.raw_content else None),  # raw_content (JSON文字列)
            # created_atは省略してPostgreSQLのdefaultNow()に任せる
        )

        self.logger.debug(f"Inserted data source: {data_source.summary[:50]}...")

    async def get_data_sources(self, limit: int = 100, offset: int = 0) -> list[DataSource]:
        """data_sourceテーブルからデータソースを取得"""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, type, url, summary, published_at, raw_content, created_at
                FROM data_source
                WHERE type = 'news'
                ORDER BY published_at DESC NULLS LAST, created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )

        data_sources = []
        for row in rows:
            try:
                data_source = self._row_to_data_source(row)
                data_sources.append(data_source)
            except Exception as e:
                self.logger.warning(f"Failed to convert row to DataSource: {e}")
                continue

        return data_sources

    def _row_to_data_source(self, row) -> DataSource:
        """データベース行をDataSourceに変換"""
        # raw_contentからメタデータを復元
        raw_content = {}
        if row["raw_content"]:
            try:
                raw_content = json.loads(row["raw_content"])
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse raw_content JSON: {e}")

        return DataSource(
            id=row["id"],
            type=row["type"],
            url=row["url"] or "",
            summary=row["summary"] or "",
            published_at=row["published_at"],
            raw_content=raw_content,
            created_at=row["created_at"],
        )

    async def data_source_exists(self, url: str) -> bool:
        """データソースがdata_sourceテーブルに存在するかチェック"""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            return await self._data_source_exists_in_db(conn, url)

    async def get_latest_published_at(self) -> datetime | None:
        """最新の記事の公開日時を取得（前回取得チェック用）"""
        if not self.pool:
            await self.connect()

        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT MAX(published_at) FROM data_source
                WHERE type = 'news' AND published_at IS NOT NULL
                """
            )

            # 結果がある場合はタイムゾーン情報を確保
            if result and not result.tzinfo:
                from datetime import UTC

                result = result.replace(tzinfo=UTC)

            return result

    async def close(self) -> None:
        """接続プールを閉じる"""
        if self.pool:
            self.logger.info("Closing PostgreSQL connection pool...")
            await self.pool.close()
            self.pool = None
            self.logger.info("PostgreSQL connection pool closed")


async def create_postgres_storage() -> PostgresStorage:
    """環境変数からPostgreSQLストレージを作成"""
    storage = PostgresStorage()
    await storage.connect()
    return storage
