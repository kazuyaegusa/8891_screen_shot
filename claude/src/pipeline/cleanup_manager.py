"""
クリーンアップマネージャ: 学習済みファイルの即時削除・重複排除・古いファイル削除

【使用方法】
from pathlib import Path
from pipeline.cleanup_manager import CleanupManager

manager = CleanupManager(watch_dir=Path("./screenshots"))

# 学習処理済みのJSON+関連画像を即座に削除（最重要）
manager.cleanup_processed_files(processed_set)

# セッション内の全ファイルを削除
manager.cleanup_session(session)

# 古いファイル（デフォルト1時間以上前）を安全削除
manager.cleanup_old_files(retention_sec=3600)

# 重複画像を削除
manager.cleanup_duplicates()

【処理内容】
1. cleanup_processed_files: _processed.txtに記録済みのJSONと関連PNG/JSONを即削除
2. cleanup_session: セッション内の全レコードのファイルを削除
3. cleanup_old_files: 1時間以上前の *_cap_*, *_full_*, *_crop_* を削除
4. cleanup_duplicates: MD5ハッシュで完全重複PNGを削除

【依存】
Python標準ライブラリ (pathlib, time, logging, hashlib, json), pipeline.models
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

    def cleanup_processed_files(self, processed_names: set) -> List[str]:
        """学習処理済みのJSONファイルと関連画像を即座に削除する（最重要）

        processed_names: _processed.txt に記録されたファイル名のset
        JSONファイルの中の screenshots パスも読み取って関連PNGも削除する
        """
        import json as _json

        deleted = []
        if not self._watch_dir.exists():
            return deleted

        for name in list(processed_names):
            json_path = self._watch_dir / name
            if not json_path.exists():
                continue

            # JSON内の関連画像パスを取得して削除
            try:
                data = _json.loads(json_path.read_text(encoding="utf-8"))
                screenshots = data.get("screenshots", {})
                for key in ("full", "cropped", "json"):
                    path_str = screenshots.get(key)
                    if path_str:
                        self._safe_delete(Path(path_str))
                        deleted.append(Path(path_str).name)
            except Exception:
                pass

            # JSONファイル自体を削除
            self._safe_delete(json_path)
            deleted.append(name)

        if deleted:
            logger.info("処理済みファイル %d 件を削除", len(deleted))
        return deleted

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
        # 実際のファイル名パターン: click_cap_*, text_cap_*, shortcut_cap_*, *_full_*, *_crop_*
        patterns = (
            "*_cap_*.json", "*_cap_*.png",
            "*_full_*.png", "*_crop_*.png",
        )

        for pattern in patterns:
            for filepath in self._watch_dir.glob(pattern):
                if filepath.is_file() and filepath.stat().st_mtime < cutoff:
                    self._safe_delete(filepath)
                    deleted.append(filepath.name)

        return deleted

    def cleanup_duplicates(self) -> List[str]:
        """MD5ハッシュで完全重複画像を検出・削除（各グループの最古1枚を残す）"""
        import hashlib
        from collections import defaultdict

        deleted = []
        if not self._watch_dir.exists():
            return deleted

        hashes: defaultdict = defaultdict(list)
        for filepath in sorted(self._watch_dir.glob("*.png")):
            if filepath.is_file():
                h = hashlib.md5(filepath.read_bytes()).hexdigest()
                hashes[h].append(filepath)

        for h, files in hashes.items():
            if len(files) > 1:
                for f in files[1:]:
                    self._safe_delete(f)
                    deleted.append(f.name)

        if deleted:
            logger.info("重複画像 %d 枚を削除", len(deleted))
        return deleted

    def _safe_delete(self, path: Path) -> None:
        if not path.exists():
            return
        try:
            path.unlink()
            logger.debug("削除: %s", path)
        except OSError as e:
            logger.warning("削除失敗 %s: %s", path, e)
