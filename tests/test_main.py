"""
Tests for the Selenium scraper application
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import pytest

from src.constants import (
    DEFAULT_BROWSER,
    DEFAULT_REMOTE_URL_DOCKER,
    DEFAULT_REMOTE_URL_LOCAL,
    ENV_SELENIUM_BROWSER,
    ENV_SELENIUM_REMOTE_URL,
    TEST_URL,
)
from src.main import main, print_banner
from src.scraper import StandaloneChromiumScraper, create_scraper_from_env, scrape_test_page
from src.utils.logger import ColoredFormatter, get_app_logger


class TestLogger(unittest.TestCase):
    """Logger functionality tests"""

    def test_get_app_logger(self):
        """Test logger creation"""
        logger = get_app_logger("test_module")
        assert logger.name == "railway_app.test_module"

    def test_colored_formatter(self):
        """Test colored formatter functionality"""
        import logging

        formatter = ColoredFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        assert "Test message" in formatted
        assert "✅" in formatted  # INFO icon


class TestScraper(unittest.TestCase):
    """Scraper functionality tests"""

    @patch("src.scraper.webdriver.Remote")
    def test_scraper_initialization(self, mock_remote):
        """Test scraper initialization with constants"""
        scraper = StandaloneChromiumScraper()
        assert scraper.browser == DEFAULT_BROWSER
        assert scraper.remote_url == DEFAULT_REMOTE_URL_LOCAL

    @patch("src.scraper.webdriver.Remote")
    def test_scraper_custom_params(self, mock_remote):
        """Test scraper with custom parameters"""
        scraper = StandaloneChromiumScraper(browser="firefox", remote_url="http://custom:4444", timeout=20)
        assert scraper.browser == "firefox"
        assert scraper.remote_url == "http://custom:4444"
        assert scraper.timeout == 20

    @patch("src.scraper.webdriver.Remote")
    def test_scraper_connect_chrome(self, mock_remote):
        """Test Chrome connection"""
        mock_driver = MagicMock()
        mock_driver.capabilities = {"browserName": "chrome", "browserVersion": "90.0"}
        mock_remote.return_value = mock_driver

        scraper = StandaloneChromiumScraper(browser="chrome")
        scraper.connect()

        assert scraper.driver == mock_driver
        mock_remote.assert_called_once()

    @patch("src.scraper.webdriver.Remote")
    def test_scraper_connect_firefox(self, mock_remote):
        """Test Firefox connection"""
        mock_driver = MagicMock()
        mock_driver.capabilities = {"browserName": "firefox", "browserVersion": "85.0"}
        mock_remote.return_value = mock_driver

        scraper = StandaloneChromiumScraper(browser="firefox")
        scraper.connect()

        assert scraper.driver == mock_driver
        mock_remote.assert_called_once()

    def test_scraper_unsupported_browser(self):
        """Test unsupported browser raises error"""
        scraper = StandaloneChromiumScraper(browser="safari")
        with pytest.raises(ValueError, match="Unsupported browser"):
            scraper.connect()

    @patch("src.scraper.webdriver.Remote")
    def test_scraper_get_page(self, mock_remote):
        """Test get_page functionality"""
        mock_driver = MagicMock()
        mock_remote.return_value = mock_driver

        scraper = StandaloneChromiumScraper()
        scraper.connect()

        test_url = "https://example.com"
        scraper.get_page(test_url)

        mock_driver.get.assert_called_once_with(test_url)

    @patch("src.scraper.webdriver.Remote")
    def test_scraper_get_page_info(self, mock_remote):
        """Test get_page_info functionality"""
        mock_driver = MagicMock()
        mock_driver.title = "Test Page"
        mock_driver.current_url = "https://example.com"
        mock_driver.page_source = "<html><body>Test</body></html>"
        mock_driver.capabilities = {"browserName": "chrome", "browserVersion": "90.0"}
        mock_remote.return_value = mock_driver

        scraper = StandaloneChromiumScraper()
        scraper.connect()

        page_info = scraper.get_page_info()

        assert page_info["title"] == "Test Page"
        assert page_info["current_url"] == "https://example.com"
        assert page_info["browser_name"] == "chrome"
        assert page_info["browser_version"] == "90.0"

    @patch("src.scraper.webdriver.Remote")
    @patch("src.scraper.os.makedirs")
    def test_scraper_take_screenshot(self, mock_makedirs, mock_remote):
        """Test screenshot functionality"""
        mock_driver = MagicMock()
        mock_remote.return_value = mock_driver

        scraper = StandaloneChromiumScraper()
        scraper.connect()

        with tempfile.TemporaryDirectory() as temp_dir:
            filepath = scraper.take_screenshot("test.png", temp_dir)
            expected_path = os.path.join(temp_dir, "test.png")
            assert filepath == expected_path
            mock_driver.save_screenshot.assert_called_with(expected_path)

    def test_create_scraper_from_env_defaults(self):
        """Test creating scraper from environment variables with defaults"""
        with patch.dict(os.environ, {}, clear=True):
            scraper = create_scraper_from_env()
            assert scraper.browser == DEFAULT_BROWSER
            assert scraper.remote_url == DEFAULT_REMOTE_URL_LOCAL

    def test_create_scraper_from_env_custom(self):
        """Test creating scraper from custom environment variables"""
        test_env = {
            ENV_SELENIUM_BROWSER: "firefox",
            ENV_SELENIUM_REMOTE_URL: "http://test:4444",
        }
        with patch.dict(os.environ, test_env, clear=True):
            scraper = create_scraper_from_env()
            assert scraper.browser == "firefox"
            assert scraper.remote_url == "http://test:4444"


class TestScrapingFunction(unittest.TestCase):
    """Test the external scraping function"""

    @patch("src.scraper.webdriver.Remote")
    def test_scrape_test_page_function(self, mock_remote):
        """Test the external scrape_test_page function"""
        mock_driver = MagicMock()
        mock_driver.title = "Test Page"
        mock_driver.page_source = "<html><body>Test content</body></html>"
        mock_driver.current_url = TEST_URL
        mock_driver.capabilities = {"browserName": "chrome", "browserVersion": "90.0"}

        # Mock H1 element
        mock_h1 = MagicMock()
        mock_h1.text = "Herman Melville - Moby-Dick"
        mock_driver.find_element.return_value = mock_h1

        mock_remote.return_value = mock_driver

        scraper = StandaloneChromiumScraper()
        scraper.connect()

        # Use the external function
        result = scrape_test_page(scraper)

        assert result["status"] == "success"
        assert result["title"] == "Test Page"
        assert result["h1_text"] == "Herman Melville - Moby-Dick"
        assert result["url"] == TEST_URL
        # Verify that scraper methods were called
        mock_driver.get.assert_called_with(TEST_URL)


class TestMain(unittest.TestCase):
    """Main application tests"""

    def test_print_banner(self):
        """Test banner printing"""
        mock_logger = MagicMock()
        print_banner(mock_logger, "chrome", "http://localhost:4444")

        # Verify banner was printed
        assert mock_logger.info.call_count >= 5
        mock_logger.info.assert_any_call("🚀 Python Railway Template - Selenium Standalone Chromium")

    @patch("src.main.scrape_test_page")
    @patch("src.main.create_scraper_from_env")
    @patch("src.main.get_app_logger")
    def test_main_success(self, mock_logger_func, mock_create_scraper, mock_scrape_func):
        """Test successful main execution"""
        # Setup mocks
        mock_logger = MagicMock()
        mock_logger_func.return_value = mock_logger

        mock_scraper = MagicMock()
        mock_scraper.take_screenshot.return_value = "test_screenshot.png"
        mock_create_scraper.return_value.__enter__.return_value = mock_scraper

        # Mock the external scraping function
        mock_scrape_func.return_value = {
            "status": "success",
            "title": "Test",
            "h1_text": "Test H1",
            "page_source_length": "100",
            "url": TEST_URL,
            "browser_name": "chrome",
            "browser_version": "90.0",
            "execution_mode": "selenium_standalone_chromium",
        }

        # Mock environment variables
        test_env = {
            ENV_SELENIUM_BROWSER: DEFAULT_BROWSER,
            ENV_SELENIUM_REMOTE_URL: DEFAULT_REMOTE_URL_DOCKER,
        }

        with patch.dict(os.environ, test_env, clear=True):
            try:
                main()
            except SystemExit:
                pass  # main() may call sys.exit on success

        # Verify functions were called
        mock_scrape_func.assert_called_once_with(mock_scraper)
        mock_scraper.take_screenshot.assert_called_once()

    @patch("src.main.create_scraper_from_env")
    @patch("src.main.get_app_logger")
    def test_main_exception_handling(self, mock_logger_func, mock_create_scraper):
        """Test main exception handling"""
        mock_logger = MagicMock()
        mock_logger_func.return_value = mock_logger

        # Mock scraper to raise exception
        mock_create_scraper.side_effect = Exception("Connection failed")

        with pytest.raises(SystemExit):
            main()

        # Verify error was logged
        mock_logger.error.assert_called()


if __name__ == "__main__":
    unittest.main()
