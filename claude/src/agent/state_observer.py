"""
画面状態を観測するモジュール（AppInspector + mss/Pillow ラッパー）

【使用方法】
from agent.config import AgentConfig
from agent.state_observer import StateObserver

config = AgentConfig()
observer = StateObserver(config)

# 現在の画面状態を取得（最前面アプリ + スクリーンショット）
state = observer.observe_current_state()
# => {
#     "app": {"name": "Safari", "bundle_id": "...", "pid": 1234},
#     "screenshot_path": "/path/to/screenshots/state_20260217_120000.png",
#     "timestamp": "2026-02-17T12:00:00"
# }

# 指定座標のUI要素情報を取得
info = observer.observe_at_position(500, 300)
# => {"app": {...}, "element": {...}, "coordinates": {"x": 500, "y": 300}}

# スクリーンショットのみ撮影
path = observer.take_screenshot("my_prefix")
# => "/path/to/screenshots/my_prefix_20260217_120000.png"

# アプリのUI要素一覧を取得
elements = observer.get_visible_elements(pid=1234)
# => [{"role": "AXButton", "title": "OK", ...}, ...]

【処理内容】
1. AppInspector をラップし、最前面アプリ・UI要素・ブラウザ情報を取得
2. mss + Pillow でフルスクリーンのスクリーンショットを撮影・保存
3. Accessibility API で指定PIDアプリのUI要素を再帰的に検索

【依存】
- common.app_inspector (AppInspector)
- mss, Pillow（オプション: 未インストール時はスクリーンショット機能が None を返す）
- pyobjc-framework-ApplicationServices（macOS、オプション）
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# AppInspector（macOS 専用、未インストール時は graceful に無効化）
try:
    from common.app_inspector import AppInspector
    _INSPECTOR_AVAILABLE = True
except ImportError:
    _INSPECTOR_AVAILABLE = False

# mss + Pillow（スクリーンショット撮影用、未インストール時は無効化）
try:
    import mss
    from PIL import Image
    _SCREENSHOT_AVAILABLE = True
except ImportError:
    _SCREENSHOT_AVAILABLE = False

# Accessibility API（UI要素検索用）
try:
    from ApplicationServices import (
        AXUIElementCreateApplication,
        AXUIElementCopyAttributeValue,
    )
    _AX_AVAILABLE = True
except ImportError:
    _AX_AVAILABLE = False


class StateObserver:
    """画面状態を観測するクラス（AppInspector + スクリーンショット）"""

    def __init__(self, config=None):
        """
        初期化

        Input:
            config: AgentConfig インスタンス（screenshot_dir 等を参照）
                    None の場合はデフォルト設定を使用
        """
        self._config = config
        self._inspector: Optional[Any] = None

        if _INSPECTOR_AVAILABLE:
            try:
                self._inspector = AppInspector()
            except Exception:
                pass

        # スクリーンショット保存先
        if config and config.screenshot_dir:
            self._screenshot_dir = Path(config.screenshot_dir)
        else:
            self._screenshot_dir = Path.cwd() / "screenshots"
        self._screenshot_dir.mkdir(parents=True, exist_ok=True)

    def observe_current_state(self) -> Dict[str, Any]:
        """
        現在の画面状態を取得（最前面アプリ情報 + スクリーンショット）

        Input: なし
        Output:
            Dict:
                "app": 最前面アプリ情報 {"name", "bundle_id", "pid"} or None
                "screenshot_path": スクリーンショットのファイルパス or None
                "timestamp": ISO形式タイムスタンプ
        """
        timestamp = datetime.now()

        # 最前面アプリ情報
        app_info = None
        if self._inspector:
            try:
                app_info = self._inspector.get_frontmost_app()
            except Exception:
                pass

        # スクリーンショット撮影
        screenshot_path = self.take_screenshot("state")

        return {
            "app": app_info,
            "screenshot_path": screenshot_path,
            "timestamp": timestamp.isoformat(),
        }

    def observe_at_position(self, x: float, y: float) -> Dict[str, Any]:
        """
        指定座標のUI要素情報を取得（app_inspector.get_full_info のラッパー）

        Input:
            x: 画面X座標
            y: 画面Y座標
        Output:
            Dict: {"app": {...}, "element": {...}, "coordinates": {"x", "y"}}
                  AppInspector 未使用時は各値が None
        """
        if not self._inspector:
            return {
                "app": None,
                "element": None,
                "coordinates": {"x": x, "y": y},
            }

        try:
            return self._inspector.get_full_info(x, y)
        except Exception as e:
            return {
                "app": None,
                "element": {"error": str(e)},
                "coordinates": {"x": x, "y": y},
            }

    def take_screenshot(self, filename_prefix: str = "screenshot") -> Optional[str]:
        """
        フルスクリーンのスクリーンショットを撮影してパスを返す

        Input:
            filename_prefix: ファイル名の接頭辞
        Output:
            str: 保存したファイルの絶対パス
            None: mss/Pillow 未インストール等で撮影できなかった場合
        """
        if not _SCREENSHOT_AVAILABLE:
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.png"
            filepath = self._screenshot_dir / filename

            with mss.mss() as sct:
                # プライマリモニターをキャプチャ
                monitor = sct.monitors[1]
                raw = sct.grab(monitor)
                img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
                img.save(str(filepath))

            return str(filepath.absolute())
        except Exception:
            return None

    def get_visible_elements(self, pid: int, max_depth: int = 5) -> List[Dict[str, Any]]:
        """
        指定PIDアプリのUI要素一覧を再帰的に取得

        Input:
            pid: 対象アプリのプロセスID
            max_depth: 再帰探索の最大深さ（デフォルト5）
        Output:
            List[Dict]: UI要素のリスト。各要素は {"role", "title", "description", "frame"} を含む
                        AX API 未使用時は空リスト
        """
        if not _AX_AVAILABLE or not self._inspector:
            return []

        try:
            app_element = AXUIElementCreateApplication(pid)
            elements: List[Dict[str, Any]] = []
            self._collect_elements(app_element, elements, depth=0, max_depth=max_depth)
            return elements
        except Exception:
            return []

    def _collect_elements(
        self, element, results: List[Dict[str, Any]], depth: int, max_depth: int
    ) -> None:
        """
        Accessibility 要素を再帰的に収集する内部メソッド

        Input:
            element: AXUIElement
            results: 結果を蓄積するリスト（ミュータブル）
            depth: 現在の深さ
            max_depth: 最大深さ
        """
        if depth > max_depth:
            return

        # 現在の要素の情報を取得
        role = self._get_ax_attr(element, "AXRole")
        title = self._get_ax_attr(element, "AXTitle")
        description = self._get_ax_attr(element, "AXDescription")

        # フレーム情報
        frame = self._parse_element_frame(element)

        if role:
            results.append({
                "role": str(role),
                "title": str(title) if title else None,
                "description": str(description) if description else None,
                "frame": frame,
                "depth": depth,
            })

        # 子要素を再帰探索
        children = self._get_ax_attr(element, "AXChildren")
        if children:
            for child in children:
                self._collect_elements(child, results, depth + 1, max_depth)

    @staticmethod
    def _get_ax_attr(element, attr: str) -> Optional[Any]:
        """Accessibility 属性を安全に取得"""
        try:
            err, value = AXUIElementCopyAttributeValue(element, attr, None)
            if err == 0 and value is not None:
                return value
        except Exception:
            pass
        return None

    def _parse_element_frame(self, element) -> Optional[Dict[str, float]]:
        """AXPosition / AXSize からフレーム情報をパース"""
        if self._inspector:
            return self._inspector._parse_frame(element)
        return None
