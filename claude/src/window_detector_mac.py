"""
macOS用: マウスカーソル位置のウィンドウを検出するモジュール

【使用方法】
from window_detector_mac import WindowDetectorMac

detector = WindowDetectorMac()

# マウスカーソル位置のウィンドウ情報を取得
window_info = detector.get_window_at_cursor()
# => {"window_id": 1234, "name": "Safari", "x": 100, "y": 50, "width": 800, "height": 600, ...}

【処理内容】
1. Quartz (CGEvent) でマウスカーソル位置を取得
2. CGWindowListCopyWindowInfo で全ウィンドウ一覧を取得
3. マウス座標が含まれるウィンドウを特定（Z-order順で最前面）
4. ウィンドウのジオメトリ（位置・サイズ）と名前を返却

【必要環境】
- macOS
- pip install pyobjc-framework-Quartz
- アクセシビリティの許可は不要（CGWindowListはスクリーン録画権限のみ必要）
"""

import sys
from typing import Dict, Optional, Tuple, List

if sys.platform != "darwin":
    raise ImportError("このモジュールはmacOS専用です")

import Quartz
from Quartz import (
    CGEventGetLocation,
    CGEventCreate,
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGWindowListExcludeDesktopElements,
    kCGNullWindowID,
)
from AppKit import NSWorkspace


class WindowDetectorMac:
    """
    macOS用: マウスカーソル位置のウィンドウを検出するクラス
    Quartz API を使用
    """

    def __init__(self):
        """初期化"""
        pass

    def get_mouse_position(self) -> Tuple[int, int]:
        """
        現在のマウスカーソル位置を取得

        Input: なし
        Output:
            Tuple[int, int]: (x, y) マウス座標
        """
        event = CGEventCreate(None)
        point = CGEventGetLocation(event)
        return int(point.x), int(point.y)

    def get_all_windows(self) -> List[Dict]:
        """
        画面上の全ウィンドウ情報を取得（Z-order順: 最前面が先頭）

        Input: なし
        Output:
            List[Dict]: ウィンドウ情報のリスト
                各要素: {"window_id": int, "name": str, "owner": str,
                         "x": int, "y": int, "width": int, "height": int, "layer": int}
        """
        options = kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements
        window_list = CGWindowListCopyWindowInfo(options, kCGNullWindowID)

        results = []
        for win in window_list:
            bounds = win.get("kCGWindowBounds", {})
            if not bounds:
                continue

            results.append({
                "window_id": win.get("kCGWindowNumber", 0),
                "name": win.get("kCGWindowName", ""),
                "owner": win.get("kCGWindowOwnerName", ""),
                "owner_pid": win.get("kCGWindowOwnerPID", 0),
                "x": int(bounds.get("X", 0)),
                "y": int(bounds.get("Y", 0)),
                "width": int(bounds.get("Width", 0)),
                "height": int(bounds.get("Height", 0)),
                "layer": win.get("kCGWindowLayer", 0),
            })

        return results

    def _point_in_window(self, x: int, y: int, win: Dict) -> bool:
        """座標がウィンドウ範囲内かチェック"""
        return (
            win["x"] <= x <= win["x"] + win["width"]
            and win["y"] <= y <= win["y"] + win["height"]
        )

    def get_window_at_cursor(self) -> Optional[Dict]:
        """
        現在のマウスカーソル位置にあるウィンドウの全情報を取得
        Z-order で最前面のウィンドウを返す

        Input: なし
        Output:
            Dict: ウィンドウ情報
                {
                    "window_id": int,
                    "name": str,
                    "owner": str,
                    "x": int, "y": int,
                    "width": int, "height": int,
                    "mouse_x": int, "mouse_y": int
                }
            None: ウィンドウが見つからない場合
        """
        try:
            mouse_x, mouse_y = self.get_mouse_position()
            windows = self.get_all_windows()

            # 通常レイヤー（layer==0）のウィンドウのみ対象にし、
            # Z-order順（リスト先頭が最前面）で最初にヒットしたものを返す
            for win in windows:
                if win["layer"] != 0:
                    continue
                if win["width"] <= 1 or win["height"] <= 1:
                    continue
                if self._point_in_window(mouse_x, mouse_y, win):
                    win["mouse_x"] = mouse_x
                    win["mouse_y"] = mouse_y
                    return win

            return None
        except Exception as e:
            print(f"ウィンドウ検出エラー: {e}")
            return None

    def get_focused_window(self) -> Optional[Dict]:
        """
        最前面アプリのウィンドウ情報を取得（NSWorkspaceでPID特定）

        Input: なし
        Output:
            Dict: ウィンドウ情報（get_window_at_cursorと同じ形式）or None
        """
        try:
            ws = NSWorkspace.sharedWorkspace()
            app = ws.frontmostApplication()
            pid = app.processIdentifier()

            windows = self.get_all_windows()
            for win in windows:
                if win["owner_pid"] == pid and win["layer"] == 0:
                    if win["width"] > 1 and win["height"] > 1:
                        return win
            return None
        except Exception as e:
            print(f"最前面ウィンドウ取得エラー: {e}")
            return None

    def get_window_at_position(self, x: int, y: int) -> Optional[Dict]:
        """
        指定座標にあるウィンドウの全情報を取得

        Input:
            x: X座標
            y: Y座標
        Output:
            get_window_at_cursorと同じ形式 or None
        """
        try:
            windows = self.get_all_windows()

            for win in windows:
                if win["layer"] != 0:
                    continue
                if win["width"] <= 1 or win["height"] <= 1:
                    continue
                if self._point_in_window(x, y, win):
                    win["mouse_x"] = x
                    win["mouse_y"] = y
                    return win

            return None
        except Exception as e:
            print(f"ウィンドウ検出エラー: {e}")
            return None
