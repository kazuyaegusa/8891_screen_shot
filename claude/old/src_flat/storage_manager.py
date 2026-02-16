"""
スクリーンショット自動撮影＆画像解析システム - ストレージ管理モジュール

処理内容:
  古いスクリーンショットの自動削除（デフォルト1時間保持）、
  解析結果のJSONLファイルへの追記（日別ファイル）、
  ディスク使用量の監視を行う。

使用方法:
  from storage_manager import cleanup_old_screenshots, append_analysis, get_disk_usage_mb

  # 古いファイルを削除
  deleted = cleanup_old_screenshots(screenshot_dir, retention_seconds=3600)

  # 解析結果を追記
  append_analysis(analysis_dir, result_dict)

  # ディスク使用量を確認
  usage = get_disk_usage_mb(screenshot_dir)
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List


def cleanup_old_screenshots(screenshot_dir: Path, retention_seconds: int = 3600) -> List[str]:
    """
    指定時間より古いスクリーンショットを削除する。

    Args:
        screenshot_dir: スクリーンショット保存ディレクトリ
        retention_seconds: 保持期間（秒）。デフォルト3600秒（1時間）

    Returns:
        削除されたファイル名のリスト
    """
    deleted = []
    now = time.time()
    cutoff = now - retention_seconds

    if not screenshot_dir.exists():
        return deleted

    for filepath in screenshot_dir.glob("screenshot_*"):
        if filepath.is_file() and filepath.stat().st_mtime < cutoff:
            filepath.unlink()
            deleted.append(filepath.name)

    return deleted


def append_analysis(analysis_dir: Path, result: dict) -> Path:
    """
    解析結果をJSONLファイルに追記する。日別でファイルを分割。

    Args:
        analysis_dir: 解析結果の保存先ディレクトリ
        result: 解析結果の辞書

    Returns:
        書き込み先のJSONLファイルパス
    """
    analysis_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    jsonl_path = analysis_dir / f"analysis_{today}.jsonl"

    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")

    return jsonl_path


def get_disk_usage_mb(directory: Path) -> float:
    """
    ディレクトリ内の全ファイルの合計サイズをMB単位で返す。

    Args:
        directory: 対象ディレクトリ

    Returns:
        合計サイズ（MB）
    """
    if not directory.exists():
        return 0.0

    total_bytes = sum(f.stat().st_size for f in directory.rglob("*") if f.is_file())
    return total_bytes / (1024 * 1024)
