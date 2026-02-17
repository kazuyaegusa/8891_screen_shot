"""
AI クライアント: セッション分析・スキル抽出・ワークフロー分析・
アクション選択・実行検証・目標判定・要素検出を行うプラガブルなAIラッパー

【使用方法】
from pipeline.ai_client import AIClient
from pipeline.models import Session

client = AIClient(provider="openai", model="gpt-5")
result = client.analyze_session(session)
skill = client.extract_skill(session)
workflow = client.analyze_workflow_segment(actions_text, app_name)
action = client.select_next_action(goal, current_state, available_actions, history)
verification = client.verify_execution(before_path, after_path, expected_change)
goal_check = client.check_goal_achieved(goal, current_state, history)
element = client.find_element_by_vision(screenshot_path, element_description)

【処理内容】
- analyze_session: セッション内の操作列を要約・分析し Dict で返す
- extract_skill: セッションから繰り返し操作パターンをスキルとして抽出
  JSON Schema による構造化出力で ExtractedSkill を生成
- analyze_workflow_segment: ワークフローセグメントを分析し名前・説明・パラメータ化・confidenceを返す
- select_next_action: 目標と現在の状態から次のアクションを選択
- verify_execution: 実行前後のスクリーンショットをVisionで比較し成功/失敗を判定
- check_goal_achieved: 目標が達成されたか判定
- find_element_by_vision: スクリーンショットからVisionで要素の座標を推定
- provider が "openai" 以外の場合は NotImplementedError
- API 呼び出し失敗時はログ出力して None/デフォルト値を返す

【依存】
openai, pipeline.models (Session, ExtractedSkill)
環境変数: OPENAI_API_KEY
"""

import base64
import json
import logging
import os
from typing import Dict, Optional

from pipeline.models import ExtractedSkill, Session

logger = logging.getLogger(__name__)

_SKILL_SCHEMA = {
    "name": "extracted_skill",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "steps": {"type": "array", "items": {"type": "string"}},
            "app": {"type": "string"},
            "triggers": {"type": "array", "items": {"type": "string"}},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "is_skill": {"type": "boolean"},
        },
        "required": [
            "name", "description", "steps", "app",
            "triggers", "confidence", "is_skill",
        ],
    },
    "strict": True,
}

_WORKFLOW_SCHEMA = {
    "name": "workflow_analysis",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string"},
            "description": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "parameters": {"type": "array", "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "step_index": {"type": "integer"},
                },
                "required": ["name", "description", "step_index"],
            }},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "is_workflow": {"type": "boolean"},
        },
        "required": [
            "name", "description", "tags", "parameters",
            "confidence", "is_workflow",
        ],
    },
    "strict": True,
}

_ACTION_SELECTION_SCHEMA = {
    "name": "action_selection",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "action_type": {
                "type": "string",
                "enum": ["click", "right_click", "text_input", "key_shortcut", "wait", "done"],
            },
            "target_description": {"type": "string"},
            "x": {"type": "number"},
            "y": {"type": "number"},
            "text": {"type": "string"},
            "keycode": {"type": "integer"},
            "flags": {"type": "integer"},
            "modifiers": {"type": "array", "items": {"type": "string"}},
            "reasoning": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        },
        "required": [
            "action_type", "target_description", "x", "y",
            "text", "keycode", "flags", "modifiers",
            "reasoning", "confidence",
        ],
    },
    "strict": True,
}


def _encode_image(path: str) -> str:
    """画像ファイルをbase64エンコードして返す"""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


