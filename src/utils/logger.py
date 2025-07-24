"""
Colored Logger Utility for Python Railway Template

提供美しい色付きログ出力功能
"""

import logging
import sys
from datetime import datetime

from src.constants import (
    ANSI_RESET,
    DEFAULT_LOG_LEVEL,
    LOG_COLORS,
)


class ColoredFormatter(logging.Formatter):
    """カスタムフォーマッター - ログレベルごとに色分け"""

    def format(self, record: logging.LogRecord) -> str:
        """ログレコードをフォーマット"""
        # 色を取得
        color = LOG_COLORS.get(record.levelname, "")

        # タイムスタンプを正確に作成（LogRecordの時刻からdatetimeオブジェクトを作成）
        dt = datetime.fromtimestamp(record.created)
        timestamp = f"[{dt.strftime('%Y-%m-%dT%H:%M:%S')}.{dt.microsecond // 1000:03d}Z]"
        level_tag = f"[{record.levelname}]"
        message = record.getMessage()

        # 全体メッセージを構築
        full_message = f"{timestamp} {level_tag} {message}"

        # 色が設定されている場合は全体に色を適用
        if color:
            return f"{color}{full_message}{ANSI_RESET}"
        else:
            return full_message


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
