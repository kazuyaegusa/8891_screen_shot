"""
ActionPlayer: ActionStep モデル対応のアクション再生モジュール

【使用方法】
from agent.action_player import ActionPlayer
from agent.models import ActionStep

player = ActionPlayer()

# 単一ステップの実行
step = ActionStep(
    action_type="click",
    app_bundle_id="com.apple.finder",
    target_role="AXButton",
    target_title="開く",
    x=500.0, y=300.0,
)
result = player.play_action_step(step, dry_run=True)

# 複数ステップの順次実行
steps = [step1, step2, step3]
results = player.play_steps(steps, dry_run=False, delay=1.0)

# レガシー形式（Dict）での実行も可能
result = player.play_action(action_dict, dry_run=False)

【処理内容】
- ActionStep を受け取り、内部でレガシー Dict 形式に変換して操作を再生
- クリック操作: AXUIElement による要素検索 → 座標特定 → CGEvent でクリック
- キー操作: CGEvent でキー入力（text_input, key_input, key_shortcut）
- 要素検索優先順位: identifier → value → description → title+role → アプリ全体検索 → coordinate_fallback → Vision

【依存】
- agent.models.ActionStep
- macOS フレームワーク: Quartz, ApplicationServices, AppKit（アクセシビリティ権限が必要）
"""

import re
import time
from typing import Any, Dict, List, Optional, Tuple

from agent.models import ActionStep

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
        AXUIElementCreateApplication,
    )
    from AppKit import NSWorkspace, NSRunningApplication
    QUARTZ_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required frameworks: {e}")
    QUARTZ_AVAILABLE = False

BASE_FLAGS = 0x100
KEY_ACTION_TYPES = {"text_input", "key_input", "key_shortcut"}


# --- mvp_action_player.py からコピーした低レベル関数群 ---

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
        position = get_ax_attribute(element, "AXPosition")
        size = get_ax_attribute(element, "AXSize")
        if position and size:
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
            time.sleep(0.3)
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
    """キー系アクションを再生"""
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

    orig_x = target.get("coordinates", {}).get("x", 0)
    orig_y = target.get("coordinates", {}).get("y", 0)

    err, element_at_pos = AXUIElementCopyElementAtPosition(system_wide, orig_x, orig_y, None)

    if err == 0 and element_at_pos:
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

    # 6. アプリ全体検索（ウィンドウ位置が変わった場合のフォールバック）
    bundle_id = target.get("app", {}).get("bundle_id")
    if bundle_id:
        try:
            apps = NSRunningApplication.runningApplicationsWithBundleIdentifier_(bundle_id)
            if apps and len(apps) > 0:
                pid = apps[0].processIdentifier()
                app_element = AXUIElementCreateApplication(pid)
                all_elements = search_all_elements(app_element, max_depth=8)

                elem_info = target.get("element", {})
                t_identifier = elem_info.get("identifier")
                t_value = elem_info.get("value")
                t_description = elem_info.get("description")
                t_title = elem_info.get("title")
                t_role = elem_info.get("role")

                # identifier一致
                if t_identifier:
                    for _, info in all_elements:
                        if info.get("identifier") == t_identifier and info.get("frame"):
                            f = info["frame"]
                            return (f["x"] + f["width"] / 2, f["y"] + f["height"] / 2, "app_wide_identifier_match")

                # value一致
                if t_value:
                    for _, info in all_elements:
                        if info.get("value") == t_value and info.get("frame"):
                            f = info["frame"]
                            return (f["x"] + f["width"] / 2, f["y"] + f["height"] / 2, "app_wide_value_match")

                # description一致
                if t_description:
                    for _, info in all_elements:
                        if info.get("description") == t_description and info.get("frame"):
                            f = info["frame"]
                            return (f["x"] + f["width"] / 2, f["y"] + f["height"] / 2, "app_wide_description_match")

                # title + role一致
                if t_title and t_role:
                    for _, info in all_elements:
                        if info.get("title") == t_title and info.get("role") == t_role and info.get("frame"):
                            f = info["frame"]
                            return (f["x"] + f["width"] / 2, f["y"] + f["height"] / 2, "app_wide_title_role_match")
        except Exception:
            pass

    return (orig_x, orig_y, "coordinate_fallback")