class AIClient:
    def __init__(self, provider: str = "openai", model: str = "gpt-5"):
        if provider != "openai":
            raise NotImplementedError(f"Provider '{provider}' is not supported yet")
        self.provider = provider
        self.model = model

    def analyze_session(self, session: Session) -> Dict:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        prompt = _build_analysis_prompt(session)

        try:
            res = client.responses.create(
                model=self.model,
                input=prompt,
                reasoning={"effort": "low"},
            )
            return {"summary": res.output_text, "session_id": session.session_id}
        except Exception as e:
            logger.error("セッション分析に失敗: %s", e)
            return {"error": str(e), "session_id": session.session_id}

    def extract_skill(self, session: Session) -> Optional[ExtractedSkill]:
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        prompt = _build_extraction_prompt(session)

        try:
            res = client.responses.create(
                model=self.model,
                input=prompt,
                text={"format": {"type": "json_schema", **_SKILL_SCHEMA}},
                reasoning={"effort": "low"},
            )
            data = json.loads(res.output_text)

            if not data.get("is_skill", False):
                return None

            return ExtractedSkill(
                name=data["name"],
                description=data["description"],
                steps=data["steps"],
                app=data["app"],
                triggers=data["triggers"],
                confidence=data["confidence"],
            )
        except Exception as e:
            logger.error("スキル抽出に失敗: %s", e)
            return None

    def analyze_workflow_segment(
        self, actions_text: str, app_name: str
    ) -> Optional[Dict]:
        """ワークフローセグメントを分析し、名前・説明・パラメータ化・confidenceを返す"""
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        prompt = (
            f"以下はアプリ '{app_name}' での操作列です。\n\n"
            f"{actions_text}\n\n"
            f"この操作列がワークフロー（再利用可能な手順）として抽出できるか分析してください。\n"
            f"ワークフローとして抽出できる場合は is_workflow=true、"
            f"できない場合は is_workflow=false としてください。\n"
            f"パラメータ化可能な箇所（ファイル名、URL等）があれば parameters に含めてください。"
        )

        try:
            res = client.responses.create(
                model=self.model,
                input=prompt,
                text={"format": {"type": "json_schema", **_WORKFLOW_SCHEMA}},
                reasoning={"effort": "medium"},
                max_output_tokens=2000,
            )
            data = json.loads(res.output_text)
            if not data.get("is_workflow", False):
                return None
            return data
        except Exception as e:
            logger.error("ワークフロー分析に失敗: %s", e)
            return None

    def select_next_action(
        self,
        goal: str,
        current_state: Dict,
        available_actions: str,
        history: str,
    ) -> Optional[Dict]:
        """目標と現在の状態から次のアクションを選択する"""
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        state_text = json.dumps(current_state, ensure_ascii=False, indent=2)
        prompt = (
            f"目標: {goal}\n\n"
            f"現在の状態:\n{state_text}\n\n"
            f"利用可能なアクション:\n{available_actions}\n\n"
            f"これまでの操作履歴:\n{history}\n\n"
            f"目標を達成するための次のアクションを1つ選択してください。\n"
            f"目標が既に達成されている場合は action_type='done' としてください。"
        )

        try:
            res = client.responses.create(
                model=self.model,
                input=prompt,
                text={"format": {"type": "json_schema", **_ACTION_SELECTION_SCHEMA}},
                reasoning={"effort": "medium"},
                max_output_tokens=2000,
            )
            return json.loads(res.output_text)
        except Exception as e:
            logger.error("アクション選択に失敗: %s", e)
            return None

    def verify_execution(
        self,
        before_screenshot: str,
        after_screenshot: str,
        expected_change: str,
    ) -> Dict:
        """実行前後のスクリーンショットをVisionで比較し、成功/失敗を判定する"""
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        before_b64 = _encode_image(before_screenshot)
        after_b64 = _encode_image(after_screenshot)

        try:
            res = client.responses.create(
                model=self.model,
                input=[
                    {"role": "user", "content": [
                        {"type": "input_text", "text": (
                            f"以下の2枚のスクリーンショット（実行前・実行後）を比較してください。\n"
                            f"期待される変化: {expected_change}\n\n"
                            f"1枚目が実行前、2枚目が実行後です。\n"
                            f"期待される変化が実際に起きたかどうかを判定し、\n"
                            f"結果を JSON で返してください:\n"
                            f'{{"success": true/false, "reasoning": "判定理由"}}'
                        )},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{before_b64}"},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{after_b64}"},
                    ]}
                ],
                reasoning={"effort": "medium"},
            )
            try:
                return json.loads(res.output_text)
            except json.JSONDecodeError:
                return {"success": False, "reasoning": res.output_text}
        except Exception as e:
            logger.error("実行検証に失敗: %s", e)
            return {"success": False, "reasoning": str(e)}

    def check_goal_achieved(
        self, goal: str, current_state: Dict, history: str
    ) -> Dict:
        """目標が達成されたか判定する"""
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        state_text = json.dumps(current_state, ensure_ascii=False, indent=2)
        prompt = (
            f"目標: {goal}\n\n"
            f"現在の状態:\n{state_text}\n\n"
            f"操作履歴:\n{history}\n\n"
            f"目標が達成されたかどうかを判定してください。\n"
            f"結果を JSON で返してください:\n"
            f'{{"achieved": true/false, "confidence": 0.0~1.0, "reasoning": "判定理由"}}'
        )

        try:
            res = client.responses.create(
                model=self.model,
                input=prompt,
                reasoning={"effort": "medium"},
            )
            try:
                return json.loads(res.output_text)
            except json.JSONDecodeError:
                return {"achieved": False, "confidence": 0.0, "reasoning": res.output_text}
        except Exception as e:
            logger.error("目標達成判定に失敗: %s", e)
            return {"achieved": False, "confidence": 0.0, "reasoning": str(e)}

    def find_element_by_vision(
        self, screenshot_path: str, element_description: str
    ) -> Optional[Dict]:
        """スクリーンショットからVisionで要素の座標を推定する"""
        from openai import OpenAI

        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        img_b64 = _encode_image(screenshot_path)

        try:
            res = client.responses.create(
                model=self.model,
                input=[
                    {"role": "user", "content": [
                        {"type": "input_text", "text": (
                            f"以下のスクリーンショットから、次の要素を見つけてください:\n"
                            f"「{element_description}」\n\n"
                            f"要素の中心座標（ピクセル）と確信度を JSON で返してください:\n"
                            f'{{"x": 数値, "y": 数値, "confidence": 0.0~1.0, "description": "要素の説明"}}'
                        )},
                        {"type": "input_image", "image_url": f"data:image/png;base64,{img_b64}"},
                    ]}
                ],
                reasoning={"effort": "medium"},
            )
            try:
                return json.loads(res.output_text)
            except json.JSONDecodeError:
                logger.error("Vision応答のJSON解析に失敗: %s", res.output_text)
                return None
        except Exception as e:
            logger.error("要素検出に失敗: %s", e)
            return None


