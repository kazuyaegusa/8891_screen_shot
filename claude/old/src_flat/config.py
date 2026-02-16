"""
スクリーンショット自動撮影＆画像解析システム - 設定管理モジュール

処理内容:
  .envファイルからOPENAI_API_KEYを読み込み、システム全体の設定を管理する。
  デフォルト値を提供し、環境変数による上書きに対応。

使用方法:
  from config import get_config
  cfg = get_config()
  print(cfg.OPENAI_API_KEY)
  print(cfg.CAPTURE_INTERVAL)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# プロジェクトルート（claude/）を基準にパスを解決
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _PROJECT_ROOT.parent

# .envはリポジトリルートから読み込み
load_dotenv(_REPO_ROOT / ".env")


class Config:
    """システム設定クラス"""

    def __init__(self):
        # OpenAI API
        self.OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
        self.OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-5")

        # 撮影設定
        self.CAPTURE_INTERVAL: float = float(os.environ.get("CAPTURE_INTERVAL", "3.0"))
        self.IMAGE_FORMAT: str = os.environ.get("IMAGE_FORMAT", "png")

        # ストレージ設定
        self.RETENTION_SECONDS: int = int(os.environ.get("RETENTION_SECONDS", "3600"))  # 1時間
        self.MAX_DISK_MB: int = int(os.environ.get("MAX_DISK_MB", "500"))

        # ディレクトリ
        self.SCREENSHOT_DIR: Path = _PROJECT_ROOT / "10_raw" / "screenshots"
        self.ANALYSIS_DIR: Path = _PROJECT_ROOT / "10_raw" / "analysis"
        self.LOG_DIR: Path = _PROJECT_ROOT / "98_tmp"

        # ログ
        self.LOG_FILE: Path = self.LOG_DIR / "daemon.log"

    def ensure_dirs(self):
        """必要なディレクトリを作成する"""
        self.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        self.ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)

    def validate(self) -> List[str]:
        """設定のバリデーション。エラーメッセージのリストを返す（空なら正常）"""
        errors = []
        if not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY が設定されていません (.envファイルを確認)")
        if self.CAPTURE_INTERVAL <= 0:
            errors.append("CAPTURE_INTERVAL は正の数である必要があります")
        return errors


# シングルトンインスタンス
_config_instance: Optional[Config] = None


def get_config() -> Config:
    """設定インスタンスを取得する（シングルトン）"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance
