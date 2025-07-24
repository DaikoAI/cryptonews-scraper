"""
CryptoPanic News Scraper

メインスクレイピングアプリケーション
効率的な差分更新 - 新規記事がある場合のみスクレイピング実行
"""

from datetime import datetime

from src.scrapers import CryptoPanicScraper
from src.storage import PostgresStorage
from src.utils.logger import get_app_logger
from src.webdriver import create_webdriver_from_env


async def get_last_published_timestamp(storage: PostgresStorage) -> datetime | None:
    """データベースから前回取得した最新記事の公開日時を取得"""
    try:
        logger = get_app_logger(__name__)
        logger.info("📅 Checking last published timestamp...")

        last_published = await storage.get_latest_published_at()

        if last_published:
            logger.info(f"✅ Found previous latest article: {last_published}")
        else:
            logger.info("🆕 First run - no previous articles found")

        return last_published
    except Exception as e:
        logger = get_app_logger(__name__)
        logger.error(f"❌ Failed to get last published timestamp: {e}")
        return None


async def connect_to_database() -> PostgresStorage | None:
    """PostgreSQLデータベースに接続"""
    logger = get_app_logger(__name__)
    logger.info("🔌 Connecting to database...")

    try:
        storage = PostgresStorage()
        await storage.connect()
        logger.info("✅ Database connected successfully")
        return storage
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return None


async def scrape_and_save_new_articles() -> None:
    """新規記事のスクレイピングと保存"""
    logger = get_app_logger(__name__)
    logger.info("🚀 Starting CryptoPanic news scraper...")

    # データベース接続
    storage = await connect_to_database()
    last_published_at = None

    if storage:
        last_published_at = await get_last_published_timestamp(storage)

    # News element取得とフィルタリング
    with create_webdriver_from_env() as driver:
        scraper = CryptoPanicScraper(driver)
        filtered_elements = scraper.get_filtered_elements_by_date(last_published_at)

        if not filtered_elements:
            logger.info("⚡ No new articles found - process completed")
            if storage:
                await storage.close()
            return

        logger.info(f"📰 Found {len(filtered_elements)} new articles - starting scraping")
        scraped_articles = scraper.scrape_filtered_articles(filtered_elements)

    logger.info(f"📄 Scraped {len(scraped_articles)} articles")

    # データベース保存
    if storage and scraped_articles:
        try:
            logger.info(f"💾 Saving {len(scraped_articles)} articles to database...")
            saved_count = await storage.save_data_sources(scraped_articles)

            # 保存結果の詳細サマリー
            if saved_count == len(scraped_articles):
                logger.info(f"✅ Successfully saved all {saved_count} articles to database")
            elif saved_count > 0:
                skipped_count = len(scraped_articles) - saved_count
                logger.warning(
                    f"⚠️ Saved {saved_count}/{len(scraped_articles)} articles ({skipped_count} skipped due to duplicates/validation errors)"
                )
            else:
                logger.warning(f"⚠️ No new articles saved (all {len(scraped_articles)} were duplicates or invalid)")

        except Exception as e:
            logger.error(f"❌ Database save failed: {e}")
        finally:
            await storage.close()
    else:
        if not storage:
            logger.warning("⚠️ No database connection - articles not saved")
        elif not scraped_articles:
            logger.warning("⚠️ No articles to save")

    logger.info("🎉 Process completed successfully")


async def main():
    """アプリケーションエントリーポイント"""
    logger = get_app_logger(__name__)

    try:
        await scrape_and_save_new_articles()

    except KeyboardInterrupt:
        logger.info("⏹️ Process interrupted by user")

    except Exception as e:
        logger.error(f"💥 Unexpected error occurred: {e}")
        raise


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
