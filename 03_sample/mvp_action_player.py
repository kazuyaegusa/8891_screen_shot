#!/usr/bin/env python3
"""
MVP: Action Player
記録したセッションJSONから操作を再生する

使用方法:
    python3 mvp_action_player.py <session.json>
    python3 mvp_action_player.py mvp_output/session_20260205_222336.json

オプション:
    --dry-run    実際にクリックせず、何が起きるか確認
    --delay N    各アクション間の待機秒数（デフォルト: 1.0）
    --start N    N番目のアクションから開始（0始まり）

必要な権限:
- アクセシビリティ: システム環境設定 > プライバシーとセキュリティ > アクセシビリティ
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    from Quartz import (
        CGEventCreateMouseEvent,
        CGEventCreateKeyboardEvent,
        CGEventPost,
        CGEventSetIntegerValueField,
        CGEventSetFlags,
        kCGEventLeftMouseDown,
        kCGEventLeftMouseUp,
        kCGEventRightMouseDown,
        kCGEventRightMouseUp,
        kCGMouseButtonLeft,
        kCGMouseButtonRight,
        kCGHIDEventTap,
        kCGMouseEventClickState,
    )
    from ApplicationServices import (
        AXUIElementCopyElementAtPosition,
        AXUIElementCreateSystemWide,
        AXUIElementCopyAttributeValue,
        AXUIElementCopyAttributeNames,
    )
    from AppKit import NSWorkspace, NSRunningApplication
    QUARTZ_AVAILABLE = True
except ImportError as e:
    print(f"Error: Could not import required frameworks: {e}")
    QUARTZ_AVAILABLE = False

BASE_FLAGS = 0x100
KEY_ACTION_TYPES = {"text_input", "key_input", "key_shortcut"}


def get_ax_attribute(element, attr: str) -> Optional[Any]:
    """Accessibility要素の属性を取得"""
    try:
        err, value = AXUIElementCopyAttributeValue(element, attr, None)
        if err == 0 and value is not None:
            return value
        return None
    except Exception:
        return None


def get_element_frame(element) -> Optional[Dict[str, float]]:
    """要素のフレーム（位置・サイズ）を取得"""
    try:
        import re
        position = get_ax_attribute(element, "AXPosition")
        size = get_ax_attribute(element, "AXSize")
        if position and size:
            # AXValueRefの文字列表現から値をパース
            pos_str = str(position)
            size_str = str(size)

            pos_match = re.search(r'x:([\d.]+)\s*y:([\d.]+)', pos_str)
            size_match = re.search(r'w:([\d.]+)\s*h:([\d.]+)', size_str)

            if pos_match and size_match:
                return {
                    "x": float(pos_match.group(1)),
                    "y": float(pos_match.group(2)),
                    "width": float(size_match.group(1)),
                    "height": float(size_match.group(2)),
                }
    except Exception:
        pass
    return None


def activate_app(bundle_id: str) -> bool:
    """アプリをアクティブにする"""
    try:
        ws = NSWorkspace.sharedWorkspace()
        apps = NSRunningApplication.runningApplicationsWithBundleIdentifier_(bundle_id)
        if apps and len(apps) > 0:
            apps[0].activateWithOptions_(0)
            time.sleep(0.3)  # アクティブ化を待つ
            return True
        return False
    except Exception as e:
        print(f"  Warning: Could not activate app: {e}")
        return False


def click_at(x: float, y: float, button: str = "left") -> None:
    """指定座標をクリック"""
    if button == "right":
        down_type, up_type, mouse_button = (
            kCGEventRightMouseDown,
            kCGEventRightMouseUp,
            kCGMouseButtonRight,
        )
    else:
        down_type, up_type, mouse_button = (
            kCGEventLeftMouseDown,
            kCGEventLeftMouseUp,
            kCGMouseButtonLeft,
        )

    down = CGEventCreateMouseEvent(None, down_type, (x, y), mouse_button)
    up = CGEventCreateMouseEvent(None, up_type, (x, y), mouse_button)
    CGEventSetIntegerValueField(down, kCGMouseEventClickState, 1)
    CGEventSetIntegerValueField(up, kCGMouseEventClickState, 1)
    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)


def normalize_flags(flags: Optional[int]) -> int:
    if flags is None:
        return BASE_FLAGS
    return int(flags) | BASE_FLAGS


def type_key(keycode: int, flags: Optional[int] = None, delay: float = 0.03) -> None:
    """キーを押して離す。flagsは常に明示的に設定する"""
    normalized = normalize_flags(flags)
    down = CGEventCreateKeyboardEvent(None, keycode, True)
    up = CGEventCreateKeyboardEvent(None, keycode, False)
    CGEventSetFlags(down, normalized)
    CGEventSetFlags(up, normalized)
    CGEventPost(kCGHIDEventTap, down)
    time.sleep(0.01)
    CGEventPost(kCGHIDEventTap, up)
    time.sleep(delay)


def play_key_action(action: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    action_id = action.get("action_id", "unknown")
    action_type = action.get("action_type")
    result = {
        "action_id": action_id,
        "success": False,
        "method": action_type,
        "coordinates_used": None,
        "error": None,
    }

    if dry_run:
        result["success"] = True
        result["dry_run"] = True
        return result

    if action_type == "text_input":
        key_events = action.get("key_events") or []
        if not key_events:
            result["error"] = "No key_events found for text_input"
            return result
        for evt in key_events:
            keycode = evt.get("keycode")
            if keycode is None:
                continue
            type_key(int(keycode), evt.get("flags"))
        result["success"] = True
        return result

    key_event = action.get("key_event") or {}
    keycode = key_event.get("keycode")
    if keycode is None:
        result["error"] = "Missing keycode"
        return result
    type_key(int(keycode), key_event.get("flags"))
    result["success"] = True
    return result


def search_all_elements(app_element, max_depth: int = 10) -> List[Tuple[Any, Dict]]:
    """アプリ内の全要素を再帰的に検索"""
    results = []

    def recurse(element, depth: int):
        if depth > max_depth:
            return

        # この要素の情報を取得
        role = get_ax_attribute(element, "AXRole")
        title = get_ax_attribute(element, "AXTitle")
        description = get_ax_attribute(element, "AXDescription")
        identifier = get_ax_attribute(element, "AXIdentifier")
        value = get_ax_attribute(element, "AXValue")
        frame = get_element_frame(element)

        info = {
            "role": str(role) if role else None,
            "title": str(title) if title else None,
            "description": str(description) if description else None,
            "identifier": str(identifier) if identifier else None,
            "value": str(value)[:100] if value else None,
            "frame": frame,
        }
        results.append((element, info))

        # 子要素を再帰的に検索
        children = get_ax_attribute(element, "AXChildren")
        if children:
            for child in children:
                recurse(child, depth + 1)

    recurse(app_element, 0)
    return results


def find_element_by_criteria(
    target: Dict[str, Any],
    tolerance: float = 50.0,
) -> Optional[Tuple[float, float, str]]:
    """
    記録された要素情報をもとに、現在の画面から要素を検索

    検索優先順位:
    1. identifier が一致
    2. value が一致
    3. description が一致
    4. title + role が一致
    5. 座標が近い（フォールバック）

    Returns: (x, y, match_method) or None
    """
    system_wide = AXUIElementCreateSystemWide()

    # まず座標位置の要素を確認
    orig_x = target.get("coordinates", {}).get("x", 0)
    orig_y = target.get("coordinates", {}).get("y", 0)

    err, element_at_pos = AXUIElementCopyElementAtPosition(system_wide, orig_x, orig_y, None)

    if err == 0 and element_at_pos:
        # 座標位置の要素が記録と一致するか確認
        elem_info = target.get("element", {})
        target_identifier = elem_info.get("identifier")
        target_value = elem_info.get("value")
        target_description = elem_info.get("description")
        target_title = elem_info.get("title")
        target_role = elem_info.get("role")

        current_identifier = get_ax_attribute(element_at_pos, "AXIdentifier")
        current_value = get_ax_attribute(element_at_pos, "AXValue")
        current_description = get_ax_attribute(element_at_pos, "AXDescription")
        current_title = get_ax_attribute(element_at_pos, "AXTitle")
        current_role = get_ax_attribute(element_at_pos, "AXRole")

        # 1. identifier一致
        if target_identifier and current_identifier:
            if str(current_identifier) == target_identifier:
                frame = get_element_frame(element_at_pos)
                if frame:
                    cx = frame["x"] + frame["width"] / 2
                    cy = frame["y"] + frame["height"] / 2
                    return (cx, cy, "identifier_match_at_position")
                return (orig_x, orig_y, "identifier_match_at_position")

        # 2. value一致
        if target_value and current_value:
            if str(current_value) == target_value:
                frame = get_element_frame(element_at_pos)
                if frame:
                    cx = frame["x"] + frame["width"] / 2
                    cy = frame["y"] + frame["height"] / 2
                    return (cx, cy, "value_match_at_position")
                return (orig_x, orig_y, "value_match_at_position")

        # 3. description一致
        if target_description and current_description:
            if str(current_description) == target_description:
                frame = get_element_frame(element_at_pos)
                if frame:
                    cx = frame["x"] + frame["width"] / 2
                    cy = frame["y"] + frame["height"] / 2
                    return (cx, cy, "description_match_at_position")
                return (orig_x, orig_y, "description_match_at_position")

        # 4. title + role一致
        if target_title and current_title and target_role and current_role:
            if str(current_title) == target_title and str(current_role) == target_role:
                frame = get_element_frame(element_at_pos)
                if frame:
                    cx = frame["x"] + frame["width"] / 2
                    cy = frame["y"] + frame["height"] / 2
                    return (cx, cy, "title_role_match_at_position")
                return (orig_x, orig_y, "title_role_match_at_position")

        # 5. roleだけ一致（フォールバック）
        if target_role and current_role:
            if str(current_role) == target_role:
                return (orig_x, orig_y, "role_match_at_position")

    # 座標位置で見つからない場合、元の座標をフォールバックとして使用
    return (orig_x, orig_y, "coordinate_fallback")


def play_action(action: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    """
    単一アクションを再生

    Returns: 実行結果の辞書
    """
    action_id = action.get("action_id", "unknown")
    action_type = action.get("action_type", "left_click")
    app_info = action.get("app", {})
    elem_info = action.get("element", {})
    coordinates = action.get("coordinates", {})

    result = {
        "action_id": action_id,
        "success": False,
        "method": None,
        "coordinates_used": None,
        "error": None,
    }

    # アプリをアクティブ化
    bundle_id = app_info.get("bundle_id")
    if bundle_id:
        activate_app(bundle_id)

    if action_type in KEY_ACTION_TYPES:
        return play_key_action(action, dry_run=dry_run)

    # 要素を検索
    search_result = find_element_by_criteria(action)

    if search_result is None:
        result["error"] = "Element not found"
        return result

    x, y, method = search_result
    result["method"] = method
    result["coordinates_used"] = {"x": x, "y": y}

    # クリック実行
    if not dry_run:
        button = "right" if action_type == "right_click" else "left"
        click_at(x, y, button)
        result["success"] = True
    else:
        result["success"] = True
        result["dry_run"] = True

    return result


def play_session(
    session: Dict[str, Any],
    dry_run: bool = False,
    delay: float = 1.0,
    start_index: int = 0,
) -> List[Dict[str, Any]]:
    """
    セッション全体を再生
    """
    actions = session.get("actions", [])
    total = len(actions)
    results = []

    print(f"\n{'='*60}")
    print(f"Playing session: {session.get('session_id', 'unknown')}")
    print(f"Total actions: {total}")
    print(f"Starting from: #{start_index}")
    print(f"Delay: {delay}s")
    print(f"Dry run: {dry_run}")
    print(f"{'='*60}\n")

    for i, action in enumerate(actions[start_index:], start=start_index):
        print(f"[{i+1}/{total}] Action: {action.get('action_id')}")
        print(f"  Type: {action.get('action_type')}")
        print(f"  App: {action.get('app', {}).get('name')}")

        if action.get("action_type") in KEY_ACTION_TYPES:
            if action.get("action_type") == "text_input":
                print(f"  Text: {action.get('text', '')}")
            else:
                key_event = action.get("key_event") or {}
                print(f"  Keycode: {key_event.get('keycode')}")
                mods = key_event.get("modifiers") or []
                if mods:
                    print(f"  Modifiers: {', '.join(mods)}")
        else:
            elem = action.get("element", {})
            if elem.get("identifier"):
                print(f"  Target ID: {elem.get('identifier')}")
            elif elem.get("value"):
                print(f"  Target Value: {elem.get('value')}")
            elif elem.get("description"):
                print(f"  Target Desc: {elem.get('description')}")
            else:
                print(f"  Target Role: {elem.get('role')}")

        result = play_action(action, dry_run=dry_run)
        results.append(result)

        if result["success"]:
            print(f"  ✓ Success (method: {result['method']})")
            if result.get("coordinates_used"):
                coords = result["coordinates_used"]
                print(f"    Clicked at: ({coords['x']:.0f}, {coords['y']:.0f})")
        else:
            print(f"  ✗ Failed: {result.get('error')}")

        # 次のアクションまで待機
        if i < total - 1:
            print(f"  Waiting {delay}s...")
            time.sleep(delay)

        print()

    # サマリー
    success_count = sum(1 for r in results if r["success"])
    print(f"{'='*60}")
    print(f"Completed: {success_count}/{len(results)} actions successful")
    print(f"{'='*60}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Play recorded actions from session JSON")
    parser.add_argument("session_file", help="Path to session JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually click, just show what would happen")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between actions (seconds)")
    parser.add_argument("--start", type=int, default=0, help="Start from action index (0-based)")
    args = parser.parse_args()

    if not QUARTZ_AVAILABLE:
        print("Error: Required frameworks not available.")
        sys.exit(1)

    if not os.path.exists(args.session_file):
        print(f"Error: Session file not found: {args.session_file}")
        sys.exit(1)

    # セッション読み込み
    with open(args.session_file, "r", encoding="utf-8") as f:
        session = json.load(f)

    print("="*60)
    print("MVP Action Player")
    print("="*60)

    if args.dry_run:
        print("\n*** DRY RUN MODE - No actual clicks will be performed ***\n")

    input("Press Enter to start playback (Ctrl+C to cancel)...")

    try:
        results = play_session(
            session,
            dry_run=args.dry_run,
            delay=args.delay,
            start_index=args.start,
        )
    except KeyboardInterrupt:
        print("\n\nPlayback cancelled.")
        sys.exit(0)


if __name__ == "__main__":
    main()
