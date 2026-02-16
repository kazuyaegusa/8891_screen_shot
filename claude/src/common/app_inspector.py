"""
macOS Accessibility APIでUI要素・アプリ・ブラウザ情報を取得するモジュール

【使用方法】
from common.app_inspector import AppInspector

inspector = AppInspector()
app_info = inspector.get_frontmost_app()
# => {"name": "Safari", "bundle_id": "com.apple.Safari", "pid": 1234}

element_info = inspector.get_element_at_position(500, 300)
# => {"role": "AXTextField", "title": "検索", "value": "入力テキスト", "frame": {...}, ...}

browser_info = inspector.get_browser_info(pid)
# => {"is_browser": True, "url": "https://...", "page_title": "..."}

【処理内容】
1. NSWorkspaceで最前面アプリ情報(名前, bundle_id, pid)を取得
2. AXUIElementでマウス座標のUI要素(role, title, value等 + 拡張属性)を取得
3. AXPosition/AXSizeからフレーム情報を計算
4. ブラウザ判定 + AXDocumentでURL取得

【必要な権限】
- アクセシビリティ: システム設定 > プライバシーとセキュリティ > アクセシビリティ
"""

import re
from typing import Any, Dict, Optional

try:
    from ApplicationServices import (
        AXUIElementCopyElementAtPosition,
        AXUIElementCreateSystemWide,
        AXUIElementCopyAttributeValue,
        AXUIElementCreateApplication,
    )
    from AppKit import NSWorkspace
    QUARTZ_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import Quartz/AppKit: {e}")
    QUARTZ_AVAILABLE = False

# ブラウザ判定用キーワード
_BROWSER_BUNDLE_KEYWORDS = ("safari", "chrome", "firefox", "edge", "arc", "brave")


class AppInspector:
    """Accessibility APIを使ってアプリ・UI要素・ブラウザ情報を取得するクラス"""

    def __init__(self):
        if not QUARTZ_AVAILABLE:
            raise RuntimeError(
                "Quartz framework not available. "
                "pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz "
                "pyobjc-framework-ApplicationServices"
            )

    def get_frontmost_app(self) -> Dict[str, Any]:
        """
        最前面のアプリケーション情報を取得

        Input: なし
        Output:
            Dict: {"name": str, "bundle_id": str, "pid": int}
            エラー時: {"name": "Unknown", "bundle_id": "", "pid": 0, "error": str}
        """
        try:
            ws = NSWorkspace.sharedWorkspace()
            app = ws.frontmostApplication()
            return {
                "name": app.localizedName(),
                "bundle_id": app.bundleIdentifier(),
                "pid": app.processIdentifier(),
            }
        except Exception as e:
            return {"name": "Unknown", "bundle_id": "", "pid": 0, "error": str(e)}

    @staticmethod
    def _get_ax_attribute(element, attr: str) -> Optional[Any]:
        """Accessibility要素の属性を取得"""
        try:
            err, value = AXUIElementCopyAttributeValue(element, attr, None)
            if err == 0 and value is not None:
                return value
            return None
        except Exception:
            return None

    def _parse_frame(self, element) -> Optional[Dict[str, float]]:
        """AXPosition/AXSizeからフレーム情報をパース"""
        try:
            position = self._get_ax_attribute(element, "AXPosition")
            size = self._get_ax_attribute(element, "AXSize")
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

    def get_element_at_position(self, x: float, y: float) -> Dict[str, Any]:
        """
        指定座標のUI要素情報を取得（拡張属性含む）

        Input:
            x: 画面X座標
            y: 画面Y座標
        Output:
            Dict: role, title, description, identifier, value, frame 等
            エラー時: {"error": str, "code": int}
        """
        try:
            system_wide = AXUIElementCreateSystemWide()
            err, element = AXUIElementCopyElementAtPosition(system_wide, x, y, None)

            if err != 0 or element is None:
                return {"error": f"No element found at ({x}, {y})", "code": err}

            role = self._get_ax_attribute(element, "AXRole")
            title = self._get_ax_attribute(element, "AXTitle")
            description = self._get_ax_attribute(element, "AXDescription")
            identifier = self._get_ax_attribute(element, "AXIdentifier")
            value = self._get_ax_attribute(element, "AXValue")
            frame = self._parse_frame(element)

            # 拡張属性
            focused = self._get_ax_attribute(element, "AXFocused")
            enabled = self._get_ax_attribute(element, "AXEnabled")
            placeholder = self._get_ax_attribute(element, "AXPlaceholderValue")
            role_description = self._get_ax_attribute(element, "AXRoleDescription")

            role_str = str(role) if role else None
            return {
                "role": role_str,
                "title": str(title) if title else None,
                "description": str(description) if description else None,
                "identifier": str(identifier) if identifier else None,
                "value": str(value)[:2000] if value else None,
                "frame": frame,
                "focused": bool(focused) if focused is not None else None,
                "enabled": bool(enabled) if enabled is not None else None,
                "placeholder": str(placeholder) if placeholder else None,
                "role_description": str(role_description) if role_description else None,
                "is_secure": role_str == "AXSecureTextField",
            }
        except Exception as e:
            return {"error": str(e)}

    def get_browser_info(self, pid: int) -> Dict[str, Any]:
        """
        指定PIDのアプリがブラウザの場合、URL・タイトル情報を取得

        Input:
            pid: プロセスID
        Output:
            Dict: {"is_browser": bool, "url": str|None, "page_title": str|None}
        """
        try:
            app_info = self.get_frontmost_app()
            bundle_id = (app_info.get("bundle_id") or "").lower()

            is_browser = any(kw in bundle_id for kw in _BROWSER_BUNDLE_KEYWORDS)
            if not is_browser:
                return {"is_browser": False, "url": None, "page_title": None}

            app_element = AXUIElementCreateApplication(pid)

            # AXDocumentでURLを取得
            url = self._get_ax_attribute(app_element, "AXDocument")

            # ウィンドウタイトルを取得
            windows = self._get_ax_attribute(app_element, "AXWindows")
            page_title = None
            if windows and len(windows) > 0:
                title = self._get_ax_attribute(windows[0], "AXTitle")
                if title:
                    page_title = str(title)

            return {
                "is_browser": True,
                "url": str(url) if url else None,
                "page_title": page_title,
            }
        except Exception as e:
            return {"is_browser": False, "url": None, "page_title": None}

    def get_full_info(self, x: float, y: float) -> Dict[str, Any]:
        """
        アプリ情報+UI要素情報をまとめて取得

        Input:
            x, y: 画面座標
        Output:
            Dict: {"app": {...}, "element": {...}, "coordinates": {"x": x, "y": y}}
        """
        return {
            "app": self.get_frontmost_app(),
            "element": self.get_element_at_position(x, y),
            "coordinates": {"x": x, "y": y},
        }
