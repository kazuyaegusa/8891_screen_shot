"""
ワークフロー永続化・検索モジュール

【使用方法】
from agent.workflow_store import WorkflowStore
from agent.models import Workflow

store = WorkflowStore(workflow_dir="./workflows")

# 保存
store.save(workflow)

# 取得
wf = store.get("wf-001")

# 一覧
all_wfs = store.list_all()

# キーワード検索（スコアリング付き推薦）
results = store.search("Finder フォルダ", feedback_store=feedback_store)

# 削除
store.delete("wf-001")

【処理内容】
- ワークフローをJSONファイルとして永続化（workflows/{id}.json）
- ID/名前/タグ/説明でのキーワード検索（重み付きスコアリングで推薦順ソート）
- スコア = keyword_match × 3.0 + success_rate × 2.0 + log(execution_count + 1) × 0.3
- deprecated ワークフローは検索結果から除外
- 重複排除（同名ワークフローの統合）

【依存】
agent.models (Workflow), json, pathlib
"""

import json
import logging
import math
from pathlib import Path
from typing import List, Optional

from agent.models import Workflow, WorkflowStatus

logger = logging.getLogger(__name__)


class WorkflowStore:
    def __init__(self, workflow_dir: str):
        self._dir = Path(workflow_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, workflow: Workflow) -> str:
        """ワークフローを保存。返却: 保存パス"""
        path = self._dir / f"{workflow.workflow_id}.json"
        data = workflow.to_dict()
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("ワークフロー保存: %s (%s)", workflow.name, path)
        return str(path)

    def get(self, workflow_id: str) -> Optional[Workflow]:
        """IDでワークフロー取得"""
        path = self._dir / f"{workflow_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Workflow.from_dict(data)
        except Exception as e:
            logger.error("ワークフロー読み込み失敗: %s - %s", workflow_id, e)
            return None

    def list_all(self) -> List[Workflow]:
        """全ワークフロー取得（confidence降順）"""
        workflows = []
        for path in sorted(self._dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                workflows.append(Workflow.from_dict(data))
            except Exception as e:
                logger.warning("ワークフロー読み込みスキップ: %s - %s", path.name, e)
        workflows.sort(key=lambda w: w.confidence, reverse=True)
        return workflows

    def search(self, query: str, feedback_store=None) -> List[Workflow]:
        """キーワード検索 + 重み付きスコアリングでワークフロー推薦

        スコア = keyword_match × 3.0 + success_rate × 2.0 + log(execution_count + 1) × 0.3
        deprecated ワークフローは除外。feedback_store が渡された場合は成功率も加味する。
        """
        query_lower = query.lower()
        keywords = query_lower.split()
        scored: list[tuple[float, Workflow]] = []
        for wf in self.list_all():
            # deprecated を除外
            if wf.status == WorkflowStatus.DEPRECATED.value:
                continue

            searchable = " ".join([
                wf.name.lower(),
                wf.description.lower(),
                wf.app_name.lower(),
                " ".join(t.lower() for t in wf.tags),
            ])
            if not all(kw in searchable for kw in keywords):
                continue

            keyword_match = 1.0
            success_rate = 0.0
            if feedback_store is not None:
                success_rate = feedback_store.get_success_rate(wf.workflow_id)

            score = (
                keyword_match * 3.0
                + success_rate * 2.0
                + math.log(wf.execution_count + 1) * 0.3
            )
            scored.append((score, wf))

        scored.sort(key=lambda t: t[0], reverse=True)
        return [wf for _, wf in scored]

    def delete(self, workflow_id: str) -> bool:
        """ワークフロー削除"""
        path = self._dir / f"{workflow_id}.json"
        if path.exists():
            path.unlink()
            logger.info("ワークフロー削除: %s", workflow_id)
            return True
        return False

    def find_duplicate(self, name: str) -> Optional[Workflow]:
        """同名ワークフローの検索（重複排除用）"""
        name_lower = name.lower()
        for wf in self.list_all():
            if wf.name.lower() == name_lower:
                return wf
        return None

    def count(self) -> int:
        """保存済みワークフロー数"""
        return len(list(self._dir.glob("*.json")))
