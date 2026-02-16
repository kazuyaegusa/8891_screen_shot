#!/usr/bin/env python3
"""
アプリケーション情報取得モジュール (app_inspector.py)

マウス座標位置にあるUI要素のアプリケーション情報をAccessibility APIで取得する。
他モジュール(mouse_tracker, screenshot_recorder)から呼び出される共通モジュール。

使用方法:
    from app_inspector import AppInspector
    inspector = AppInspector()
    app_info = inspector.get_frontmost_app()
    element_info = inspector.get_element_at_position(x, y)

処理:
    - NSWorkspaceで最前面アプリ情報(名前, bundle_id)を取得
    - AXUIElementでマウス座標のUI要素(role, title, identifier等)を取得
    - AXPosition/AXSizeからフレーム情報を計算

必要な権限:
    - アクセシビリティ: システム設定 > プライバシーとセキュリティ > アクセシビリティ
"""

import re
from typing import Any, Dict, Optional

try:
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


class AppInspector:
    """Accessibility APIを使ってアプリ・UI要素情報を取得するクラス"""

    def __init__(self):
        if not QUARTZ_AVAILABLE:
            raise RuntimeError(
                "Quartz framework not available. "
                "pip install pyobjc-framework-Cocoa pyobjc-framework-Quartz "
                "pyobjc-framework-ApplicationServices"
            )

    def get_frontmost_app(self) -> Dict[str, str]:
        """最前面のアプリ情報を取得

        Returns:
            dict: {"name": str, "bundle_id": str} または {"name": "Unknown", ...}
        """
        try:
            ws = NSWorkspace.sharedWorkspace()
            app = ws.frontmostApplication()
            return {
                "name": app.localizedName(),
                "bundle_id": app.bundleIdentifier(),
            }
        except Exception as e:
            return {"name": "Unknown", "bundle_id": "", "error": str(e)}

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

    def get_element_at_position(self, x: float, y: float) -> Dict[str, Any]:
        """指定座標のUI要素情報を取得

        Args:
            x: 画面上のX座標
            y: 画面上のY座標

        Returns:
            dict: {
                "role": str, "title": str, "description": str,
                "identifier": str, "value": str, "frame": dict
            }
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

            return {
                "role": str(role) if role else None,
                "title": str(title) if title else None,
                "description": str(description) if description else None,
                "identifier": str(identifier) if identifier else None,
                "value": str(value)[:100] if value else None,
                "frame": frame,
            }
        except Exception as e:
            return {"error": str(e)}

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

    def get_full_info(self, x: float, y: float) -> Dict[str, Any]:
        """マウス位置のアプリ情報+UI要素情報をまとめて取得

        Args:
            x: 画面上のX座標
            y: 画面上のY座標

        Returns:
            dict: {"app": {...}, "element": {...}, "coordinates": {"x": x, "y": y}}
        """
        return {
            "app": self.get_frontmost_app(),
            "element": self.get_element_at_position(x, y),
            "coordinates": {"x": x, "y": y},
        }
