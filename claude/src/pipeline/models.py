"""
パイプライン全体で共有するデータモデル定義

【使用方法】
from pipeline.models import CaptureRecord, Session, ExtractedSkill

record = CaptureRecord(
    capture_id="uuid-xxx",
    timestamp="2026-02-16T12:00:00",
    session={"session_id": "s1", "sequence": 1},
    user_action={"type": "click", "button": "left"},
    target={"detection_type": "window", "name": "Finder"},
    app={"name": "Finder", "bundle_id": "com.apple.finder", "pid": 123},
    browser={"is_browser": False, "url": None, "page_title": None},
    window={"window_id": 1, "name": "Documents"},
    screenshots={"full": "/path/full.png", "cropped": "/path/crop.png"},
    json_path="/path/cap_xxx.json",
)

session = Session(
    session_id="s1",
    app_name="Finder",
    records=[record],
    start_time="2026-02-16T12:00:00",
    end_time="2026-02-16T12:05:00",
)

skill = ExtractedSkill(
    name="ファイル整理",
    description="Finderでファイルをフォルダに移動する操作",
    steps=["フォルダを開く", "ファイルをドラッグ"],
    app="Finder",
    triggers=["ファイル移動", "整理"],
    confidence=0.85,
)

【処理内容】
CaptureRecord: 1回のキャプチャ結果を表すデータクラス
Session: 同一アプリでの連続操作をグループ化したセッション
ExtractedSkill: AIが抽出したスキル（操作パターン）

【依存】
Python標準ライブラリのみ (dataclasses, typing)
"""

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class CaptureRecord:
    capture_id: str
    timestamp: str
    session: Dict
    user_action: Dict
    target: Dict
    app: Dict
    browser: Dict
    window: Dict
    screenshots: Dict
    json_path: str


@dataclass
class Session:
    session_id: str
    app_name: str
    records: List[CaptureRecord] = field(default_factory=list)
    start_time: str = ""
    end_time: str = ""


@dataclass
class ExtractedSkill:
    name: str
    description: str
    steps: List[str] = field(default_factory=list)
    app: str = ""
    triggers: List[str] = field(default_factory=list)
    confidence: float = 0.0
