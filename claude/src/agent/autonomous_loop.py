"""
自律実行メインループ

【使用方法】
from agent.autonomous_loop import AutonomousLoop
from agent.models import ExecutionContext
from agent.config import AgentConfig

config = AgentConfig()
ctx = ExecutionContext(goal="Finderでフォルダを開く", dry_run=True)

loop = AutonomousLoop(config=config)
result = loop.run(ctx)
print(f"成功: {result.success}, ステップ: {result.steps_executed}")

# ワークフロー直接再生
result = loop.play_workflow(workflow_id="wf-001", dry_run=False)

【処理内容】
メインループ: 目標→観測→選択→実行→検証→目標達成判定
1. 目標に合致するワークフローを検索
2. 見つかればワークフロー実行、なければ自由探索
3. 各ステップ: 状態観測 → アクション選択 → 実行 → 検証
4. 安全機構: 最大50ステップ、連続5失敗で中断

【依存】
agent.models, agent.config, agent.state_observer, agent.action_player,
agent.action_selector, agent.execution_verifier, agent.workflow_store
"""

import logging
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.action_selector import ActionSelector
from agent.config import AgentConfig
from agent.execution_verifier import ExecutionVerifier
from agent.feedback_store import FeedbackStore
from agent.models import (
    ActionStep, ExecutionContext, ExecutionFeedback, ExecutionResult, Workflow,
)
from agent.workflow_store import WorkflowStore

logger = logging.getLogger(__name__)


