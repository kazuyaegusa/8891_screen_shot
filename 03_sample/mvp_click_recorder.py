#!/usr/bin/env python3
"""
MVP: Click Recorder Test
グローバルクリックを監視し、クリック位置のUI要素情報を取得するテスト

使用方法:
    python3 mvp_click_recorder.py

終了: Ctrl+C

必要な権限:
- アクセシビリティ: システム環境設定 > プライバシーとセキュリティ > アクセシビリティ
- 入力監視: システム環境設定 > プライバシーとセキュリティ > 入力監視（キーボード記録時）
"""

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from Quartz import (
        CGEventTapCreate,
        CGEventTapEnable,
        CFMachPortCreateRunLoopSource,
        CFRunLoopGetCurrent,
        CFRunLoopAddSource,
        CFRunLoopRun,
        CGEventGetLocation,
        CGEventGetIntegerValueField,
        CGEventGetFlags,
        CGEventKeyboardGetUnicodeString,
        kCGSessionEventTap,
        kCGHeadInsertEventTap,
        kCGEventTapOptionListenOnly,
        CGEventMaskBit,
        kCGEventLeftMouseDown,
        kCGEventRightMouseDown,
        kCGEventKeyDown,
        kCGEventFlagsChanged,
        kCGKeyboardEventKeycode,
        kCGEventFlagMaskShift,
        kCGEventFlagMaskControl,
        kCGEventFlagMaskAlternate,
        kCGEventFlagMaskCommand,
        kCFRunLoopCommonModes,
    )
    from ApplicationServices import (
        AXUIElementCopyElementAtPosition,
        AXUIElementCreateSystemWide,
        AXUIElementCopyAttributeValue,
        AXUIElementCopyAttributeNames,
    )
    from AppKit import NSWorkspace
    QUARTZ_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import Quartz/AppKit: {e}")
    QUARTZ_AVAILABLE = False


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "mvp_output")
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")

TEXT_INPUT_FLUSH_SECONDS = 1.0
SPECIAL_KEYCODES = {
    36,  # Enter
    48,  # Tab
    51,  # Delete
    53,  # Escape
    123, 124, 125, 126,  # Arrow keys
    116, 121, 115, 119, 117,  # PageUp/PageDown/Home/End/ForwardDelete
    102, 104, 109,  # Eisu/Kana (varies by environment)
}


def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def get_frontmost_app() -> Dict[str, str]:
    """最前面のアプリ情報を取得"""
    try:
        ws = NSWorkspace.sharedWorkspace()
        app = ws.frontmostApplication()
        return {
            "name": app.localizedName(),
            "bundle_id": app.bundleIdentifier(),
        }
    except Exception as e:
        return {"name": "Unknown", "bundle_id": "", "error": str(e)}


def get_ax_attribute(element, attr: str) -> Optional[Any]:
    """Accessibility要素の属性を取得"""
    try:
        err, value = AXUIElementCopyAttributeValue(element, attr, None)
        if err == 0 and value is not None:
            return value
        return None
    except Exception:
        return None


def get_element_at_position(x: float, y: float) -> Dict[str, Any]:
    """指定座標のUI要素情報を取得"""
    try:
        system_wide = AXUIElementCreateSystemWide()
        err, element = AXUIElementCopyElementAtPosition(system_wide, x, y, None)

        if err != 0 or element is None:
            return {"error": f"No element found at ({x}, {y})", "code": err}

        # 属性を取得
        role = get_ax_attribute(element, "AXRole")
        title = get_ax_attribute(element, "AXTitle")
        description = get_ax_attribute(element, "AXDescription")
        identifier = get_ax_attribute(element, "AXIdentifier")
        value = get_ax_attribute(element, "AXValue")

        # フレーム情報（AXPosition + AXSize から構築）
        frame = None
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
                    frame = {
                        "x": float(pos_match.group(1)),
                        "y": float(pos_match.group(2)),
                        "width": float(size_match.group(1)),
                        "height": float(size_match.group(2)),
                    }
        except Exception as frame_err:
            # フレーム取得失敗は無視（他の情報は返す）
            pass

        # 全属性名を取得（デバッグ用）
        err2, attr_names = AXUIElementCopyAttributeNames(element, None)
        available_attrs = list(attr_names) if err2 == 0 and attr_names else []

        return {
            "role": str(role) if role else None,
            "title": str(title) if title else None,
            "description": str(description) if description else None,
            "identifier": str(identifier) if identifier else None,
            "value": str(value)[:100] if value else None,  # 長すぎる場合は切り詰め
            "frame": frame,
            "available_attributes": available_attrs[:20],  # 最初の20個
        }
    except Exception as e:
        return {"error": str(e)}


