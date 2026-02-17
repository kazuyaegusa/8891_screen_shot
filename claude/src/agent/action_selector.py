"""
AIによる次アクション選択モジュール

【使用方法】
from agent.action_selector import ActionSelector
from agent.config import AgentConfig

selector = ActionSelector(config=AgentConfig())

# ワークフローベース（学習済みステップを順次実行）
next_step = selector.select_from_workflow(workflow, step_index=2, current_state={})

# 自由探索（AIが判断）
next_action = selector.select_autonomous(
    goal="Finderでフォルダを開く",
    current_state={"app": "Finder", "screenshot_path": "/tmp/ss.png"},
    history=[{"step": 1, "action": "click", "result": "success"}],
)

【処理内容】
- ワークフロー実行: 学習済みステップを順番に返す（パラメータ置換あり）
- 自由探索: GPT-5 に現在状態・目標・履歴を送り、次アクションを推論
- 危険操作チェック: 送信系アプリ操作時はフラグを立てる

【依存】
agent.models (ActionStep, Workflow, ExecutionContext),
agent.config (AgentConfig),
agent.workflow_store (WorkflowStore),
pipeline.ai_client (AIClient)
"""

import logging
from typing import Any, Dict, List, Optional

from agent.config import AgentConfig
from agent.models import ActionStep, Workflow

logger = logging.getLogger(__name__)


class ActionSelector:
    def __init__(self, config: AgentConfig):
        self._config = config

    def select_from_workflow(
        self,
        workflow: Workflow,
        step_index: int,
        current_state: Dict[str, Any],
        parameters: Optional[Dict[str, str]] = None,
    ) -> Optional[ActionStep]:
        """ワークフローから次のステップを取得（パラメータ置換あり）"""
        if step_index >= len(workflow.steps):
            return None

        step = workflow.steps[step_index]

        # パラメータ置換
        if parameters and step.is_parameterized and step.param_name:
            replacement = parameters.get(step.param_name, "")
            if replacement:
                step.text = replacement
                step.target_value = replacement

        return step

    def select_autonomous(
        self,
        goal: str,
        current_state: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """AIで次のアクションを自律選択"""
        try:
            from pipeline.ai_client import AIClient
            client = AIClient(model=self._config.openai_model)
        except Exception as e:
            logger.error("AIClient初期化失敗: %s", e)
            return None

        # 利用可能アクションの説明
        available_actions = (
            "click(x,y) - 指定座標をクリック\n"
            "right_click(x,y) - 右クリック\n"
            "text_input(text) - テキスト入力\n"
            "key_shortcut(keycode, flags) - キーボードショートカット\n"
            "wait - 待機\n"
            "done - 目標達成完了"
        )

        # 履歴テキスト
        history_text = ""
        if history:
            lines = []
            for h in history[-10:]:  # 直近10ステップ
                lines.append(f"Step {h.get('step', '?')}: {h.get('action', '?')} → {h.get('result', '?')}")
            history_text = "\n".join(lines)

        try:
            result = client.select_next_action(
                goal=goal,
                current_state=current_state,
                available_actions=available_actions,
                history=history_text,
            )
        except Exception as e:
            logger.error("アクション選択失敗: %s", e)
            return None

        if not result:
            return None

        # 危険操作チェック
        app_name = current_state.get("app", {}).get("name", "")
        if self._config.is_dangerous_app(app_name):
            result["requires_confirmation"] = True
            logger.warning("危険アプリ操作検出: %s", app_name)

        return result

    def action_dict_to_step(self, action: Dict[str, Any], app_info: Dict[str, Any]) -> ActionStep:
        """AI選択結果をActionStepに変換"""
        return ActionStep(
            action_type=action.get("action_type", "click"),
            app_bundle_id=app_info.get("bundle_id", ""),
            app_name=app_info.get("name", ""),
            x=action.get("x", 0.0),
            y=action.get("y", 0.0),
            text=action.get("text", ""),
            keycode=action.get("keycode"),
            flags=action.get("flags"),
            modifiers=action.get("modifiers", []),
            description=action.get("target_description", ""),
        )