class AutonomousLoop:
    def __init__(self, config: AgentConfig):
        self._config = config
        self._store = WorkflowStore(config.workflow_dir)
        self._selector = ActionSelector(config)
        self._verifier = ExecutionVerifier(config)
        feedback_dir = str(Path(config.workflow_dir) / "feedback") if config.workflow_dir else ""
        self._feedback = FeedbackStore(feedback_dir) if feedback_dir else None

    def run(self, ctx: ExecutionContext) -> ExecutionResult:
        """自律実行メインループ"""
        start_time = time.time()
        logger.info("自律実行開始: goal='%s' dry_run=%s", ctx.goal, ctx.dry_run)

        # ワークフロー検索
        if ctx.workflow_id:
            workflow = self._store.get(ctx.workflow_id)
            if workflow:
                return self._run_workflow(workflow, ctx, start_time)
            else:
                logger.warning("ワークフロー %s が見つかりません。自由探索に切り替え", ctx.workflow_id)

        # 目標からワークフロー検索
        workflows = self._store.search(ctx.goal)
        if workflows:
            best = workflows[0]
            logger.info("マッチするワークフロー: %s (confidence: %.2f)", best.name, best.confidence)
            return self._run_workflow(best, ctx, start_time)

        # 自由探索
        logger.info("ワークフローなし。自由探索モードで実行")
        return self._run_autonomous(ctx, start_time)

    def play_workflow(
        self,
        workflow_id: str,
        dry_run: bool = False,
        delay: float = 1.0,
        parameters: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        """ワークフローを直接再生"""
        workflow = self._store.get(workflow_id)
        if not workflow:
            return ExecutionResult(success=False, error=f"ワークフロー {workflow_id} が見つかりません")

        ctx = ExecutionContext(
            goal=workflow.name,
            workflow_id=workflow_id,
            dry_run=dry_run,
            step_delay=delay,
            parameters=parameters or {},
        )
        return self._run_workflow(workflow, ctx, time.time())

    def _run_workflow(
        self,
        workflow: Workflow,
        ctx: ExecutionContext,
        start_time: float,
    ) -> ExecutionResult:
        """ワークフロー実行"""
        from agent.action_player import ActionPlayer
        from agent.state_observer import StateObserver

        player = ActionPlayer()
        observer = StateObserver(self._config)

        step_results: List[Dict[str, Any]] = []
        consecutive_failures = 0
        total_steps = len(workflow.steps)

        logger.info("ワークフロー実行: %s (%d ステップ)", workflow.name, total_steps)

        for i in range(total_steps):
            if consecutive_failures >= ctx.max_consecutive_failures:
                logger.error("連続失敗上限到達 (%d回)", consecutive_failures)
                break

            # 状態観測
            current_state = observer.observe_current_state()
            before_ss = current_state.get("screenshot_path", "")

            # ステップ取得
            step = self._selector.select_from_workflow(
                workflow, i, current_state, ctx.parameters
            )
            if not step:
                break

            logger.info("[%d/%d] %s: %s", i + 1, total_steps, step.action_type, step.description or step.target_title or "")

            # 危険操作チェック
            if ctx.confirm_dangerous and self._config.is_dangerous_app(step.app_name):
                logger.warning("危険アプリ操作: %s - dry_run=%s", step.app_name, ctx.dry_run)
                if not ctx.dry_run:
                    print(f"\n⚠️  危険アプリ操作: {step.app_name}")
                    confirm = input("実行しますか? (y/N): ").strip().lower()
                    if confirm != "y":
                        step_results.append({"step": i + 1, "action": step.action_type, "result": "skipped_dangerous"})
                        continue

            # 実行
            play_result = player.play_action_step(step, dry_run=ctx.dry_run)
            success = play_result.get("success", False)

            # 検証（verified=Trueの場合のみAI判定で上書き、Falseならアクション結果を維持）
            verified = False
            if not ctx.dry_run and success:
                time.sleep(0.5)
                after_state = observer.observe_current_state()
                after_ss = after_state.get("screenshot_path", "")
                verify = self._verifier.verify_step(
                    before_ss, after_ss,
                    step.description or step.action_type,
                    dry_run=ctx.dry_run,
                )
                verified = verify.get("verified", False)
                if verified:
                    success = verify.get("success", success)
                else:
                    logger.info("AI検証スキップ: %s", verify.get("reasoning", ""))

            step_results.append({
                "step": i + 1,
                "action": step.action_type,
                "result": "success" if success else "failed",
                "verified": verified,
                "details": play_result,
            })

            if success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1

            # ステップ間待機
            if i < total_steps - 1:
                time.sleep(ctx.step_delay)

        elapsed = time.time() - start_time
        succeeded = sum(1 for r in step_results if r["result"] == "success")
        failed_indices = [
            r["step"] - 1 for r in step_results if r["result"] != "success"
        ]
        result = ExecutionResult(
            success=succeeded > 0,
            steps_executed=len(step_results),
            steps_succeeded=succeeded,
            steps_failed=len(step_results) - succeeded,
            goal_achieved=succeeded == total_steps,
            step_results=step_results,
            total_time_seconds=elapsed,
        )
        # dry-run はフィードバックに記録しない（偽の成功データ混入防止）
        if not ctx.dry_run:
            self._record_feedback(
                workflow_id=workflow.workflow_id,
                goal=ctx.goal,
                result=result,
                failed_indices=failed_indices,
                mode="workflow",
            )
        return result

    def _run_autonomous(
        self,
        ctx: ExecutionContext,
        start_time: float,
    ) -> ExecutionResult:
        """自由探索実行"""
        from agent.action_player import ActionPlayer
        from agent.state_observer import StateObserver

        player = ActionPlayer()
        observer = StateObserver(self._config)

        step_results: List[Dict[str, Any]] = []
        consecutive_failures = 0
        steps_executed = 0

        for step_num in range(1, ctx.max_steps + 1):
            if consecutive_failures >= ctx.max_consecutive_failures:
                logger.error("連続失敗上限到達 (%d回)", consecutive_failures)
                break

            # 状態観測
            current_state = observer.observe_current_state()
            before_ss = current_state.get("screenshot_path", "")

            # 目標達成チェック（5ステップごと）
            if step_num > 1 and step_num % 5 == 0:
                history_text = [
                    {"step": r["step"], "action": r["action"], "result": r["result"]}
                    for r in step_results[-10:]
                ]
                goal_check = self._verifier.check_goal(ctx.goal, current_state, history_text)
                if goal_check.get("achieved", False) and goal_check.get("confidence", 0) >= 0.7:
                    logger.info("目標達成: %s (confidence: %.2f)", ctx.goal, goal_check["confidence"])
                    elapsed = time.time() - start_time
                    succeeded = sum(1 for r in step_results if r["result"] == "success")
                    failed_indices = [
                        r["step"] - 1 for r in step_results if r["result"] != "success"
                    ]
                    result = ExecutionResult(
                        success=True,
                        steps_executed=len(step_results),
                        steps_succeeded=succeeded,
                        steps_failed=len(step_results) - succeeded,
                        goal_achieved=True,
                        step_results=step_results,
                        total_time_seconds=elapsed,
                    )
                    self._record_feedback(
                        workflow_id=None,
                        goal=ctx.goal,
                        result=result,
                        failed_indices=failed_indices,
                        mode="autonomous",
                    )
                    return result

            # AIでアクション選択
            history = [
                {"step": r["step"], "action": r["action"], "result": r["result"]}
                for r in step_results[-10:]
            ]
            action = self._selector.select_autonomous(ctx.goal, current_state, history)
            if not action:
                logger.warning("アクション選択不可。ループ終了")
                break

            # done シグナル
            if action.get("action_type") == "done":
                logger.info("AI判断: 目標達成")
                break

            # wait シグナル
            if action.get("action_type") == "wait":
                logger.info("AI判断: 待機")
                time.sleep(2.0)
                step_results.append({"step": step_num, "action": "wait", "result": "success"})
                continue

            # 危険操作チェック
            if action.get("requires_confirmation") and ctx.confirm_dangerous and not ctx.dry_run:
                app_name = current_state.get("app", {}).get("name", "")
                print(f"\n⚠️  危険アプリ操作: {app_name}")
                print(f"    アクション: {action.get('action_type')} - {action.get('target_description')}")
                confirm = input("実行しますか? (y/N): ").strip().lower()
                if confirm != "y":
                    step_results.append({"step": step_num, "action": action["action_type"], "result": "skipped_dangerous"})
                    continue

            # ActionStep に変換して実行
            app_info = current_state.get("app", {})
            step = self._selector.action_dict_to_step(action, app_info)

            logger.info("[%d] %s: %s (confidence: %.2f)",
                        step_num, step.action_type,
                        action.get("target_description", ""),
                        action.get("confidence", 0))

            play_result = player.play_action_step(step, dry_run=ctx.dry_run)
            success = play_result.get("success", False)

            # 検証（verified=Trueの場合のみAI判定で上書き、Falseならアクション結果を維持）
            verified = False
            if not ctx.dry_run and success:
                time.sleep(0.5)
                after_state = observer.observe_current_state()
                after_ss = after_state.get("screenshot_path", "")
                verify = self._verifier.verify_step(
                    before_ss, after_ss,
                    action.get("target_description", ""),
                    dry_run=ctx.dry_run,
                )
                verified = verify.get("verified", False)
                if verified:
                    success = verify.get("success", success)
                else:
                    logger.info("AI検証スキップ: %s", verify.get("reasoning", ""))

            step_results.append({
                "step": step_num,
                "action": step.action_type,
                "result": "success" if success else "failed",
                "verified": verified,
                "details": play_result,
                "ai_reasoning": action.get("reasoning", ""),
            })

            if success:
                consecutive_failures = 0
            else:
                consecutive_failures += 1

            steps_executed = step_num
            time.sleep(ctx.step_delay)

        elapsed = time.time() - start_time
        succeeded = sum(1 for r in step_results if r["result"] == "success")
        failed_indices = [
            r["step"] - 1 for r in step_results if r["result"] != "success"
        ]
        result = ExecutionResult(
            success=succeeded > 0,
            steps_executed=len(step_results),
            steps_succeeded=succeeded,
            steps_failed=len(step_results) - succeeded,
            goal_achieved=False,
            step_results=step_results,
            total_time_seconds=elapsed,
        )
        self._record_feedback(
            workflow_id=None,
            goal=ctx.goal,
            result=result,
            failed_indices=failed_indices,
            mode="autonomous",
        )
        return result

    def _record_feedback(
        self,
        workflow_id: Optional[str],
        goal: str,
        result: ExecutionResult,
        failed_indices: List[int],
        mode: str,
    ) -> None:
        """実行結果をフィードバックとして記録"""
        if not self._feedback:
            return
        try:
            feedback = ExecutionFeedback(
                feedback_id=f"fb-{uuid.uuid4().hex[:8]}",
                workflow_id=workflow_id,
                goal=goal,
                success=result.success,
                steps_executed=result.steps_executed,
                steps_succeeded=result.steps_succeeded,
                failed_step_indices=failed_indices,
                timestamp=datetime.now().isoformat(),
                execution_mode=mode,
            )
            self._feedback.record(feedback)
            logger.info("フィードバック記録: %s (success=%s)", feedback.feedback_id, feedback.success)
        except Exception as e:
            logger.warning("フィードバック記録失敗: %s", e)