def take_screenshot(action_id: str) -> Optional[str]:
    """スクリーンショットを撮影"""
    try:
        filename = f"{action_id}.png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        subprocess.run(
            ["screencapture", "-x", "-C", filepath],
            check=True,
            capture_output=True,
        )
        return filepath
    except Exception as e:
        print(f"  Screenshot failed: {e}")
        return None


def create_action_record(
    action_type: str,
    x: float,
    y: float,
    element_info: Dict[str, Any],
    app_info: Dict[str, str],
    screenshot_path: Optional[str],
    action_id: Optional[str] = None,
) -> Dict[str, Any]:
    """アクション記録を作成"""
    action_id = action_id or str(uuid.uuid4())[:8]
    return {
        "action_id": action_id,
        "timestamp": datetime.now().isoformat(),
        "action_type": action_type,
        "coordinates": {"x": x, "y": y},
        "app": app_info,
        "element": element_info,
        "screenshot_path": screenshot_path,
    }


# グローバル変数で記録を保持
recorded_actions = []
pending_text = ""
pending_key_events = []
pending_app_info = None
pending_last_time = None


def get_modifiers_from_flags(flags: int) -> list:
    mods = []
    if flags & kCGEventFlagMaskCommand:
        mods.append("Cmd")
    if flags & kCGEventFlagMaskShift:
        mods.append("Shift")
    if flags & kCGEventFlagMaskAlternate:
        mods.append("Option")
    if flags & kCGEventFlagMaskControl:
        mods.append("Control")
    return mods


def flush_pending_text():
    global pending_text, pending_key_events, pending_app_info, pending_last_time
    if not pending_key_events:
        return

    record = {
        "action_id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now().isoformat(),
        "action_type": "text_input",
        "app": pending_app_info or {},
        "text": pending_text,
        "key_events": pending_key_events,
    }
    recorded_actions.append(record)

    pending_text = ""
    pending_key_events = []
    pending_app_info = None
    pending_last_time = None


def record_key_action(action_type: str, app_info: Dict[str, str], key_event: Dict[str, Any]):
    record = {
        "action_id": str(uuid.uuid4())[:8],
        "timestamp": datetime.now().isoformat(),
        "action_type": action_type,
        "app": app_info,
        "key_event": key_event,
    }
    recorded_actions.append(record)


def handle_key_event(event_type, event):
    global pending_text, pending_key_events, pending_app_info, pending_last_time

    if event_type != kCGEventKeyDown:
        return

    now = time.time()
    app_info = get_frontmost_app()

    if pending_last_time and (now - pending_last_time > TEXT_INPUT_FLUSH_SECONDS):
        flush_pending_text()
    if pending_app_info and pending_app_info.get("bundle_id") != app_info.get("bundle_id"):
        flush_pending_text()

    keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
    flags = CGEventGetFlags(event)
    modifiers = get_modifiers_from_flags(flags)

    try:
        length, chars = CGEventKeyboardGetUnicodeString(event, 20, None, None)
        char_str = chars if chars else ""
    except Exception:
        char_str = ""

    key_event = {
        "event_type": "key_down",
        "keycode": int(keycode),
        "character": char_str if char_str else None,
        "modifiers": modifiers,
        "flags": int(flags),
    }

    is_shortcut = ("Cmd" in modifiers) or ("Control" in modifiers)
    is_special = keycode in SPECIAL_KEYCODES or not char_str or len(char_str) > 1

    if is_shortcut:
        flush_pending_text()
        record_key_action("key_shortcut", app_info, key_event)
        return

    if is_special:
        flush_pending_text()
        record_key_action("key_input", app_info, key_event)
        return

    # Text input aggregation
    pending_text += char_str
    pending_key_events.append(key_event)
    pending_app_info = app_info
    pending_last_time = now


