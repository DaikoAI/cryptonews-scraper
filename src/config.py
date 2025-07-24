"""
Configuration Module

Railway環境での安全な環境変数読み込み
"""

import os


class Config:
    """環境変数設定管理"""

    # Database
    DATABASE_URL: str | None = None

    # Selenium
    SELENIUM_BROWSER: str = "chrome"
    SELENIUM_REMOTE_URL: str | None = None

    # Logging
    LOG_LEVEL: str = "INFO"

    # Railway Environment Detection
    RAILWAY_ENVIRONMENT: str | None = None
    RAILWAY_PROJECT_ID: str | None = None

    @classmethod
    def load_from_env(cls) -> None:
        """環境変数から設定を読み込み"""

        # Railway Environment Detection (先に設定)
        cls.RAILWAY_ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT")
        cls.RAILWAY_PROJECT_ID = os.getenv("RAILWAY_PROJECT_ID")

        # Database Configuration (Required for Railway)
        cls.DATABASE_URL = os.getenv("DATABASE_URL")
        if not cls.DATABASE_URL and cls.is_railway_environment():
            raise ValueError("DATABASE_URL is required in Railway environment")

        # Selenium Configuration
        cls.SELENIUM_BROWSER = os.getenv("SELENIUM_BROWSER", cls.SELENIUM_BROWSER)
        cls.SELENIUM_REMOTE_URL = os.getenv("SELENIUM_REMOTE_URL")

        # Logging Configuration
        cls.LOG_LEVEL = os.getenv("LOG_LEVEL", cls.LOG_LEVEL)

    @classmethod
    def is_railway_environment(cls) -> bool:
        """Railway環境かどうかチェック"""
        return bool(cls.RAILWAY_ENVIRONMENT or cls.RAILWAY_PROJECT_ID)

    @classmethod
    def is_development_environment(cls) -> bool:
        """開発環境かどうかチェック"""
        return not cls.is_railway_environment()

    @classmethod
    def get_selenium_remote_url(cls) -> str:
        """環境に応じたSelenium Remote URLを取得"""
        if cls.SELENIUM_REMOTE_URL:
            return cls.SELENIUM_REMOTE_URL

        # Railway環境では外部Selenium Gridサービスを使用
        if cls.is_railway_environment():
            return "http://selenium-chrome:4444"  # Railway内部ネットワーク

        # 開発環境ではローカルSelenium Grid
        return "http://localhost:4444"

    @classmethod
    def validate_configuration(cls) -> None:
        """設定の妥当性をチェック"""
        errors = []

        # Railway環境では必須
        if cls.is_railway_environment():
            if not cls.DATABASE_URL:
                errors.append("DATABASE_URL is required in Railway environment")

        # ログレベルの妥当性チェック
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if cls.LOG_LEVEL not in valid_log_levels:
            errors.append(f"LOG_LEVEL must be one of: {', '.join(valid_log_levels)}")

        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")


# 初期化時に環境変数を読み込み
Config.load_from_env()
