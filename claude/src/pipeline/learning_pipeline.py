"""
常時学習パイプライン: メインオーケストレータ + CLI

【使用方法】
# Python から
from pipeline.config import PipelineConfig
from pipeline.learning_pipeline import LearningPipeline

config = PipelineConfig.from_env()
pipeline = LearningPipeline(config)
pipeline.run()       # 常時実行
pipeline.run_once()  # 1サイクルのみ（テスト用）

# CLI から
python -m pipeline.learning_pipeline --watch-dir ./screenshots --once
python -m pipeline.learning_pipeline --provider openai --model gpt-5

【処理内容】
メインループ:
1. ResourceGuard でリソース監視・スロットリング
2. FileWatcher で新規 cap_*.json ファイルをスキャン
3. SessionBuilder でレコードをセッションに区切る
4. PatternExtractor (AIClient経由) でスキル抽出
5. SkillWriter でスキルを SKILL.md として書き出し
6. CleanupManager で処理済みファイルを削除
7. poll_sec 間隔でループ

run_once の場合のみ SessionBuilder.flush() で残りバッファも処理する。

【依存】
pipeline 全モジュール, signal, argparse, time, logging
"""

import argparse
import logging
import signal
import time
from pathlib import Path

from pipeline.ai_client import AIClient
from pipeline.cleanup_manager import CleanupManager
from pipeline.config import PipelineConfig
from pipeline.file_watcher import FileWatcher
from pipeline.models import ExtractedSkill, Session
from pipeline.pattern_extractor import PatternExtractor
from pipeline.resource_guard import ResourceGuard
from pipeline.session_builder import SessionBuilder
from pipeline.skill_writer import SkillWriter

logger = logging.getLogger(__name__)


class LearningPipeline:
    # 古いファイルの定期クリーンアップ間隔（秒）
    _CLEANUP_INTERVAL = 600  # 10分ごと
    # 古いファイルの保持期間（秒）: 1時間以上前のファイルを削除
    _RETENTION_SEC = 3600

    def __init__(self, config: PipelineConfig):
        self._config = config
        self._running = False
        self._last_cleanup_time = 0.0

        self._resource_guard = ResourceGuard(
            cpu_limit=config.cpu_limit,
            mem_limit_mb=config.mem_limit,
        )
        self._file_watcher = FileWatcher(
            watch_dir=config.watch_dir,
            poll_interval=config.poll_sec,
        )
        self._session_builder = SessionBuilder(
            gap_seconds=config.session_gap,
            max_records=config.session_max,
        )
        self._ai_client = AIClient(
            provider=config.ai_provider,
            model=config.ai_model,
        )
        self._pattern_extractor = PatternExtractor(
            ai_client=self._ai_client,
            min_confidence=config.min_confidence,
        )
        self._skill_writer = SkillWriter(skills_dir=config.skills_dir)
        self._cleanup_manager = CleanupManager(watch_dir=config.watch_dir)

    def run(self) -> None:
        self._running = True
        self._resource_guard.setup_low_priority()
        logger.info("パイプライン開始: watch_dir=%s", self._config.watch_dir)

        while self._running:
            self._process_cycle()
            time.sleep(self._config.poll_sec)

        logger.info("パイプライン停止")

    def run_once(self) -> None:
        self._running = True
        logger.info("パイプライン1回実行: watch_dir=%s", self._config.watch_dir)
        self._process_cycle()

        remaining = self._session_builder.flush()
        if remaining:
            self._process_session(remaining)

        logger.info("パイプライン1回実行完了")

    def stop(self) -> None:
        self._running = False

    def _process_cycle(self) -> None:
        self._resource_guard.check_and_throttle()
        new_files = self._file_watcher.scan_new_files()

        for file in new_files:
            record = self._file_watcher.load_record(file)
            session = self._session_builder.add_record(record)
            if session:
                self._process_session(session)
            self._file_watcher.mark_processed(file)

        # 学習成功・失敗に関わらず、古いファイルを定期的に削除
        now = time.time()
        if now - self._last_cleanup_time > self._CLEANUP_INTERVAL:
            deleted = self._cleanup_manager.cleanup_old_files(
                retention_sec=self._RETENTION_SEC,
            )
            if deleted:
                logger.info("古いファイルを%d件削除", len(deleted))
            self._last_cleanup_time = now

    def _process_session(self, session: Session) -> None:
        logger.info(
            "セッション処理: %s (app=%s, records=%d)",
            session.session_id, session.app_name, len(session.records),
        )
        skills = self._pattern_extractor.extract(session)
        for skill in skills:
            if self._skill_writer.skill_exists(skill.name):
                self._skill_writer.update_skill(skill)
            else:
                self._skill_writer.write_skill(skill)
        self._cleanup_manager.cleanup_session(session)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="常時学習パイプライン")
    parser.add_argument("--watch-dir", type=str, help="監視ディレクトリ")
    parser.add_argument("--provider", type=str, help="AIプロバイダ (openai)")
    parser.add_argument("--model", type=str, help="AIモデル名")
    parser.add_argument("--once", action="store_true", help="1回だけ実行")
    args = parser.parse_args()

    config = PipelineConfig.from_env()

    if args.watch_dir:
        config.watch_dir = Path(args.watch_dir)
    if args.provider:
        config.ai_provider = args.provider
    if args.model:
        config.ai_model = args.model

    pipeline = LearningPipeline(config)
    signal.signal(signal.SIGINT, lambda s, f: pipeline.stop())
    signal.signal(signal.SIGTERM, lambda s, f: pipeline.stop())

    if args.once:
        pipeline.run_once()
    else:
        pipeline.run()


if __name__ == "__main__":
    main()
