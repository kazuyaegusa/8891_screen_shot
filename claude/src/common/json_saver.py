"""
スクリーンショットキャプチャ結果をJSONファイルとして保存するユーティリティ

【使用方法】
from common.json_saver import build_capture_payload, save_capture_json

payload = build_capture_payload(
    capture_result=result,
    monitors=monitors,
    all_windows=all_windows,
    browser_info=browser_info,
)
json_path = save_capture_json(payload, "output/cap_20240101.json")

【処理内容】
1. capture_resultからターゲット・アプリ・ウィンドウ情報を抽出しJSON構造を構築
2. UUID・タイムスタンプを付与
3. UTF-8でJSONファイルに保存（日本語そのまま、2スペースインデント）

【依存】
Python標準ライブラリのみ (json, uuid, datetime, pathlib)
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


def build_capture_payload(
    capture_result: Dict[str, Any],
    monitors: Optional[List[Dict]] = None,
    all_windows: Optional[List[Dict]] = None,
    browser_info: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    キャプチャ結果を包括的なJSONペイロードに構築する

    Input:
        capture_result: WindowScreenshot.capture_window_at_cursor()の戻り値
        monitors: mss.monitorsの全モニター情報リスト
        all_windows: detector.get_all_windows()の戻り値
        browser_info: inspector.get_browser_info()の戻り値
    Output:
        Dict: 包括的キャプチャ情報
    """
    window_info = capture_result.get("window_info", {})
    detection_type = window_info.get("detection_type", "window")

    # ターゲット情報
    target = {
        "detection_type": detection_type,
        "x": window_info.get("x", 0),
        "y": window_info.get("y", 0),
        "width": window_info.get("width", 0),
        "height": window_info.get("height", 0),
        "name": window_info.get("name", ""),
    }

    if detection_type == "element":
        target.update({
            "role": window_info.get("role"),
            "title": window_info.get("title"),
            "description": window_info.get("description"),
            "identifier": window_info.get("identifier"),
            "value": window_info.get("value"),
            "placeholder": window_info.get("placeholder"),
            "focused": window_info.get("focused"),
            "enabled": window_info.get("enabled"),
            "role_description": window_info.get("role_description"),
        })

    # アプリ情報
    app = {
        "name": window_info.get("app_name", window_info.get("window_owner", "")),
        "bundle_id": window_info.get("app_bundle_id", ""),
        "pid": window_info.get("app_pid", window_info.get("window_owner_pid", 0)),
    }

    # ウィンドウ情報
    window = {
        "window_id": window_info.get("window_id", 0),
        "name": window_info.get("window_name", window_info.get("name", "")),
        "owner": window_info.get("window_owner", window_info.get("owner", "")),
        "x": window_info.get("window_x", window_info.get("x", 0)),
        "y": window_info.get("window_y", window_info.get("y", 0)),
        "width": window_info.get("window_width", window_info.get("width", 0)),
        "height": window_info.get("window_height", window_info.get("height", 0)),
    }

    # モニター情報を整形
    formatted_monitors = []
    if monitors:
        for i, m in enumerate(monitors):
            if i == 0:
                continue  # monitors[0] は全結合なのでスキップ
            formatted_monitors.append({
                "index": i,
                "left": m.get("left", 0),
                "top": m.get("top", 0),
                "width": m.get("width", 0),
                "height": m.get("height", 0),
            })

    # スクリーンショットパス
    screenshots = {
        "full": capture_result.get("full_screenshot"),
        "cropped": capture_result.get("cropped_screenshot"),
    }

    return {
        "capture_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "detection_mode": capture_result.get("detection_mode", "window"),
        "mouse": {
            "x": window_info.get("mouse_x", 0),
            "y": window_info.get("mouse_y", 0),
        },
        "target": target,
        "app": app,
        "browser": browser_info or {"is_browser": False, "url": None, "page_title": None},
        "window": window,
        "all_windows": all_windows or [],
        "monitors": formatted_monitors,
        "screenshots": screenshots,
    }


def save_capture_json(payload: Dict[str, Any], output_path: str) -> str:
    """
    ペイロードをJSONファイルに保存する

    Input:
        payload: build_capture_payload()の戻り値
        output_path: 保存先パス
    Output:
        str: 保存したJSONファイルの絶対パス
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(str(path), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)

    return str(path.resolve())
