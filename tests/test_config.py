"""
Test Configuration Module
"""

import os
from unittest.mock import patch

import pytest

from src.config import Config


class TestConfig:
    """Config設定管理のテスト"""

    def setup_method(self):
        """各テスト前にConfigをリセット"""
        Config.DATABASE_URL = None
        Config.SELENIUM_BROWSER = "chrome"
        Config.SELENIUM_REMOTE_URL = None
        Config.LOG_LEVEL = "INFO"
        Config.RAILWAY_ENVIRONMENT = None
        Config.RAILWAY_PROJECT_ID = None

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://test:test@localhost:5432/test",
            "SELENIUM_BROWSER": "firefox",
            "SELENIUM_REMOTE_URL": "http://custom:4444",
            "LOG_LEVEL": "DEBUG",
        },
        clear=False,
    )
    def test_load_from_env(self):
        """環境変数からの設定読み込みテスト"""
        Config.load_from_env()

        assert Config.DATABASE_URL == "postgresql://test:test@localhost:5432/test"
        assert Config.SELENIUM_BROWSER == "firefox"
        assert Config.SELENIUM_REMOTE_URL == "http://custom:4444"
        assert Config.LOG_LEVEL == "DEBUG"

    @patch.dict(os.environ, {}, clear=True)
    def test_load_from_env_defaults(self):
        """デフォルト値のテスト"""
        Config.load_from_env()

        assert Config.DATABASE_URL is None
        assert Config.SELENIUM_BROWSER == "chrome"
        assert Config.SELENIUM_REMOTE_URL is None
        assert Config.LOG_LEVEL == "INFO"

    @patch.dict(
        os.environ,
        {"RAILWAY_ENVIRONMENT": "production", "DATABASE_URL": "postgresql://test:test@localhost:5432/test"},
        clear=False,
    )
    def test_is_railway_environment_with_env_var(self):
        """Railway環境判定テスト（環境変数あり）"""
        Config.load_from_env()
        assert Config.is_railway_environment() is True
        assert Config.is_development_environment() is False

    @patch.dict(
        os.environ,
        {"RAILWAY_PROJECT_ID": "proj-123", "DATABASE_URL": "postgresql://test:test@localhost:5432/test"},
        clear=False,
    )
    def test_is_railway_environment_with_project_id(self):
        """Railway環境判定テスト（プロジェクトIDあり）"""
        Config.load_from_env()
        assert Config.is_railway_environment() is True
        assert Config.is_development_environment() is False

    @patch.dict(os.environ, {}, clear=True)
    def test_is_development_environment(self):
        """開発環境判定テスト"""
        Config.load_from_env()
        assert Config.is_railway_environment() is False
        assert Config.is_development_environment() is True

    def test_get_selenium_remote_url_with_explicit_url(self):
        """明示的URL設定時のSelenium URL取得テスト"""
        Config.SELENIUM_REMOTE_URL = "http://custom-selenium:4444"

        result = Config.get_selenium_remote_url()
        assert result == "http://custom-selenium:4444"

    def test_get_selenium_remote_url_railway_environment(self):
        """Railway環境でのSelenium URL取得テスト"""
        Config.RAILWAY_ENVIRONMENT = "production"
        Config.SELENIUM_REMOTE_URL = None

        result = Config.get_selenium_remote_url()
        assert result == "http://selenium-chrome:4444"

    def test_get_selenium_remote_url_development_environment(self):
        """開発環境でのSelenium URL取得テスト"""
        Config.RAILWAY_ENVIRONMENT = None
        Config.RAILWAY_PROJECT_ID = None
        Config.SELENIUM_REMOTE_URL = None

        result = Config.get_selenium_remote_url()
        assert result == "http://localhost:4444"

    def test_validate_configuration_success(self):
        """正常な設定のバリデーションテスト"""
        Config.DATABASE_URL = "postgresql://test:test@localhost:5432/test"
        Config.LOG_LEVEL = "INFO"
        Config.RAILWAY_ENVIRONMENT = None

        # エラーが発生しないことを確認
        Config.validate_configuration()

    def test_validate_configuration_missing_database_url_in_railway(self):
        """Railway環境でのDATABASE_URL不足テスト"""
        Config.DATABASE_URL = None
        Config.RAILWAY_ENVIRONMENT = "production"

        with pytest.raises(ValueError, match="DATABASE_URL is required in Railway environment"):
            Config.validate_configuration()

    def test_validate_configuration_invalid_log_level(self):
        """無効なログレベルのバリデーションテスト"""
        Config.LOG_LEVEL = "INVALID"

        with pytest.raises(ValueError, match="LOG_LEVEL must be one of"):
            Config.validate_configuration()

    @patch.dict(os.environ, {"RAILWAY_ENVIRONMENT": "production", "DATABASE_URL": ""}, clear=True)
    def test_railway_environment_requires_database_url(self):
        """Railway環境でのDATABASE_URL必須チェック"""
        with pytest.raises(ValueError, match="DATABASE_URL is required in Railway environment"):
            Config.load_from_env()