def event_callback(proxy, event_type, event, refcon):
    """イベントコールバック"""
    global recorded_actions

    try:
        if event_type in (kCGEventKeyDown, kCGEventFlagsChanged):
            handle_key_event(event_type, event)
            return event

        flush_pending_text()

        # クリック位置を取得
        location = CGEventGetLocation(event)
        x, y = location.x, location.y

        # アクションタイプを判定
        if event_type == kCGEventLeftMouseDown:
            action_type = "left_click"
        elif event_type == kCGEventRightMouseDown:
            action_type = "right_click"
        else:
            action_type = "unknown"

        print(f"\n{'='*60}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {action_type.upper()} at ({x:.0f}, {y:.0f})")

        # アプリ情報取得
        app_info = get_frontmost_app()
        print(f"  App: {app_info.get('name', 'Unknown')}")

        # UI要素情報取得
        element_info = get_element_at_position(x, y)
        if "error" not in element_info:
            print(f"  Role: {element_info.get('role')}")
            print(f"  Title: {element_info.get('title')}")
            if element_info.get('identifier'):
                print(f"  ID: {element_info.get('identifier')}")
            if element_info.get('description'):
                print(f"  Desc: {element_info.get('description')}")
        else:
            print(f"  Element: {element_info.get('error')}")

        # スクリーンショット撮影
        action_id = str(uuid.uuid4())[:8]
        screenshot_path = take_screenshot(action_id)
        if screenshot_path:
            print(f"  Screenshot: {os.path.basename(screenshot_path)}")

        # 記録を保存
        record = create_action_record(
            action_type, x, y, element_info, app_info, screenshot_path, action_id=action_id
        )
        recorded_actions.append(record)

        print(f"  Total recorded: {len(recorded_actions)} actions")

    except Exception as e:
        print(f"Error in callback: {e}")

    return event


def save_session():
    """セッションをJSONファイルに保存"""
    flush_pending_text()
    if not recorded_actions:
        print("\nNo actions recorded.")
        return

    session = {
        "session_id": str(uuid.uuid4())[:8],
        "created_at": datetime.now().isoformat(),
        "total_actions": len(recorded_actions),
        "actions": recorded_actions,
    }

    filename = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"Session saved: {filepath}")
    print(f"Total actions: {len(recorded_actions)}")


def main():
    if not QUARTZ_AVAILABLE:
        print("Error: Quartz framework not available.")
        print("Please install pyobjc:")
        print("  pip install pyobjc-framework-Quartz pyobjc-framework-ApplicationServices")
        sys.exit(1)

    ensure_dirs()

    print("="*60)
    print("MVP Click Recorder")
    print("="*60)
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    print("Listening for clicks...")
    print("Press Ctrl+C to stop and save session.")
    print("="*60)

    # イベントマスク: 左クリック + 右クリック
    event_mask = (
        CGEventMaskBit(kCGEventLeftMouseDown)
        | CGEventMaskBit(kCGEventRightMouseDown)
        | CGEventMaskBit(kCGEventKeyDown)
        | CGEventMaskBit(kCGEventFlagsChanged)
    )

    # イベントタップを作成
    tap = CGEventTapCreate(
        kCGSessionEventTap,
        kCGHeadInsertEventTap,
        kCGEventTapOptionListenOnly,
        event_mask,
        event_callback,
        None,
    )

    if tap is None:
        print("\nError: Failed to create event tap.")
        print("Please grant Accessibility permission:")
        print("  System Preferences > Privacy & Security > Accessibility")
        print("  Add and enable Terminal (or your Python interpreter)")
        sys.exit(1)

    # RunLoopに追加
    run_loop_source = CFMachPortCreateRunLoopSource(None, tap, 0)
    CFRunLoopAddSource(CFRunLoopGetCurrent(), run_loop_source, kCFRunLoopCommonModes)
    CGEventTapEnable(tap, True)

    try:
        CFRunLoopRun()
    except KeyboardInterrupt:
        print("\n\nStopping...")
        save_session()
        print("Done.")


if __name__ == "__main__":
    main()
