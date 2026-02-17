"""
ワークフロー改善モジュール（フィードバックに基づく自動改善 + ステータスライフサイクル）

【使用方法】
from agent.workflow_store import WorkflowStore
from agent.feedback_store import FeedbackStore
from agent.workflow_refiner import WorkflowRefiner

store = WorkflowStore(workflow_dir="./workflows")
feedback = FeedbackStore(feedback_dir="./feedback")
refiner = WorkflowRefiner(store, feedback)

# 全ワークフローを改善
stats = refiner.refine_all()
print(stats)  # {"updated": 2, "pruned": 3, "merged": 1, "promoted": 1, "demoted": 0, "variants": 1}

【処理内容】
1. ステータス昇降格: 実行回数・成功率に基づく自動ライフサイクル管理（kework-agi準拠）
   - DRAFT → TESTED: 1回以上実行 & 成功あり
   - TESTED → ACTIVE: 5回以上実行 & 成功率70%以上
   - ANY → DEPRECATED: 3回以上実行 & 成功率20%未満
2. 信頼度更新: フィードバックの成功率をもとにconfidenceをブレンド更新
3. 失敗ステップ除去: 失敗率80%以上（3件以上のデータあり）のステップを自動削除
4. バリアント生成: 失敗パターンから改善版ワークフロー(v2,v3...)を自動作成
5. 類似ワークフロー統合: 同一アプリ・類似名・タグ重複率50%以上のワークフローをマージ

【依存】
agent.models (Workflow, WorkflowStatus), agent.workflow_store (WorkflowStore),
agent.feedback_store (FeedbackStore), logging, uuid, datetime, copy
"""

import copy
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

from agent.feedback_store import FeedbackStore
from agent.models import Workflow, WorkflowStatus
from agent.workflow_store import WorkflowStore

logger = logging.getLogger(__name__)

# ステータス昇格閾値（kework-agi準拠）
PROMOTE_TO_TESTED_MIN_COUNT = 1
PROMOTE_TO_ACTIVE_MIN_COUNT = 5
PROMOTE_TO_ACTIVE_MIN_RATE = 0.7
DEMOTE_TO_DEPRECATED_MIN_COUNT = 3
DEMOTE_TO_DEPRECATED_MAX_RATE = 0.2

# バリアント生成閾値
MIN_FAILURES_FOR_VARIANT = 3
STEP_FAILURE_THRESHOLD = 0.5


