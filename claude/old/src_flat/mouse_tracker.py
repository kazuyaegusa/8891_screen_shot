#!/usr/bin/env python3
"""
マウス移動追跡モジュール (mouse_tracker.py)

マウスの移動をリアルタイムで記録するモジュール。
ポーリング方式でマウス座標を定期取得し、座標・タイムスタンプを記録する。
CGEventTapはバックグラウンドスレッドでRunLoop問題があるため、
CGEventCreate+CGEventGetLocationによるポーリング方式を採用。

使用方法:
    from mouse_tracker import MouseTracker

    tracker = MouseTracker(
        on_move=lambda data: print(data),
        move_interval=0.05,  # 50ms間隔で移動記録
    )
    tracker.start()  # ブロッキング (Ctrl+Cで停止)
    # または
    tracker.start_background()  # バックグラウンドスレッドで開始
    # ... 他の処理 ...
    tracker.stop()

処理:
    - CGEventCreate+CGEventGetLocationでマウス位置をポーリング
    - move_interval秒ごとにマウス位置を記録
    - 前回位置から動いていない場合は記録しない(静止時のノイズ除去)
    - マウスボタン状態もCGEventSourceButtonStateで監視してクリック検出
    - on_moveコールバックにイベントデータを渡す

必要な権限:
    - アクセシビリティ: システム設定 > プライバシーとセキュリティ > アクセシビリティ
"""

import threading
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

try:
    from Quartz import (
        CGEventCreate,
        CGEventGetLocation,
        CGEventSourceButtonState,
        kCGEventSourceStateCombinedSessionState,
        kCGMouseButtonLeft,
        kCGMouseButtonRight,
    )
    QUARTZ_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import Quartz: {e}")
    QUARTZ_AVAILABLE = False


class MouseTracker:
    """マウスの移動とクリックをポーリングで追跡するクラス"""

    def __init__(
        self,
        on_move: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_click: Optional[Callable[[Dict[str, Any]], None]] = None,
        move_interval: float = 0.05,
    ):
        """
        Args:
            on_move: マウス移動時のコールバック。
                     引数: {"x": float, "y": float, "timestamp": str, "elapsed": float}
            on_click: クリック時のコールバック。
                      引数: {"x": float, "y": float, "timestamp": str, "elapsed": float,
                             "button": "left"|"right"}
            move_interval: マウス移動の記録間隔(秒)。デフォルト0.05秒(50ms)
        """
        if not QUARTZ_AVAILABLE:
            raise RuntimeError(
                "Quartz framework not available. "
                "pip install pyobjc-framework-Quartz"
            )
        self.on_move = on_move
        self.on_click = on_click
        self.move_interval = move_interval
        self._start_time = 0.0
        self._move_log: List[Dict[str, Any]] = []
        self._click_log: List[Dict[str, Any]] = []
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._prev_x = -1.0
        self._prev_y = -1.0
        self._prev_left_down = False
        self._prev_right_down = False

    def _get_mouse_position(self):
        """現在のマウス位置を取得(どのスレッドからでも動作)"""
        event = CGEventCreate(None)
        if event is None:
            return None, None
        loc = CGEventGetLocation(event)
        return loc.x, loc.y

    def _is_button_pressed(self, button) -> bool:
        """マウスボタンの押下状態を取得"""
        return CGEventSourceButtonState(
            kCGEventSourceStateCombinedSessionState, button
        )

    def _make_event_data(
        self, x: float, y: float, button: Optional[str] = None
    ) -> Dict[str, Any]:
        """イベントデータを作成"""
        now = time.time()
        data = {
            "x": round(x, 2),
            "y": round(y, 2),
            "timestamp": datetime.now().isoformat(),
            "elapsed": round(now - self._start_time, 3),
        }
        if button:
            data["button"] = button
        return data

    def _poll_loop(self):
        """ポーリングループ: move_interval間隔でマウス位置を取得"""
        while self._running:
            x, y = self._get_mouse_position()
            if x is None:
                time.sleep(self.move_interval)
                continue

            # クリック検出
            left_down = self._is_button_pressed(kCGMouseButtonLeft)
            right_down = self._is_button_pressed(kCGMouseButtonRight)

            # 左クリック検出(押下開始時のみ)
            if left_down and not self._prev_left_down:
                data = self._make_event_data(x, y, button="left")
                self._click_log.append(data)
                if self.on_click:
                    self.on_click(data)

            # 右クリック検出(押下開始時のみ)
            if right_down and not self._prev_right_down:
                data = self._make_event_data(x, y, button="right")
                self._click_log.append(data)
                if self.on_click:
                    self.on_click(data)

            self._prev_left_down = left_down
            self._prev_right_down = right_down

            # 移動検出(位置が変わった場合のみ記録)
            if abs(x - self._prev_x) > 0.5 or abs(y - self._prev_y) > 0.5:
                data = self._make_event_data(x, y)
                self._move_log.append(data)
                if self.on_move:
                    self.on_move(data)
                self._prev_x = x
                self._prev_y = y

            time.sleep(self.move_interval)

    def start(self):
        """マウス追跡を開始する (ブロッキング、Ctrl+Cで停止)"""
        self._start_time = time.time()
        self._running = True
        try:
            self._poll_loop()
        except KeyboardInterrupt:
            self._running = False

    def start_background(self):
        """マウス追跡をバックグラウンドスレッドで開始する"""
        self._start_time = time.time()
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """マウス追跡を停止する"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def get_move_log(self) -> List[Dict[str, Any]]:
        """記録されたマウス移動ログを取得"""
        return list(self._move_log)

    def get_click_log(self) -> List[Dict[str, Any]]:
        """記録されたクリックログを取得"""
        return list(self._click_log)

    def get_stats(self) -> Dict[str, Any]:
        """記録統計を取得"""
        return {
            "total_moves": len(self._move_log),
            "total_clicks": len(self._click_log),
            "duration": round(time.time() - self._start_time, 2) if self._start_time else 0,
        }
