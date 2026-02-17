"""
エージェントシステムのデータモデル定義

【使用方法】
from agent.models import ActionStep, Workflow, ExecutionContext, ExecutionResult, WorkflowStatus

step = ActionStep(
    action_type="click",
    app_bundle_id="com.apple.finder",
    target_role="AXButton",
    target_title="開く",
    x=500.0, y=300.0,
)

workflow = Workflow(
    workflow_id="wf-001",
    name="Finderでフォルダを開く",
    description="指定パスのフォルダをFinderで開く操作",
    steps=[step],
    app_name="Finder",
    confidence=0.85,
)

ctx = ExecutionContext(goal="Finderでフォルダを開く", dry_run=True)
result = ExecutionResult(success=True, steps_executed=3)

【処理内容】
WorkflowStatus: ワークフローライフサイクル（DRAFT→TESTED→ACTIVE→DEPRECATED）
ActionStep: 1つの操作ステップ（クリック・キー入力・ショートカット）
Workflow: 操作ステップの集合（学習済みワークフロー、ステータス・実行回数・バリアント対応）
ExecutionContext: 自律実行時のコンテキスト（目標・設定・状態）
ExecutionResult: 実行結果のサマリー
ExecutionFeedback: 実行フィードバック（ステップ別エラー詳細・実行時間・アプリ名付き）

【依存】
Python標準ライブラリのみ (dataclasses, typing)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class WorkflowStatus(str, Enum):
    """ワークフローのライフサイクルステータス（kework-agi準拠）"""
    DRAFT = "draft"          # 新規抽出直後
    TESTED = "tested"        # 1回以上実行 & 成功あり
    ACTIVE = "active"        # 5回以上実行 & 成功率70%以上
    DEPRECATED = "deprecated"  # 3回以上実行 & 成功率20%未満


@dataclass
class ActionStep:
    """1つの操作ステップ"""
    action_type: str  # click, right_click, text_input, key_input, key_shortcut
    app_bundle_id: str = ""
    app_name: str = ""

    # クリック対象
    target_role: Optional[str] = None
    target_title: Optional[str] = None
    target_value: Optional[str] = None
    target_description: Optional[str] = None
    target_identifier: Optional[str] = None
    x: float = 0.0
    y: float = 0.0

    # キー入力
    keycode: Optional[int] = None
    flags: Optional[int] = None
    key_events: List[Dict[str, Any]] = field(default_factory=list)
    text: str = ""
    modifiers: List[str] = field(default_factory=list)

    # パラメータ化（ワークフロー内で可変な値）
    is_parameterized: bool = False
    param_name: Optional[str] = None

    # メタ情報
    description: str = ""
    screenshot_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "app_bundle_id": self.app_bundle_id,
            "app_name": self.app_name,
            "target": {
                "role": self.target_role,
                "title": self.target_title,
                "value": self.target_value,
                "description": self.target_description,
                "identifier": self.target_identifier,
            },
            "coordinates": {"x": self.x, "y": self.y},
            "key": {
                "keycode": self.keycode,
                "flags": self.flags,
                "key_events": self.key_events,
                "text": self.text,
                "modifiers": self.modifiers,
            },
            "parameterized": {
                "is_parameterized": self.is_parameterized,
                "param_name": self.param_name,
            },
            "description": self.description,
            "screenshot_path": self.screenshot_path,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ActionStep":
        target = d.get("target", {})
        coords = d.get("coordinates", {})
        key = d.get("key", {})
        param = d.get("parameterized", {})
        return cls(
            action_type=d.get("action_type", "click"),
            app_bundle_id=d.get("app_bundle_id", ""),
            app_name=d.get("app_name", ""),
            target_role=target.get("role"),
            target_title=target.get("title"),
            target_value=target.get("value"),
            target_description=target.get("description"),
            target_identifier=target.get("identifier"),
            x=coords.get("x", 0.0),
            y=coords.get("y", 0.0),
            keycode=key.get("keycode"),
            flags=key.get("flags"),
            key_events=key.get("key_events", []),
            text=key.get("text", ""),
            modifiers=key.get("modifiers", []),
            is_parameterized=param.get("is_parameterized", False),
            param_name=param.get("param_name"),
            description=d.get("description", ""),
            screenshot_path=d.get("screenshot_path"),
        )

    @classmethod
    def from_capture_json(cls, capture: Dict[str, Any]) -> "ActionStep":
        """キャプチャJSON（cap_*.json）から ActionStep を生成"""
        user_action = capture.get("user_action", {})
        target = capture.get("target", {})
        app = capture.get("app", {})
        screenshots = capture.get("screenshots", {})
        mouse = capture.get("mouse", {})

        action_type = user_action.get("type", "click")
        # shortcut → key_shortcut にマッピング
        if action_type == "shortcut":
            action_type = "key_shortcut"

        return cls(
            action_type=action_type,
            app_bundle_id=app.get("bundle_id", ""),
            app_name=app.get("name", ""),
            target_role=target.get("role"),
            target_title=target.get("name"),
            target_value=target.get("value"),
            target_description=target.get("description"),
            target_identifier=target.get("identifier"),
            x=mouse.get("x", user_action.get("x", 0.0)),
            y=mouse.get("y", user_action.get("y", 0.0)),
            keycode=user_action.get("keycode"),
            flags=user_action.get("flags"),
            key_events=user_action.get("key_events", []),
            text=user_action.get("text", ""),
            modifiers=user_action.get("modifiers", []),
            screenshot_path=screenshots.get("full"),
        )


@dataclass
class Workflow:
    """学習済みワークフロー（操作ステップの集合）"""
    workflow_id: str
    name: str
    description: str
    steps: List[ActionStep] = field(default_factory=list)
    app_name: str = ""
    tags: List[str] = field(default_factory=list)
    parameters: List[Dict[str, str]] = field(default_factory=list)
    confidence: float = 0.0
    source_session_ids: List[str] = field(default_factory=list)
    created_at: str = ""
    status: str = "draft"  # WorkflowStatus: draft/tested/active/deprecated
    execution_count: int = 0
    parent_id: Optional[str] = None  # バリアント元のworkflow_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "app_name": self.app_name,
            "tags": self.tags,
            "parameters": self.parameters,
            "confidence": self.confidence,
            "source_session_ids": self.source_session_ids,
            "created_at": self.created_at,
            "status": self.status,
            "execution_count": self.execution_count,
            "parent_id": self.parent_id,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Workflow":
        steps = [ActionStep.from_dict(s) for s in d.get("steps", [])]
        return cls(
            workflow_id=d.get("workflow_id", ""),
            name=d.get("name", ""),
            description=d.get("description", ""),
            steps=steps,
            app_name=d.get("app_name", ""),
            tags=d.get("tags", []),
            parameters=d.get("parameters", []),
            confidence=d.get("confidence", 0.0),
            source_session_ids=d.get("source_session_ids", []),
            created_at=d.get("created_at", ""),
            status=d.get("status", "draft"),
            execution_count=d.get("execution_count", 0),
            parent_id=d.get("parent_id"),
        )


@dataclass
class ExecutionContext:
    """自律実行時のコンテキスト"""
    goal: str
    workflow_id: Optional[str] = None
    dry_run: bool = False
    max_steps: int = 50
    max_consecutive_failures: int = 5
    step_delay: float = 1.0
    confirm_dangerous: bool = True
    parameters: Dict[str, str] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """実行結果のサマリー"""
    success: bool
    steps_executed: int = 0
    steps_succeeded: int = 0
    steps_failed: int = 0
    goal_achieved: bool = False
    error: Optional[str] = None
    step_results: List[Dict[str, Any]] = field(default_factory=list)
    total_time_seconds: float = 0.0


@dataclass
class ExecutionFeedback:
    """実行フィードバック（学習改善用）"""
    feedback_id: str
    workflow_id: Optional[str]
    goal: str
    success: bool
    steps_executed: int
    steps_succeeded: int
    failed_step_indices: List[int] = field(default_factory=list)
    error_details: List[Dict[str, str]] = field(default_factory=list)  # [{step_index, error_code, error_msg}]
    timestamp: str = ""
    execution_mode: str = "autonomous"  # "workflow" | "autonomous"
    duration_seconds: float = 0.0
    app_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "workflow_id": self.workflow_id,
            "goal": self.goal,
            "success": self.success,
            "steps_executed": self.steps_executed,
            "steps_succeeded": self.steps_succeeded,
            "failed_step_indices": self.failed_step_indices,
            "error_details": self.error_details,
            "timestamp": self.timestamp,
            "execution_mode": self.execution_mode,
            "duration_seconds": self.duration_seconds,
            "app_name": self.app_name,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ExecutionFeedback":
        return cls(
            feedback_id=d.get("feedback_id", ""),
            workflow_id=d.get("workflow_id"),
            goal=d.get("goal", ""),
            success=d.get("success", False),
            steps_executed=d.get("steps_executed", 0),
            steps_succeeded=d.get("steps_succeeded", 0),
            failed_step_indices=d.get("failed_step_indices", []),
            error_details=d.get("error_details", []),
            timestamp=d.get("timestamp", ""),
            execution_mode=d.get("execution_mode", "autonomous"),
            duration_seconds=d.get("duration_seconds", 0.0),
            app_name=d.get("app_name", ""),
        )