class WorkflowRefiner:
    def __init__(self, store: WorkflowStore, feedback: FeedbackStore):
        self._store = store
        self._feedback = feedback

    def refine_all(self) -> Dict[str, Any]:
        """全ワークフローを改善し、統計を返す"""
        workflows = self._store.list_all()
        updated = 0
        pruned = 0
        promoted = 0
        demoted = 0
        variants = 0

        for wf in workflows:
            if wf.status == WorkflowStatus.DEPRECATED.value:
                continue

            if self._update_confidence(wf):
                updated += 1

            status_change = self._promote_or_demote(wf)
            if status_change == "promoted":
                promoted += 1
            elif status_change == "demoted":
                demoted += 1

            pruned += self._prune_failed_steps(wf)

            if self._try_create_variant(wf):
                variants += 1

        merged = self._merge_similar(workflows)

        stats = {
            "updated": updated, "pruned": pruned, "merged": merged,
            "promoted": promoted, "demoted": demoted, "variants": variants,
        }
        logger.info("ワークフロー改善完了: %s", stats)
        return stats

    def _promote_or_demote(self, wf: Workflow) -> str:
        """ステータス自動昇降格（kework-agi LearningEngine準拠）"""
        feedbacks = self._feedback.get_by_workflow(wf.workflow_id)
        count = len(feedbacks)
        if count == 0:
            return ""

        rate = self._feedback.get_success_rate(wf.workflow_id)
        old_status = wf.status
        wf.execution_count = count

        # 降格判定（最優先）
        if count >= DEMOTE_TO_DEPRECATED_MIN_COUNT and rate < DEMOTE_TO_DEPRECATED_MAX_RATE:
            wf.status = WorkflowStatus.DEPRECATED.value
        # 昇格: ACTIVE
        elif count >= PROMOTE_TO_ACTIVE_MIN_COUNT and rate >= PROMOTE_TO_ACTIVE_MIN_RATE:
            wf.status = WorkflowStatus.ACTIVE.value
        # 昇格: TESTED
        elif count >= PROMOTE_TO_TESTED_MIN_COUNT and rate > 0:
            if wf.status == WorkflowStatus.DRAFT.value:
                wf.status = WorkflowStatus.TESTED.value

        if wf.status != old_status:
            self._store.save(wf)
            logger.info("ステータス変更: %s (%s → %s, count=%d, rate=%.2f)",
                        wf.name, old_status, wf.status, count, rate)
            if wf.status == WorkflowStatus.DEPRECATED.value:
                return "demoted"
            return "promoted"
        return ""

    def _update_confidence(self, wf: Workflow) -> bool:
        """フィードバック成功率をもとにconfidenceをブレンド更新"""
        feedbacks = self._feedback.get_by_workflow(wf.workflow_id)
        if not feedbacks:
            return False

        success_rate = self._feedback.get_success_rate(wf.workflow_id)
        new_confidence = wf.confidence * 0.7 + success_rate * 0.3

        if abs(new_confidence - wf.confidence) > 0.01:
            old_confidence = wf.confidence
            wf.confidence = new_confidence
            self._store.save(wf)
            logger.info("confidence更新: %s (%.3f → %.3f)", wf.name, old_confidence, new_confidence)
            return True
        return False

    def _prune_failed_steps(self, wf: Workflow) -> int:
        """失敗率の高いステップを除去"""
        feedbacks = self._feedback.get_by_workflow(wf.workflow_id)
        if not feedbacks:
            return 0

        step_failure_rates = self._feedback.get_step_failure_rates(wf.workflow_id)
        total_feedbacks = len(feedbacks)

        indices_to_remove = []
        for step_idx, failure_rate in step_failure_rates.items():
            if failure_rate >= 0.8 and total_feedbacks >= 3:
                indices_to_remove.append(step_idx)

        if not indices_to_remove:
            return 0

        indices_to_remove.sort(reverse=True)
        for idx in indices_to_remove:
            if 0 <= idx < len(wf.steps):
                removed_step = wf.steps.pop(idx)
                logger.info("失敗ステップ除去: %s ステップ[%d] (%s)",
                            wf.name, idx, removed_step.description or removed_step.action_type)

        self._store.save(wf)
        return len(indices_to_remove)

    def _try_create_variant(self, wf: Workflow) -> bool:
        """失敗パターンから改善バリアントを生成（kework-agi SkillOptimizer準拠）"""
        feedbacks = self._feedback.get_by_workflow(wf.workflow_id)
        failed = [fb for fb in feedbacks if not fb.success]
        if len(failed) < MIN_FAILURES_FOR_VARIANT:
            return False

        # 既にバリアントが存在するか確認
        existing_variants = [
            w for w in self._store.list_all()
            if w.parent_id == wf.workflow_id
        ]
        if len(existing_variants) >= 3:
            return False

        # エラー詳細からパターンを検出
        modifications = self._detect_improvements(wf, failed)
        if not modifications:
            return False

        variant = self._create_variant(wf, modifications, len(existing_variants) + 2)
        return variant is not None

    def _detect_improvements(self, wf: Workflow, failed_feedbacks: list) -> List[Dict]:
        """失敗パターンからステップ修正を検出"""
        modifications = []
        step_errors: Dict[int, Dict[str, int]] = {}

        for fb in failed_feedbacks:
            for detail in fb.error_details:
                idx = detail.get("step_index", -1)
                code = detail.get("error_code", "unknown")
                if idx < 0:
                    continue
                if idx not in step_errors:
                    step_errors[idx] = {}
                step_errors[idx][code] = step_errors[idx].get(code, 0) + 1

        for idx, errors in step_errors.items():
            total = sum(errors.values())
            if total < MIN_FAILURES_FOR_VARIANT:
                continue

            for error_code, count in errors.items():
                if count / total < STEP_FAILURE_THRESHOLD:
                    continue
                # kework-agi式のエラー→修正マッピング
                if error_code == "HINT_NOT_FOUND" and count >= 5:
                    modifications.append({"step_index": idx, "type": "change_to_click_xy"})
                elif error_code == "HINT_NOT_FOUND":
                    modifications.append({"step_index": idx, "type": "insert_wait", "value": 0.5})
                elif error_code == "TIMEOUT":
                    modifications.append({"step_index": idx, "type": "increase_timeout", "factor": 1.5})
                elif error_code == "INPUT_FAILED":
                    modifications.append({"step_index": idx, "type": "insert_focus_check"})

        return modifications

    def _create_variant(self, original: Workflow, modifications: List[Dict], version: int) -> Workflow:
        """バリアントワークフローを作成して保存"""
        variant = copy.deepcopy(original)
        variant.workflow_id = f"wf-{uuid.uuid4().hex[:8]}"
        variant.name = f"{original.name}_v{version}"
        variant.status = WorkflowStatus.DRAFT.value
        variant.execution_count = 0
        variant.parent_id = original.workflow_id
        variant.created_at = datetime.now().isoformat()
        variant.confidence = original.confidence * 0.8  # 初期は元の80%

        for mod in modifications:
            idx = mod["step_index"]
            if idx >= len(variant.steps):
                continue
            step = variant.steps[idx]
            mod_type = mod["type"]

            if mod_type == "change_to_click_xy":
                step.target_role = None
                step.target_title = None
                step.description = f"(v{version}) 座標クリックに変更: ({step.x}, {step.y})"
            elif mod_type == "insert_wait":
                step.description = f"(v{version}) {step.description} +wait {mod['value']}s"

        self._store.save(variant)
        logger.info("バリアント生成: %s → %s (%d modifications)",
                    original.name, variant.name, len(modifications))
        return variant

    def select_best_variant(self, original_id: str) -> str:
        """元ワークフローとバリアントの中で最も成功率の高いIDを返す"""
        candidates = [original_id]
        for wf in self._store.list_all():
            if wf.parent_id == original_id and wf.execution_count >= 3:
                candidates.append(wf.workflow_id)

        best_id = original_id
        best_rate = -1.0
        for wf_id in candidates:
            rate = self._feedback.get_success_rate(wf_id)
            feedbacks = self._feedback.get_by_workflow(wf_id)
            if len(feedbacks) >= 3 and rate > best_rate:
                best_rate = rate
                best_id = wf_id

        return best_id

    def _merge_similar(self, workflows: List[Workflow]) -> int:
        """類似ワークフローを統合"""
        merged_count = 0
        merged_ids = set()

        for wf in workflows:
            if wf.workflow_id in merged_ids or wf.parent_id:
                continue

            candidates = [
                c for c in workflows
                if c.workflow_id != wf.workflow_id
                and c.workflow_id not in merged_ids
                and not c.parent_id
            ]
            similar = self._find_similar(wf, candidates)

            for sim in similar:
                if len(sim.steps) > len(wf.steps):
                    base, other = sim, wf
                else:
                    base, other = wf, sim

                base.confidence = (base.confidence + other.confidence) / 2.0
                base.tags = list(set(base.tags) | set(other.tags))
                base.execution_count += other.execution_count

                self._store.save(base)
                self._store.delete(other.workflow_id)
                merged_ids.add(other.workflow_id)
                merged_count += 1
                logger.info("ワークフロー統合: %s + %s → %s", wf.name, sim.name, base.name)

                if base is not wf:
                    merged_ids.add(wf.workflow_id)
                    break

        return merged_count

    def _find_similar(self, wf: Workflow, candidates: List[Workflow]) -> List[Workflow]:
        """類似ワークフローを検索"""
        results = []
        for c in candidates:
            if c.app_name != wf.app_name:
                continue
            if self._edit_distance(wf.name, c.name) > 3:
                continue
            if self._tag_overlap(wf.tags, c.tags) < 0.5:
                continue
            results.append(c)
        return results

    def _edit_distance(self, s1: str, s2: str) -> int:
        """レーベンシュタイン距離"""
        m, n = len(s1), len(s2)
        dp = list(range(n + 1))
        for i in range(1, m + 1):
            prev = dp[0]
            dp[0] = i
            for j in range(1, n + 1):
                temp = dp[j]
                if s1[i - 1] == s2[j - 1]:
                    dp[j] = prev
                else:
                    dp[j] = 1 + min(prev, dp[j], dp[j - 1])
                prev = temp
        return dp[n]

    def _tag_overlap(self, tags1: List[str], tags2: List[str]) -> float:
        """タグ重複率（Jaccard係数）"""
        set1 = set(tags1)
        set2 = set(tags2)
        union = set1 | set2
        if not union:
            return 0.0
        return len(set1 & set2) / len(union)
