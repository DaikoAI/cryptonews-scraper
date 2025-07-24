"""
Colored Logger Utility for Python Railway Template

提供美しい色付きログ出力功能
"""

import logging
import sys

from src.constants import (
    ANSI_BOLD,
    ANSI_GRAY,
    ANSI_RESET,
    DEFAULT_LOG_LEVEL,
    LOG_COLORS,
    LOG_ICONS,
)


class ColoredFormatter(logging.Formatter):
    """カスタムフォーマッター - ログレベルごとに色分け"""

    def format(self, record: logging.LogRecord) -> str:
        """ログレコードをフォーマット"""
        # 色とアイコンを取得
        color = LOG_COLORS.get(record.levelname, "")
        icon = LOG_ICONS.get(record.levelname, "")

        # レベル名を色付けし、アイコンを追加
        colored_level = f"{color}{ANSI_BOLD}{icon} {record.levelname}{ANSI_RESET}"

        # メッセージを色付け
        colored_message = f"{color}{record.getMessage()}{ANSI_RESET}"

        # タイムスタンプを薄い色で
        timestamp = f"{ANSI_GRAY}{self.formatTime(record, '%Y-%m-%d %H:%M:%S')}{ANSI_RESET}"

        return f"{timestamp} {colored_level} {colored_message}"


def setup_logger(name: str = __name__, level: int = DEFAULT_LOG_LEVEL, enable_colors: bool = True) -> logging.Logger:
    """
    色付きロガーを設定

    Args:
        name: ロガー名
        level: ログレベル
        enable_colors: 色付きを有効にするか

    Returns:
        設定済みロガー
    """
    logger = logging.getLogger(name)

    # 既にハンドラーが設定されている場合はそのまま返す
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # コンソールハンドラー作成
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # フォーマッター設定
    if enable_colors and sys.stdout.isatty():  # ターミナルでのみ色付け
        formatter = ColoredFormatter()
    else:
        # 色なしフォーマッター
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 親ロガーへの伝播を防ぐ
    logger.propagate = False

    return logger


def get_app_logger(module_name: str | None = None) -> logging.Logger:
    """
    アプリケーション用ロガーを取得

    Args:
        module_name: モジュール名（__name__を渡す）

    Returns:
        色付きロガー
    """
    if module_name:
        logger_name = f"railway_app.{module_name.split('.')[-1]}"
    else:
        logger_name = "railway_app"

    return setup_logger(logger_name, level=DEFAULT_LOG_LEVEL)


# デフォルトロガー
logger = get_app_logger()
