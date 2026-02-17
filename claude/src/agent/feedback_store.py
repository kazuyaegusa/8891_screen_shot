"""
フィードバック永続化モジュール

【使用方法】
from agent.feedback_store import FeedbackStore
from agent.models import ExecutionFeedback

store = FeedbackStore(feedback_dir="./feedback")

# 記録
store.record(feedback)

# ワークフロー別取得
feedbacks = store.get_by_workflow("wf-001")

# 成功率
rate = store.get_success_rate("wf-001")

# ステップ別失敗率
step_rates = store.get_step_failure_rates("wf-001")

# 全件取得
all_fb = store.list_all()

# 件数
n = store.count()

【処理内容】
- ExecutionFeedbackをJSONファイルとして永続化（feedback/{feedback_id}.json）
- ワークフロー別のフィードバック取得・成功率算出
- ステップ別の失敗率算出（改善対象の特定用）

【依存】
agent.models (ExecutionFeedback), json, pathlib, logging
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

from agent.models import ExecutionFeedback

logger = logging.getLogger(__name__)


class FeedbackStore:
    def __init__(self, feedback_dir: str):
        self._dir = Path(feedback_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def record(self, feedback: ExecutionFeedback) -> str:
        """フィードバックを保存。返却: 保存パス"""
        path = self._dir / f"{feedback.feedback_id}.json"
        data = feedback.to_dict()
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("フィードバック保存: %s (success=%s)", feedback.feedback_id, feedback.success)
        return str(path)

    def get_by_workflow(self, workflow_id: str) -> List[ExecutionFeedback]:
        """ワークフローIDでフィードバックを取得"""
        results = []
        for path in self._dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                fb = ExecutionFeedback.from_dict(data)
                if fb.workflow_id == workflow_id:
                    results.append(fb)
            except Exception as e:
                logger.warning("フィードバック読み込みスキップ: %s - %s", path.name, e)
        results.sort(key=lambda f: f.timestamp, reverse=True)
        return results

    def get_success_rate(self, workflow_id: str) -> float:
        """ワークフローの成功率を算出（0.0〜1.0）。データなしの場合は0.0"""
        feedbacks = self.get_by_workflow(workflow_id)
        if not feedbacks:
            return 0.0
        success_count = sum(1 for f in feedbacks if f.success)
        return success_count / len(feedbacks)

    def get_step_failure_rates(self, workflow_id: str) -> Dict[int, float]:
        """ステップ別の失敗率を算出。返却: {step_index: failure_rate}"""
        feedbacks = self.get_by_workflow(workflow_id)
        if not feedbacks:
            return {}
        step_failure_count: Dict[int, int] = {}
        for fb in feedbacks:
            for idx in fb.failed_step_indices:
                step_failure_count[idx] = step_failure_count.get(idx, 0) + 1
        total = len(feedbacks)
        return {idx: count / total for idx, count in step_failure_count.items()}

    def list_all(self) -> List[ExecutionFeedback]:
        """全フィードバック取得（timestamp降順）"""
        feedbacks = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                feedbacks.append(ExecutionFeedback.from_dict(data))
            except Exception as e:
                logger.warning("フィードバック読み込みスキップ: %s - %s", path.name, e)
        feedbacks.sort(key=lambda f: f.timestamp, reverse=True)
        return feedbacks

    def count(self) -> int:
        """保存済みフィードバック数"""
        return len(list(self._dir.glob("*.json")))
