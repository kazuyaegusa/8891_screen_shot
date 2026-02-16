"""
クリーンアップマネージャ: セッション処理済みファイルおよび古いファイルの削除

【使用方法】
from pathlib import Path
from pipeline.cleanup_manager import CleanupManager
from pipeline.models import Session

manager = CleanupManager(watch_dir=Path("./screenshots"))

# セッション内の全ファイルを削除
manager.cleanup_session(session)

# 古いファイル（デフォルト1時間以上前）を安全削除
manager.cleanup_old_files(retention_sec=3600)

【処理内容】
1. cleanup_session: セッション内の全レコードの json_path, full screenshot, cropped screenshot を削除
2. cleanup_old_files: watch_dir 内の cap_*.json, full_*.png, crop_*.png で
   更新日時が retention_sec 以上前のファイルを安全に削除
   （参考: storage_manager.py の cleanup_old_screenshots パターン）

【依存】
Python標準ライブラリ (pathlib, time, logging), pipeline.models
"""

import logging
import time
from pathlib import Path
from typing import List

from pipeline.models import Session

logger = logging.getLogger(__name__)


class CleanupManager:
    def __init__(self, watch_dir: Path):
        self._watch_dir = watch_dir

    def cleanup_session(self, session: Session) -> None:
        for record in session.records:
            self._safe_delete(Path(record.json_path))
            full = record.screenshots.get("full")
            if full:
                self._safe_delete(Path(full))
            cropped = record.screenshots.get("cropped")
            if cropped:
                self._safe_delete(Path(cropped))

    def cleanup_old_files(self, retention_sec: int = 3600) -> List[str]:
        deleted = []
        if not self._watch_dir.exists():
            return deleted

        cutoff = time.time() - retention_sec
        patterns = ("cap_*.json", "full_*.png", "crop_*.png")

        for pattern in patterns:
            for filepath in self._watch_dir.glob(pattern):
                if filepath.is_file() and filepath.stat().st_mtime < cutoff:
                    self._safe_delete(filepath)
                    deleted.append(filepath.name)

        return deleted

    def _safe_delete(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            path.unlink()
            logger.debug("削除: %s", path)
        except OSError as e:
            logger.warning("削除失敗 %s: %s", path, e)
