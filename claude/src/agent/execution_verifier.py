"""
実行結果のAI検証モジュール

【使用方法】
from agent.execution_verifier import ExecutionVerifier
from agent.config import AgentConfig

verifier = ExecutionVerifier(config=AgentConfig())

# 実行前後のスクリーンショット比較
result = verifier.verify_step(
    before_screenshot="/tmp/before.png",
    after_screenshot="/tmp/after.png",
    expected_change="ボタンがクリックされてダイアログが表示される",
)
# => {"success": True, "confidence": 0.9, "verified": True, "reasoning": "..."}

# 検証不能時（API未設定、スクリーンショットなし等）
# => {"success": False, "confidence": 0.0, "verified": False, "reasoning": "..."}
# verified=False の場合、呼び出し側はアクション実行結果をそのまま使うべき

# 目標達成判定
achieved = verifier.check_goal(
    goal="Finderでフォルダを開く",
    current_state={"app": "Finder", "screenshot_path": "/tmp/current.png"},
    history=[...],
)
# => {"achieved": True, "confidence": 0.85, "reasoning": "..."}

【処理内容】
- before/after スクリーンショットをVisionで比較し、操作が成功したか判定
- 検証不能時は verified=False を返し、success=True を偽装しない
- 目標達成判定: 現在状態と目標を照合し、完了を判定
- dry-run時はスクリーンショット比較をスキップ（verified=False）

【依存】
agent.config (AgentConfig), pipeline.ai_client (AIClient)
"""

import logging
import os
from typing import Any, Dict, List

from agent.config import AgentConfig

logger = logging.getLogger(__name__)


class ExecutionVerifier:
    def __init__(self, config: AgentConfig):
        self._config = config

    def verify_step(
        self,
        before_screenshot: str,
        after_screenshot: str,
        expected_change: str,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """実行前後のスクリーンショットを比較して成否判定

        Returns:
            verified=True: AI検証が正常に実行された。success の値を信頼してよい
            verified=False: 検証が実行できなかった。呼び出し側はアクション結果をそのまま使うべき
        """
        if dry_run:
            return {"success": False, "confidence": 0.0, "verified": False,
                    "reasoning": "dry-run: 検証スキップ", "dry_run": True}

        if not before_screenshot or not after_screenshot:
            logger.warning("スクリーンショット未取得のため検証スキップ")
            return {"success": False, "confidence": 0.0, "verified": False,
                    "reasoning": "スクリーンショットなし: 検証不可"}

        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            logger.warning("OPENAI_API_KEY 未設定のためAI検証スキップ")
            return {"success": False, "confidence": 0.0, "verified": False,
                    "reasoning": "APIキー未設定: 検証不可"}

        try:
            from pipeline.ai_client import AIClient
            client = AIClient(model=self._config.openai_model)
        except Exception as e:
            logger.error("AIClient初期化失敗: %s", e)
            return {"success": False, "confidence": 0.0, "verified": False,
                    "reasoning": f"AI検証不可: {e}"}

        try:
            result = client.verify_execution(
                before_screenshot=before_screenshot,
                after_screenshot=after_screenshot,
                expected_change=expected_change,
            )
            result["verified"] = True
            return result
        except Exception as e:
            logger.error("実行検証失敗: %s", e)
            return {"success": False, "confidence": 0.0, "verified": False,
                    "reasoning": f"検証エラー: {e}"}

    def check_goal(
        self,
        goal: str,
        current_state: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """目標が達成されたか判定"""
        try:
            from pipeline.ai_client import AIClient
            client = AIClient(model=self._config.openai_model)
        except Exception as e:
            logger.error("AIClient初期化失敗: %s", e)
            return {"achieved": False, "confidence": 0.0, "reasoning": f"AI判定不可: {e}"}

        # 履歴テキスト
        history_text = ""
        if history:
            lines = []
            for h in history[-10:]:
                lines.append(f"Step {h.get('step', '?')}: {h.get('action', '?')} → {h.get('result', '?')}")
            history_text = "\n".join(lines)

        try:
            result = client.check_goal_achieved(
                goal=goal,
                current_state=current_state,
                history=history_text,
            )
            return result
        except Exception as e:
            logger.error("目標達成判定失敗: %s", e)
            return {"achieved": False, "confidence": 0.0, "reasoning": f"判定エラー: {e}"}
