"""
ファイル監視モジュール（ポーリング方式）

【使用方法】
from pathlib import Path
from pipeline.file_watcher import FileWatcher

watcher = FileWatcher(watch_dir=Path("./screenshots"), poll_interval=10.0)

# 未処理の新規ファイルを取得
new_files = watcher.scan_new_files()

for path in new_files:
    record = watcher.load_record(path)
    # ... 処理 ...
    watcher.mark_processed(path)

【処理内容】
1. watch_dir 内の cap_*.json ファイルをスキャン
2. _processed.txt で処理済みファイルを管理し、未処理のみ返す
3. JSONファイルを読み込み CaptureRecord に変換

【依存】
Python標準ライブラリ (json, pathlib), pipeline.models
"""

import json
import logging
from pathlib import Path
from typing import List, Set

from pipeline.models import CaptureRecord

logger = logging.getLogger(__name__)


class FileWatcher:
    def __init__(self, watch_dir: Path, poll_interval: float = 10.0):
        self._watch_dir = watch_dir
        self._poll_interval = poll_interval
        self._watch_dir.mkdir(parents=True, exist_ok=True)
        self._processed_file = self._watch_dir / "_processed.txt"
        self._processed: Set[str] = self._load_processed()

    def scan_new_files(self) -> List[Path]:
        files = sorted(self._watch_dir.glob("cap_*.json"))
        return [f for f in files if f.name not in self._processed]

    def mark_processed(self, path: Path) -> None:
        self._processed.add(path.name)
        with open(self._processed_file, "a", encoding="utf-8") as f:
            f.write(path.name + "\n")

    def load_record(self, path: Path) -> CaptureRecord:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return CaptureRecord(
            capture_id=data.get("capture_id", ""),
            timestamp=data.get("timestamp", ""),
            session=data.get("session", {}),
            user_action=data.get("user_action", {}),
            target=data.get("target", {}),
            app=data.get("app", {}),
            browser=data.get("browser", {}),
            window=data.get("window", {}),
            screenshots=data.get("screenshots", {}),
            json_path=str(path.resolve()),
        )

    def _load_processed(self) -> Set[str]:
        if not self._processed_file.exists():
            return set()
        text = self._processed_file.read_text(encoding="utf-8")
        return {line.strip() for line in text.splitlines() if line.strip()}

    @property
    def poll_interval(self) -> float:
        return self._poll_interval
