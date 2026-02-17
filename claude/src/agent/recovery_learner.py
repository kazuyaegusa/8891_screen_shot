"""
エラー復旧パターン学習モジュール

【使用方法】
from agent.recovery_learner import RecoveryLearner

learner = RecoveryLearner(patterns_path="./workflows/recovery_patterns.json")

# 復旧結果を記録
learner.record_recovery(
    error_code="HINT_NOT_FOUND",
    app_name="Safari",
    failed_action="click",
    recovery_action="click_xy",
    success=True,
)

# 学習済みの復旧パターンを取得
pattern = learner.get_learned_recovery(
    error_code="HINT_NOT_FOUND",
    app_name="Safari",
    failed_action="click",
)
if pattern:
    print(f"推奨復旧: {pattern['recovery_action']} (成功率: {pattern['success_rate']:.0%})")

# 信頼度の高いパターン一覧
reliable = learner.get_reliable_patterns()

【処理内容】
- 実行履歴からエラー復旧パターンを学習
- error_code / app_name / failed_action の組合せでパターンをマッチング
- サンプル数・成功率の閾値を満たすパターンのみ提案
- recovery_patterns.json にパターンを永続化

【依存】
json, logging, pathlib, typing
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

MIN_SAMPLES_FOR_SUGGESTION = 3
MIN_SUCCESS_RATE_FOR_SUGGESTION = 0.6


class RecoveryLearner:
    """実行履歴からエラー復旧パターンを学習し、復旧アクションを提案する"""

    def __init__(self, patterns_path: str):
        self._path = Path(patterns_path)
        self._patterns: List[Dict] = self._load()

    def record_recovery(
        self,
        error_code: str,
        app_name: str,
        failed_action: str,
        recovery_action: str,
        success: bool,
    ) -> None:
        """復旧結果を記録。既存パターンがあれば更新、なければ新規作成"""
        existing = self._find_pattern(error_code, app_name, failed_action, recovery_action)

        if existing:
            existing["sample_count"] += 1
            if success:
                existing["success_count"] += 1
            existing["success_rate"] = existing["success_count"] / existing["sample_count"]
            logger.info(
                "復旧パターン更新: %s/%s/%s -> %s (成功率: %.0f%%)",
                error_code, app_name, failed_action, recovery_action,
                existing["success_rate"] * 100,
            )
        else:
            pattern = {
                "error_code": error_code,
                "app_name": app_name,
                "failed_action": failed_action,
                "recovery_action": recovery_action,
                "sample_count": 1,
                "success_count": 1 if success else 0,
                "success_rate": 1.0 if success else 0.0,
            }
            self._patterns.append(pattern)
            logger.info(
                "復旧パターン新規作成: %s/%s/%s -> %s",
                error_code, app_name, failed_action, recovery_action,
            )

        self._save()

    def get_learned_recovery(
        self,
        error_code: str,
        app_name: str = "",
        failed_action: str = "",
    ) -> Optional[Dict]:
        """学習済みの復旧パターンを検索。段階的にフォールバックして最適なパターンを返す"""
        # 完全一致 → app_name なし → error_code のみ の順でフォールバック
        search_keys = [
            (error_code, app_name, failed_action),
            (error_code, "", failed_action),
            (error_code, "", ""),
        ]

        for ec, an, fa in search_keys:
            candidates = [
                p for p in self._patterns
                if p["error_code"] == ec
                and p["app_name"] == an
                and p["failed_action"] == fa
                and p["sample_count"] >= MIN_SAMPLES_FOR_SUGGESTION
                and p["success_rate"] >= MIN_SUCCESS_RATE_FOR_SUGGESTION
            ]
            if candidates:
                best = max(candidates, key=lambda p: p["success_rate"])
                return best

        return None

    def get_reliable_patterns(self) -> List[Dict]:
        """閾値を満たす信頼度の高いパターン一覧を返す（成功率降順）"""
        reliable = [
            p for p in self._patterns
            if p["sample_count"] >= MIN_SAMPLES_FOR_SUGGESTION
            and p["success_rate"] >= MIN_SUCCESS_RATE_FOR_SUGGESTION
        ]
        reliable.sort(key=lambda p: p["success_rate"], reverse=True)
        return reliable

    def _find_pattern(
        self,
        error_code: str,
        app_name: str,
        failed_action: str,
        recovery_action: str,
    ) -> Optional[Dict]:
        """4項目完全一致でパターンを検索"""
        for p in self._patterns:
            if (
                p["error_code"] == error_code
                and p["app_name"] == app_name
                and p["failed_action"] == failed_action
                and p["recovery_action"] == recovery_action
            ):
                return p
        return None

    def _save(self) -> None:
        """パターンをJSONファイルに保存"""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._patterns, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load(self) -> List[Dict]:
        """JSONファイルからパターンを読み込み"""
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            logger.warning("recovery_patterns.json の形式が不正（listでない）: %s", type(data))
            return []
        except Exception as e:
            logger.warning("recovery_patterns.json 読み込み失敗: %s", e)
            return []