def _build_analysis_prompt(session: Session) -> str:
    actions = []
    for r in session.records:
        action_type = r.user_action.get("type", "unknown")
        target_name = r.target.get("name", "")
        actions.append(f"- [{r.timestamp}] {action_type}: {target_name}")
    action_text = "\n".join(actions)

    return (
        f"以下はアプリ '{session.app_name}' での操作ログです。\n"
        f"期間: {session.start_time} ~ {session.end_time}\n"
        f"操作数: {len(session.records)}\n\n"
        f"{action_text}\n\n"
        f"この操作セッションの内容を簡潔に要約してください。"
    )


def _build_extraction_prompt(session: Session) -> str:
    actions = []
    for r in session.records:
        action_type = r.user_action.get("type", "unknown")
        button = r.user_action.get("button", "")
        target_name = r.target.get("name", "")
        window_name = r.window.get("name", "")
        actions.append(
            f"- [{r.timestamp}] {action_type}({button}) "
            f"target={target_name} window={window_name}"
        )
    action_text = "\n".join(actions)

    return (
        f"以下はアプリ '{session.app_name}' での操作ログです。\n"
        f"期間: {session.start_time} ~ {session.end_time}\n"
        f"操作数: {len(session.records)}\n\n"
        f"{action_text}\n\n"
        f"この操作列から以下を分析してください:\n"
        f"1. 繰り返されている操作パターンがあるか\n"
        f"2. 手順化できる操作フローがあるか\n"
        f"3. スキル（再利用可能な操作手順）として抽出できるか\n\n"
        f"スキルとして抽出できる場合は is_skill=true、"
        f"できない場合は is_skill=false としてください。\n"
        f"confidence は抽出の確信度を 0~1 で設定してください。"
    )
