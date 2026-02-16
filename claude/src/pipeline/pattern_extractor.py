"""
パターン抽出器: セッションから操作パターン（スキル）を抽出する

【使用方法】
from pipeline.ai_client import AIClient
from pipeline.pattern_extractor import PatternExtractor
from pipeline.models import Session

client = AIClient(provider="openai", model="gpt-5")
extractor = PatternExtractor(ai_client=client, min_confidence=0.6)
skills = extractor.extract(session)
for skill in skills:
    print(skill.name, skill.confidence)

【処理内容】
1. セッション内の操作列からプロンプトを生成
2. AIClient 経由でスキル抽出を実行
3. confidence が min_confidence 以上のスキルのみ返す

【依存】
pipeline.ai_client (AIClient), pipeline.models (Session, ExtractedSkill)
"""

import logging
from typing import List

from pipeline.ai_client import AIClient
from pipeline.models import ExtractedSkill, Session

logger = logging.getLogger(__name__)


class PatternExtractor:
    def __init__(self, ai_client: AIClient, min_confidence: float = 0.6):
        self._ai_client = ai_client
        self._min_confidence = min_confidence

    def extract(self, session: Session) -> List[ExtractedSkill]:
        if not session.records:
            return []

        skill = self._ai_client.extract_skill(session)
        if skill is None:
            logger.debug("セッション %s からスキル抽出なし", session.session_id)
            return []

        if skill.confidence < self._min_confidence:
            logger.debug(
                "スキル '%s' の confidence %.2f が閾値 %.2f 未満",
                skill.name, skill.confidence, self._min_confidence,
            )
            return []

        return [skill]
