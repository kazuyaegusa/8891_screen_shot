"""
デーモン対応の常時学習モジュール

【使用方法】
from agent.config import AgentConfig
from agent.continuous_learner import ContinuousLearner

config = AgentConfig()
learner = ContinuousLearner(config)

# 単発実行（1サイクル）
count = learner.run_once()
print(f"新規ワークフロー: {count}")

# デーモン実行（Ctrl+C で停止）
learner.run()

# 停止
learner.stop()

【処理内容】
1. ポーリングで新規キャプチャJSONを検出
2. WorkflowExtractor.extract_incremental() で増分抽出
3. 一定サイクルごとに WorkflowRefiner で品質改善
4. FeedbackStore でフィードバック蓄積
5. 日次で再現性レポート + catalog.json を自動更新

【依存】
agent.config (AgentConfig), agent.models (Workflow),
agent.workflow_extractor (WorkflowExtractor),
agent.workflow_refiner (WorkflowRefiner) [遅延import],
agent.feedback_store (FeedbackStore) [遅延import],
agent.report_generator (ReportGenerator) [遅延import],
time, logging
"""

import logging
import time
from typing import List

from agent.config import AgentConfig
from agent.models import Workflow
from agent.workflow_extractor import WorkflowExtractor

logger = logging.getLogger(__name__)


class ContinuousLearner:
    """新規キャプチャを定期検出しワークフローを増分抽出する常時学習デーモン"""

    def __init__(self, config: AgentConfig):
        self._config = config
        self._extractor = WorkflowExtractor(
            json_dir=config.screenshot_dir,
            workflow_dir=config.workflow_dir,
            model=config.openai_model,
        )
        self._feedback_store = None  # 遅延初期化
        self.poll_interval: int = 30
        self.batch_size: int = 5
        self.refine_interval: int = 10
        self.report_interval: int = 86400  # レポート自動更新間隔（秒）デフォルト24時間
        self._running: bool = False
        self._cycle_count: int = 0
        self._segment_buffer: list = []
        self._last_report_time: float = 0.0

    def run(self) -> None:
        """常時学習ループ（ブロッキング）"""
        self._running = True
        logger.info("常時学習開始 (poll_interval=%ds, refine_interval=%dサイクル)",
                     self.poll_interval, self.refine_interval)

        while self._running:
            self.run_once()
            # poll_interval 秒待機（1秒ごとに _running を確認）
            for _ in range(self.poll_interval):
                if not self._running:
                    break
                time.sleep(1)

        logger.info("常時学習停止")

    def run_once(self) -> int:
        """1サイクル実行。返却: 新規ワークフロー数"""
        new_workflows = self._scan_new_files()
        count = len(new_workflows)

        if count:
            logger.info("新規ワークフロー検出: %d件", count)

        self._cycle_count += 1

        if self._cycle_count % self.refine_interval == 0:
            self._refine_cycle()

        # 日次レポート自動更新
        now = time.time()
        if now - self._last_report_time >= self.report_interval:
            self._report_cycle()
            self._last_report_time = now

        return count

    def _scan_new_files(self) -> List[Workflow]:
        """新規キャプチャをスキャンし増分抽出"""
        return self._extractor.extract_incremental()

    def _refine_cycle(self) -> None:
        """ワークフロー品質改善サイクル"""
        try:
            from pathlib import Path
            from agent.feedback_store import FeedbackStore
            from agent.workflow_refiner import WorkflowRefiner
            from agent.workflow_store import WorkflowStore

            store = WorkflowStore(self._config.workflow_dir)
            feedback_dir = str(Path(self._config.workflow_dir) / "feedback")
            feedback = FeedbackStore(feedback_dir)
            refiner = WorkflowRefiner(store, feedback)
            result = refiner.refine_all()
            logger.info("リファインサイクル完了: %s", result)
        except Exception as e:
            logger.warning("リファインサイクル失敗: %s", e)

    def _report_cycle(self) -> None:
        """再現性レポート + catalog.json 自動更新"""
        try:
            from datetime import datetime
            from pathlib import Path
            from agent.feedback_store import FeedbackStore
            from agent.report_generator import ReportGenerator
            from agent.workflow_store import WorkflowStore

            store = WorkflowStore(self._config.workflow_dir)
            feedback_dir = str(Path(self._config.workflow_dir) / "feedback")
            feedback = FeedbackStore(feedback_dir)
            gen = ReportGenerator(store, feedback)

            # Markdownレポート生成 + catalog.json 更新
            output = gen.generate(format="markdown")

            # reports/ に保存
            reports_dir = Path(self._config.workflow_dir) / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            report_path = reports_dir / f"report_{datetime.now().strftime('%Y%m%d')}.md"
            report_path.write_text(output, encoding="utf-8")
            logger.info("日次レポート自動更新: %s", report_path)
        except Exception as e:
            logger.warning("レポート自動更新失敗: %s", e)

    def stop(self) -> None:
        """常時学習を停止"""
        self._running = False
