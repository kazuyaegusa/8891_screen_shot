"""
リソース監視・スロットリングモジュール

【使用方法】
from pipeline.resource_guard import ResourceGuard

guard = ResourceGuard(cpu_limit=30, mem_limit_mb=500)
guard.setup_low_priority()

# ループ内で呼び出し、リソース超過時は自動スリープ
guard.check_and_throttle()

# 現在のリソース状況を取得
stats = guard.get_stats()
# => {"cpu_percent": 15.2, "memory_mb": 120.5, "disk_usage_mb": 450.3}

【処理内容】
1. プロセス優先度を最低に設定（os.nice(19)）
2. CPU使用率・メモリ使用量を監視し、閾値超過時に適応的スリープ
3. ディスク使用量の計測（storage_manager パターン参照）

【依存】
psutil, pathlib
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict

import psutil

logger = logging.getLogger(__name__)


class ResourceGuard:
    def __init__(self, cpu_limit: int = 30, mem_limit_mb: int = 500):
        self._cpu_limit = cpu_limit
        self._mem_limit_mb = mem_limit_mb
        self._process = psutil.Process()
        self._watch_dir: Path = Path("./screenshots")

    def setup_low_priority(self) -> None:
        try:
            os.nice(19)
        except PermissionError:
            logger.warning("os.nice(19) に失敗（権限不足）。通常優先度で継続")
        except OSError as e:
            logger.warning("os.nice(19) に失敗: %s。通常優先度で継続", e)

    def check_and_throttle(self) -> None:
        cpu = psutil.cpu_percent(interval=0.1)
        mem_mb = self._process.memory_info().rss / (1024 * 1024)

        if cpu > self._cpu_limit:
            sleep_sec = min((cpu - self._cpu_limit) / self._cpu_limit * 2, 5.0)
            logger.info("CPU %.1f%% > %d%% → %.1f秒スリープ", cpu, self._cpu_limit, sleep_sec)
            time.sleep(sleep_sec)

        if mem_mb > self._mem_limit_mb:
            sleep_sec = min((mem_mb - self._mem_limit_mb) / self._mem_limit_mb * 2, 5.0)
            logger.info("メモリ %.1fMB > %dMB → %.1f秒スリープ", mem_mb, self._mem_limit_mb, sleep_sec)
            time.sleep(sleep_sec)

    def get_stats(self) -> Dict:
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_mb": round(self._process.memory_info().rss / (1024 * 1024), 1),
            "disk_usage_mb": round(self._get_disk_usage_mb(self._watch_dir), 1),
        }

    def _get_disk_usage_mb(self, directory: Path) -> float:
        if not directory.exists():
            return 0.0
        total_bytes = sum(f.stat().st_size for f in directory.rglob("*") if f.is_file())
        return total_bytes / (1024 * 1024)