def play_action(action: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    """
    単一アクションを再生（レガシー Dict 形式）

    Returns: 実行結果の辞書
    """
    action_id = action.get("action_id", "unknown")
    action_type = action.get("action_type", "left_click")
    app_info = action.get("app", {})

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

    if not dry_run:
        button = "right" if action_type == "right_click" else "left"
        click_at(x, y, button)
        result["success"] = True
    else:
        result["success"] = True
        result["dry_run"] = True

    return result


# --- ActionPlayer クラス: ActionStep モデル対応 ---

class ActionPlayer:
    """ActionStep モデルを受け取って操作を再生するプレイヤー"""

    def __init__(self) -> None:
        if not QUARTZ_AVAILABLE:
            print("Warning: Quartz frameworks not available. Playback will fail.")

    @staticmethod
    def _action_step_to_legacy_action(step: ActionStep) -> Dict[str, Any]:
        """ActionStep を mvp_action_player 互換の Dict 形式に変換"""
        action: Dict[str, Any] = {
            "action_id": step.description or f"{step.action_type}_{step.x}_{step.y}",
            "action_type": step.action_type,
            "app": {
                "bundle_id": step.app_bundle_id,
                "name": step.app_name,
            },
            "element": {
                "role": step.target_role,
                "title": step.target_title,
                "value": step.target_value,
                "description": step.target_description,
                "identifier": step.target_identifier,
            },
            "coordinates": {
                "x": step.x,
                "y": step.y,
            },
        }

        # キー入力系の場合
        if step.action_type == "text_input":
            action["key_events"] = step.key_events
            action["text"] = step.text
        elif step.action_type in ("key_input", "key_shortcut"):
            action["key_event"] = {
                "keycode": step.keycode,
                "flags": step.flags,
                "modifiers": step.modifiers,
            }

        return action

    @staticmethod
    def _find_element_with_vision_fallback(
        step: ActionStep,
        screenshot_path: Optional[str] = None,
    ) -> Optional[Tuple[float, float]]:
        """
        Vision ベースの要素検索フォールバック

        AXUIElement での検索が coordinate_fallback になった場合に、
        スクリーンショットを使って画像認識で要素位置を特定する。
        OPENAI_API_KEY 未設定時は None を返す（既存動作に影響なし）。
        """
        import os

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return None

        # スクリーンショットパスの決定
        ss_path = screenshot_path or step.screenshot_path
        if not ss_path:
            try:
                from agent.state_observer import StateObserver
                observer = StateObserver()
                state = observer.observe_current_state()
                ss_path = state.get("screenshot_path")
            except Exception:
                pass
        if not ss_path:
            return None

        # 要素説明テキストを構築
        parts = []
        if step.target_role:
            parts.append(f"role={step.target_role}")
        if step.target_title:
            parts.append(f"title={step.target_title}")
        if step.target_description:
            parts.append(f"description={step.target_description}")
        if step.target_value:
            parts.append(f"value={step.target_value}")
        if step.target_identifier:
            parts.append(f"identifier={step.target_identifier}")
        if step.description:
            parts.append(step.description)
        element_desc = ", ".join(parts) if parts else f"{step.action_type} target"

        try:
            import sys
            sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent.parent))
            from pipeline.ai_client import AIClient
            client = AIClient()
            result = client.find_element_by_vision(ss_path, element_desc)
            if result and result.get("confidence", 0) >= 0.5:
                return (float(result["x"]), float(result["y"]))
        except Exception:
            pass

        return None

    def play_action_step(self, step: ActionStep, dry_run: bool = False) -> Dict[str, Any]:
        """
        ActionStep を受け取って操作を再生

        coordinate_fallback になった場合は Vision フォールバックを試行してから
        クリックを実行する。クリックは最終的に1回だけ行う。
        """
        action_id = step.description or f"{step.action_type}_{step.x}_{step.y}"
        result: Dict[str, Any] = {
            "action_id": action_id,
            "success": False,
            "method": None,
            "coordinates_used": None,
            "error": None,
        }

        # アプリをアクティブ化
        if step.app_bundle_id:
            activate_app(step.app_bundle_id)

        # キー入力系はそのまま play_key_action()
        if step.action_type in KEY_ACTION_TYPES:
            legacy_action = self._action_step_to_legacy_action(step)
            return play_key_action(legacy_action, dry_run=dry_run)

        # 要素検索
        legacy_action = self._action_step_to_legacy_action(step)
        search_result = find_element_by_criteria(legacy_action)

        if search_result is None:
            result["error"] = "Element not found"
            return result

        x, y, method = search_result
        result["method"] = method

        # coordinate_fallback なら Vision フォールバックを試行
        if method == "coordinate_fallback":
            vision_coords = self._find_element_with_vision_fallback(step, step.screenshot_path)
            if vision_coords is not None:
                x, y = vision_coords
                result["method"] = "vision_fallback"

        result["coordinates_used"] = {"x": x, "y": y}

        if not dry_run:
            button = "right" if step.action_type == "right_click" else "left"
            click_at(x, y, button)
            result["success"] = True
        else:
            result["success"] = True
            result["dry_run"] = True

        return result

    def play_steps(
        self,
        steps: List[ActionStep],
        dry_run: bool = False,
        delay: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """
        ActionStep のリストを順番に実行

        Args:
            steps: 実行する ActionStep のリスト
            dry_run: True の場合、実際の操作は行わない
            delay: 各ステップ間の待機秒数

        Returns: 各ステップの実行結果リスト
        """
        results: List[Dict[str, Any]] = []
        total = len(steps)

        for i, step in enumerate(steps):
            print(f"[{i + 1}/{total}] {step.action_type}: {step.description or step.target_title or ''}")

            result = self.play_action_step(step, dry_run=dry_run)
            results.append(result)

            if result["success"]:
                coords = result.get("coordinates_used")
                coord_str = f" at ({coords['x']:.0f}, {coords['y']:.0f})" if coords else ""
                print(f"  OK (method: {result.get('method')}){coord_str}")
            else:
                print(f"  FAILED: {result.get('error')}")

            if i < total - 1:
                time.sleep(delay)

        success_count = sum(1 for r in results if r["success"])
        print(f"\nCompleted: {success_count}/{total} steps successful")

        return results
