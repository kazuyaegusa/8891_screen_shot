"""
クロスセッション性能分析モジュール（kework-agi MetaAnalyzer準拠）

【使用方法】
from agent.meta_analyzer import MetaAnalyzer
from agent.workflow_store import WorkflowStore
from agent.feedback_store import FeedbackStore

store = WorkflowStore(workflow_dir="./workflows")
feedback = FeedbackStore(feedback_dir="./feedback")
analyzer = MetaAnalyzer(store, feedback)

# 週次レポート生成
report = analyzer.generate_report(days=7)

# 回帰検出
has_regression = analyzer.detect_regression("wf-001")

# 改善提案
suggestions = analyzer.suggest_improvements()

【処理内容】
- generate_report: 指定期間のフィードバックを集計し、アプリ別統計・失敗ランキング・
  使用頻度ランキング・ステータス分布・改善提案を含むレポートを生成
- detect_regression: ワークフローの直近10回と前10回の成功率を比較し、回帰（0.2以上の低下）を検出
- suggest_improvements: 全ワークフローを走査し、失敗率・回帰・アプリ成功率・非推奨ステータスに
  基づく改善提案リストを生成

【依存】
agent.models (Workflow, WorkflowStatus), agent.workflow_store (WorkflowStore),
agent.feedback_store (FeedbackStore), datetime, logging
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List

from agent.models import Workflow, WorkflowStatus
from agent.workflow_store import WorkflowStore
from agent.feedback_store import FeedbackStore

logger = logging.getLogger(__name__)


class MetaAnalyzer:
    def __init__(self, store: WorkflowStore, feedback: FeedbackStore):
        self._store = store
        self._feedback = feedback

    def generate_report(self, days: int = 7) -> Dict[str, Any]:
        """指定期間の性能レポートを生成"""
        cutoff = datetime.now() - timedelta(days=days)
        all_feedbacks = self._feedback.list_all()

        # 期間内のフィードバックを抽出
        period_feedbacks = []
        for fb in all_feedbacks:
            try:
                ts = datetime.fromisoformat(fb.timestamp)
                if ts >= cutoff:
                    period_feedbacks.append(fb)
            except (ValueError, TypeError):
                # タイムスタンプが不正な場合はスキップ
                continue

        total = len(period_feedbacks)
        success_count = sum(1 for fb in period_feedbacks if fb.success)
        overall_success_rate = success_count / total if total > 0 else 0.0

        # アプリ別統計
        app_stats: Dict[str, Dict[str, Any]] = {}
        app_data: Dict[str, List] = defaultdict(list)
        for fb in period_feedbacks:
            app_name = fb.app_name or "Unknown"
            app_data[app_name].append(fb)

        for app_name, fbs in app_data.items():
            count = len(fbs)
            s_count = sum(1 for f in fbs if f.success)
            avg_dur = sum(f.duration_seconds for f in fbs) / count if count > 0 else 0.0
            app_stats[app_name] = {
                "count": count,
                "success_rate": s_count / count if count > 0 else 0.0,
                "avg_duration": round(avg_dur, 2),
            }

        # ワークフロー別集計
        wf_data: Dict[str, List] = defaultdict(list)
        for fb in period_feedbacks:
            if fb.workflow_id:
                wf_data[fb.workflow_id].append(fb)

        # 失敗ランキング（top 5）
        wf_failure_list = []
        for wf_id, fbs in wf_data.items():
            count = len(fbs)
            s_count = sum(1 for f in fbs if f.success)
            failure_count = count - s_count
            wf = self._store.get(wf_id)
            wf_name = wf.name if wf else wf_id
            wf_failure_list.append({
                "workflow_id": wf_id,
                "name": wf_name,
                "failure_count": failure_count,
                "success_rate": s_count / count if count > 0 else 0.0,
            })
        wf_failure_list.sort(key=lambda x: x["failure_count"], reverse=True)
        top_failures = wf_failure_list[:5]

        # 使用頻度ランキング（top 5）
        wf_usage_list = []
        for wf_id, fbs in wf_data.items():
            count = len(fbs)
            s_count = sum(1 for f in fbs if f.success)
            wf = self._store.get(wf_id)
            wf_name = wf.name if wf else wf_id
            wf_usage_list.append({
                "workflow_id": wf_id,
                "name": wf_name,
                "execution_count": count,
                "success_rate": s_count / count if count > 0 else 0.0,
            })
        wf_usage_list.sort(key=lambda x: x["execution_count"], reverse=True)
        top_used = wf_usage_list[:5]

        # ステータス分布
        status_distribution = {"draft": 0, "tested": 0, "active": 0, "deprecated": 0}
        for wf in self._store.list_all():
            status = wf.status
            if status in status_distribution:
                status_distribution[status] += 1

        # 改善提案
        suggestions = self.suggest_improvements()

        report = {
            "period_days": days,
            "total_feedbacks": total,
            "overall_success_rate": round(overall_success_rate, 4),
            "app_stats": app_stats,
            "top_failures": top_failures,
            "top_used": top_used,
            "status_distribution": status_distribution,
            "suggestions": suggestions,
        }

        logger.info("レポート生成完了: %d日間, フィードバック%d件", days, total)
        return report

    def detect_regression(self, workflow_id: str) -> bool:
        """ワークフローの回帰を検出（直近10回 vs 前10回で成功率0.2以上低下）"""
        feedbacks = self._feedback.get_by_workflow(workflow_id)
        # タイムスタンプ昇順にソート
        feedbacks.sort(key=lambda f: f.timestamp)

        if len(feedbacks) < 20:
            return False

        previous_10 = feedbacks[-20:-10]
        recent_10 = feedbacks[-10:]

        prev_rate = sum(1 for f in previous_10 if f.success) / len(previous_10)
        recent_rate = sum(1 for f in recent_10 if f.success) / len(recent_10)

        drop = prev_rate - recent_rate
        if drop >= 0.2:
            logger.warning(
                "回帰検出: %s (前回%.1f%% → 直近%.1f%%, 低下%.1f%%)",
                workflow_id, prev_rate * 100, recent_rate * 100, drop * 100,
            )
            return True
        return False

    def suggest_improvements(self) -> List[Dict[str, Any]]:
        """全ワークフローの改善提案を生成"""
        suggestions: List[Dict[str, Any]] = []
        workflows = self._store.list_all()

        # アプリ別成功率を事前計算
        app_feedback: Dict[str, List] = defaultdict(list)
        for fb in self._feedback.list_all():
            app_name = fb.app_name or "Unknown"
            app_feedback[app_name].append(fb)

        app_success_rates: Dict[str, float] = {}
        app_counts: Dict[str, int] = {}
        for app_name, fbs in app_feedback.items():
            app_counts[app_name] = len(fbs)
            app_success_rates[app_name] = (
                sum(1 for f in fbs if f.success) / len(fbs) if fbs else 0.0
            )

        for wf in workflows:
            feedbacks = self._feedback.get_by_workflow(wf.workflow_id)
            count = len(feedbacks)

            # ルール1: 失敗率 >= 0.5 かつ実行回数 >= 3
            if count >= 3:
                success_rate = sum(1 for f in feedbacks if f.success) / count
                failure_rate = 1.0 - success_rate
                if failure_rate >= 0.5:
                    suggestions.append({
                        "workflow_id": wf.workflow_id,
                        "name": wf.name,
                        "priority": "high",
                        "suggestion": "成功率が低い。バリアント生成を検討",
                        "auto_applicable": True,
                    })

            # ルール2: 回帰検出
            if self.detect_regression(wf.workflow_id):
                suggestions.append({
                    "workflow_id": wf.workflow_id,
                    "name": wf.name,
                    "priority": "high",
                    "suggestion": "回帰検出：直近の成功率が低下",
                    "auto_applicable": False,
                })

            # ルール3: アプリ成功率 < 0.3 かつ実行回数 >= 5
            app = wf.app_name or "Unknown"
            if app_counts.get(app, 0) >= 5 and app_success_rates.get(app, 1.0) < 0.3:
                suggestions.append({
                    "workflow_id": wf.workflow_id,
                    "name": wf.name,
                    "priority": "high",
                    "suggestion": f"アプリ '{app}' での操作成功率が低い",
                    "auto_applicable": False,
                })

            # ルール4: 非推奨ステータス
            if wf.status == WorkflowStatus.DEPRECATED.value:
                suggestions.append({
                    "workflow_id": wf.workflow_id,
                    "name": wf.name,
                    "priority": "medium",
                    "suggestion": "非推奨。代替ワークフローの作成を推奨",
                    "auto_applicable": False,
                })

        logger.info("改善提案生成: %d件", len(suggestions))
        return suggestions
