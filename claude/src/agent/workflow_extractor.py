"""
JSON操作履歴 → ワークフロー抽出モジュール

【使用方法】
from agent.workflow_extractor import WorkflowExtractor

extractor = WorkflowExtractor(
    json_dir="./screenshots",
    workflow_dir="./workflows",
)

# 全JSONからワークフロー抽出
workflows = extractor.extract_all()
print(f"抽出数: {len(workflows)}")

# 増分抽出（新規ファイルのみ処理）
new_wf = extractor.extract_incremental()
print(f"新規抽出数: {len(new_wf)}")

# セグメント分割のみ（AI分析なし）
segments = extractor.build_segments()
print(f"セグメント数: {len(segments)}")

【処理内容】
1. JSON履歴を timestamp 順にソート
2. セグメント分割（30秒ギャップ / アプリ遷移 / 100操作上限）
3. GPT-5 で各セグメントを分析（名前・説明・パラメータ化・confidence）
4. confidence >= 0.5 のみをワークフローとして保存
5. 重複排除（同名ワークフローは confidence が高い方を採用）

【依存】
agent.models (ActionStep, Workflow), agent.workflow_store (WorkflowStore),
pipeline.ai_client (AIClient), json, pathlib, datetime
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.models import ActionStep, Workflow
from agent.workflow_store import WorkflowStore

logger = logging.getLogger(__name__)

# セグメント分割パラメータ
SEGMENT_GAP_SECONDS = 30
SEGMENT_MAX_ACTIONS = 100


class WorkflowExtractor:
    def __init__(
        self,
        json_dir: str,
        workflow_dir: str,
        model: str = "gpt-5",
        min_confidence: float = 0.5,
    ):
        self._json_dir = Path(json_dir)
        self._store = WorkflowStore(workflow_dir)
        self._model = model
        self._min_confidence = min_confidence

    def extract_all(self) -> List[Workflow]:
        """全JSONからワークフロー抽出（メインエントリポイント）"""
        segments = self.build_segments()
        if not segments:
            logger.warning("セグメントが見つかりません")
            return []

        logger.info("セグメント数: %d, AI分析開始...", len(segments))
        workflows = []

        for i, segment in enumerate(segments):
            logger.info("[%d/%d] セグメント分析中 (操作数: %d, アプリ: %s)",
                        i + 1, len(segments), len(segment["steps"]), segment["app_name"])
            wf = self._analyze_segment(segment)
            if wf:
                # 重複チェック
                existing = self._store.find_duplicate(wf.name)
                if existing:
                    if wf.confidence > existing.confidence:
                        self._store.delete(existing.workflow_id)
                        self._store.save(wf)
                        workflows.append(wf)
                        logger.info("  更新: %s (%.2f → %.2f)", wf.name, existing.confidence, wf.confidence)
                    else:
                        logger.info("  スキップ（既存の方が高confidence）: %s", wf.name)
                else:
                    self._store.save(wf)
                    workflows.append(wf)
                    logger.info("  新規保存: %s (confidence: %.2f)", wf.name, wf.confidence)

        logger.info("抽出完了: %d ワークフロー", len(workflows))
        return workflows

    def build_segments(self) -> List[Dict[str, Any]]:
        """JSON履歴をセグメントに分割"""
        captures = self._load_all_captures()
        return self.build_segments_from_captures(captures)

    def build_segments_from_captures(self, captures: List[Dict]) -> List[Dict[str, Any]]:
        """指定キャプチャリストからセグメントを構築"""
        if not captures:
            return []

        # timestamp順ソート
        captures.sort(key=lambda c: c.get("timestamp", ""))

        segments = []
        current_segment: List[Dict] = []
        current_app = ""
        last_ts: Optional[datetime] = None

        for cap in captures:
            app_name = cap.get("app", {}).get("name", "")
            ts = _parse_timestamp(cap.get("timestamp", ""))

            should_split = False
            if current_segment:
                # 時間ギャップチェック
                if ts and last_ts:
                    gap = (ts - last_ts).total_seconds()
                    if gap >= SEGMENT_GAP_SECONDS:
                        should_split = True

                # アプリ遷移チェック
                if app_name != current_app:
                    should_split = True

                # 最大操作数チェック
                if len(current_segment) >= SEGMENT_MAX_ACTIONS:
                    should_split = True

            if should_split and current_segment:
                segments.append(self._build_segment_data(current_segment, current_app))
                current_segment = []

            current_segment.append(cap)
            current_app = app_name
            if ts:
                last_ts = ts

        if current_segment:
            segments.append(self._build_segment_data(current_segment, current_app))

        return segments

    def extract_incremental(self, processed_file: str = "_agent_processed.txt") -> List[Workflow]:
        """処理済みファイルを追跡しつつ新規分のみ処理"""
        processed_path = self._json_dir / processed_file

        # 処理済みファイル名を読み込み
        processed_set: set = set()
        if processed_path.exists():
            processed_set = set(
                line.strip()
                for line in processed_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )

        # 全キャプチャ読み込み → 未処理分のみフィルタ
        all_captures = self._load_all_captures()
        new_captures = [
            c for c in all_captures
            if Path(c.get("_source_path", "")).name not in processed_set
        ]

        if not new_captures:
            logger.info("新規キャプチャなし")
            return []

        logger.info("新規キャプチャ: %d件", len(new_captures))

        # セグメント分割
        segments = self.build_segments_from_captures(new_captures)
        if not segments:
            return []

        logger.info("新規セグメント数: %d, AI分析開始...", len(segments))
        workflows: List[Workflow] = []

        for i, segment in enumerate(segments):
            logger.info("[%d/%d] セグメント分析中 (操作数: %d, アプリ: %s)",
                        i + 1, len(segments), len(segment["steps"]), segment["app_name"])
            wf = self._analyze_segment(segment)
            if wf:
                # 重複チェック
                existing = self._store.find_duplicate(wf.name)
                if existing:
                    if wf.confidence > existing.confidence:
                        self._store.delete(existing.workflow_id)
                        self._store.save(wf)
                        workflows.append(wf)
                        logger.info("  更新: %s (%.2f → %.2f)", wf.name, existing.confidence, wf.confidence)
                    else:
                        logger.info("  スキップ（既存の方が高confidence）: %s", wf.name)
                else:
                    self._store.save(wf)
                    workflows.append(wf)
                    logger.info("  新規保存: %s (confidence: %.2f)", wf.name, wf.confidence)

        # 処理済みファイル名を追記
        new_filenames = [
            Path(c.get("_source_path", "")).name
            for c in new_captures
            if c.get("_source_path")
        ]
        with open(processed_path, "a", encoding="utf-8") as f:
            for name in new_filenames:
                f.write(name + "\n")

        logger.info("増分抽出完了: %d ワークフロー", len(workflows))
        return workflows

    def _load_all_captures(self) -> List[Dict]:
        """JSON_dir内の全キャプチャJSONを読み込み"""
        captures = []
        patterns = ["cap_*.json", "click_cap_*.json", "text_cap_*.json", "shortcut_cap_*.json"]
        for pattern in patterns:
            for path in self._json_dir.glob(pattern):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    data["_source_path"] = str(path)
                    captures.append(data)
                except Exception as e:
                    logger.warning("JSON読み込みスキップ: %s - %s", path.name, e)
        logger.info("キャプチャJSON読み込み: %d件", len(captures))
        return captures

    def _build_segment_data(self, captures: List[Dict], app_name: str) -> Dict[str, Any]:
        """キャプチャリストからセグメントデータを構築"""
        steps = [ActionStep.from_capture_json(c) for c in captures]
        return {
            "app_name": app_name,
            "steps": steps,
            "captures": captures,
            "start_time": captures[0].get("timestamp", ""),
            "end_time": captures[-1].get("timestamp", ""),
            "session_id": captures[0].get("session", {}).get("session_id", ""),
        }

    def _analyze_segment(self, segment: Dict[str, Any]) -> Optional[Workflow]:
        """セグメントをAIで分析してワークフロー生成"""
        try:
            from pipeline.ai_client import AIClient
            client = AIClient(model=self._model)
        except Exception as e:
            logger.error("AIClient初期化失敗: %s", e)
            return None

        # 操作テキスト生成
        actions_text = self._format_actions_text(segment)
        app_name = segment["app_name"]

        try:
            result = client.analyze_workflow_segment(actions_text, app_name)
        except Exception as e:
            logger.error("ワークフロー分析失敗: %s", e)
            return None

        if not result or not result.get("is_workflow", False):
            return None

        confidence = result.get("confidence", 0.0)
        if confidence < self._min_confidence:
            return None

        workflow = Workflow(
            workflow_id=f"wf-{uuid.uuid4().hex[:8]}",
            name=result.get("name", "不明なワークフロー"),
            description=result.get("description", ""),
            steps=segment["steps"],
            app_name=app_name,
            tags=result.get("tags", []),
            parameters=result.get("parameters", []),
            confidence=confidence,
            source_session_ids=[segment.get("session_id", "")],
            created_at=datetime.now().isoformat(),
        )
        return workflow

    def _format_actions_text(self, segment: Dict[str, Any]) -> str:
        """セグメント内の操作をテキスト化（AI分析用）"""
        lines = []
        for i, cap in enumerate(segment["captures"]):
            user_action = cap.get("user_action", {})
            target = cap.get("target", {})
            action_type = user_action.get("type", "unknown")
            target_name = target.get("name", "")
            target_role = target.get("role", "")
            target_value = target.get("value", "")
            window_name = cap.get("window", {}).get("name", "")
            ts = cap.get("timestamp", "")

            parts = [f"[{i+1}] {ts} {action_type}"]
            if target_name:
                parts.append(f"target={target_name}")
            if target_role:
                parts.append(f"role={target_role}")
            if target_value:
                parts.append(f"value={target_value[:50]}")
            if window_name:
                parts.append(f"window={window_name}")

            # キー操作の詳細
            if action_type == "text_input":
                text = user_action.get("text", "")
                if text:
                    parts.append(f"text='{text[:30]}'")
            elif action_type in ("shortcut", "key_shortcut"):
                mods = user_action.get("modifiers", [])
                key = user_action.get("key", "")
                if mods or key:
                    parts.append(f"shortcut={'+'.join(mods + [key])}")

            lines.append(" ".join(parts))
        return "\n".join(lines)


def _parse_timestamp(ts: str) -> Optional[datetime]:
    """タイムスタンプ文字列をパース"""
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(ts)
    except (ValueError, TypeError):
        return None
