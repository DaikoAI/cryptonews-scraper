"""
Colored Logger Utility for Python Railway Template

提供美しい色付きログ出力功能
"""

import logging
import os
from datetime import datetime

from src.constants import (
    ANSI_RESET,
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


def setup_logger(name: str) -> logging.Logger:
    """
    ロガーを設定する

    Args:
        name: ロガー名

    Returns:
        設定されたロガー
    """
    logger = logging.getLogger(name)

    # 環境変数からログレベルを取得（デフォルト: INFO）
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # ログレベルの変換
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    numeric_level = level_map.get(log_level, logging.INFO)
    logger.setLevel(numeric_level)

    # ハンドラが既に存在する場合はスキップ
    if logger.handlers:
        return logger

    # コンソールハンドラを作成
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)

    # フォーマッタを作成
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    console_handler.setFormatter(formatter)

    # ハンドラをロガーに追加
    logger.addHandler(console_handler)

    # 上位ロガーへの伝播を防ぐ
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

    return setup_logger(logger_name)


# デフォルトロガー
logger = get_app_logger()
