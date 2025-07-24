"""
CryptoPanic News Scraper

メインスクレイピングアプリケーション
data_sourceテーブル対応版 - 効率的な差分更新
"""

import json
import os
from datetime import datetime

from src.models import DataSource
from src.scrapers import CryptoPanicScraper
from src.storage import PostgresStorage
from src.utils.logger import get_app_logger
from src.webdriver import create_webdriver_from_env


async def check_for_updates(storage: PostgresStorage) -> datetime | None:
    """前回取得時刻をチェック - 効率的な差分判定用"""
    try:
        last_published = await storage.get_latest_published_at()
        logger = get_app_logger(__name__)

        if last_published:
            logger.info(f"✅ Last article published: {last_published}")
        else:
            logger.info("🆕 No previous articles found - first run")

        return last_published
    except Exception as e:
        logger = get_app_logger(__name__)
        logger.warning(f"⚠️ Could not check last update: {e}")
        return None


async def setup_storage() -> PostgresStorage | None:
    """PostgreSQL接続をセットアップ"""
    logger = get_app_logger(__name__)

    try:
        storage = PostgresStorage()
        await storage.connect()
        logger.info("📊 PostgreSQL connected successfully")
        return storage
    except Exception as e:
        logger.warning(f"❌ PostgreSQL connection failed: {e}")
        logger.info("💾 Will fallback to JSON file storage")
        return None


def filter_new_articles(data_sources: list[DataSource], last_published: datetime | None) -> list[DataSource]:
    """新しい記事のみをフィルタリング - 効率的な差分抽出"""
    if not last_published:
        return data_sources

    new_articles = []
    for ds in data_sources:
        # 公開日時が取得できない場合は新しいものとして扱う
        if not ds.published_at or ds.published_at > last_published:
            new_articles.append(ds)

    return new_articles


async def save_to_fallback_json(data_sources: list[DataSource]) -> None:
    """JSONファイルへのフォールバック保存"""
    logger = get_app_logger(__name__)

    json_data = {
        "scraped_at": datetime.now().isoformat(),
        "count": len(data_sources),
        "data_sources": [ds.to_dict() for ds in data_sources],
    }

    os.makedirs("reports", exist_ok=True)
    json_file = f"reports/crypto_news_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2, default=str)

    logger.info(f"💾 Saved {len(data_sources)} articles to {json_file}")


async def run_scraping() -> None:
    """メインスクレイピング処理 - 効率的な差分更新"""
    logger = get_app_logger(__name__)
    logger.info("🚀 Starting efficient CryptoPanic scraping...")

    # 1. PostgreSQL接続確認
    storage = await setup_storage()
    last_published_at = None

    if storage:
        last_published_at = await check_for_updates(storage)

    # 2. WebDriverでスクレイピング実行
    with create_webdriver_from_env() as driver:
        scraper = CryptoPanicScraper(driver)
        all_data_sources = scraper.run_scraping()

    logger.info(f"📄 Scraped {len(all_data_sources)} total articles")

    # 3. 新しい記事のフィルタリング（効率化ポイント）
    new_data_sources = filter_new_articles(all_data_sources, last_published_at)

    # 4. 早期終了: 新しい記事がない場合（CPU節約）
    if not new_data_sources:
        logger.info("⚡ No new articles - terminating early to save CPU")
        if storage:
            await storage.close()
        return

    logger.info(f"🆕 Found {len(new_data_sources)} new articles")

    # 5. データ保存
    saved_successfully = False

    if storage:
        try:
            saved_count = await storage.save_data_sources(new_data_sources)
            logger.info(f"✅ Saved {saved_count} articles to PostgreSQL")
            saved_successfully = True
        except Exception as e:
            logger.error(f"❌ PostgreSQL save failed: {e}")
        finally:
            await storage.close()

    # 6. フォールバック保存
    if not saved_successfully:
        await save_to_fallback_json(new_data_sources)


async def main():
    """メインエントリーポイント"""
    logger = get_app_logger(__name__)

    try:
        await run_scraping()
        logger.info("✅ Scraping completed successfully")

    except Exception as e:
        logger.error(f"💥 Scraping failed: {e}")
        raise


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
