"""
AI クライアント: セッション分析・スキル抽出を行うプラガブルなAIラッパー

【使用方法】
from pipeline.ai_client import AIClient
from pipeline.models import Session

client = AIClient(provider="openai", model="gpt-5")
result = client.analyze_session(session)
skill = client.extract_skill(session)

【処理内容】
- analyze_session: セッション内の操作列を要約・分析し Dict で返す
- extract_skill: セッションから繰り返し操作パターンをスキルとして抽出
  JSON Schema による構造化出力で ExtractedSkill を生成
- provider が "openai" 以外の場合は NotImplementedError
- API 呼び出し失敗時はログ出力して None を返す

【依存】
openai, pipeline.models (Session, ExtractedSkill)
環境変数: OPENAI_API_KEY
"""

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
                text={"format": {"type": "json_schema", "json_schema": _SKILL_SCHEMA}},
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
