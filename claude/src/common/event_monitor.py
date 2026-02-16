"""
macOS CGEventTapでクリック・キーボードイベントを監視するモジュール

【使用方法】
from common.event_monitor import EventMonitor

def on_click(data):
    print(f"Click: {data['button']} at ({data['x']}, {data['y']})")

def on_text(data):
    print(f"Text: {data['text']}")

monitor = EventMonitor(
    on_click=on_click,
    on_text_input=on_text,
    click_debounce=0.5,
    text_flush_sec=1.0,
)
monitor.start()   # メインスレッドでブロッキング（CFRunLoop）
# monitor.stop()  # 別スレッドから呼ぶ or SIGINTで停止

【処理内容】
1. CGEventTapでマウスクリック・キーボードイベントを監視
2. クリック: デバウンス後にon_clickコールバックを呼ぶ
3. キーボード: 入力バッファに蓄積し、flush_sec経過後にon_text_inputを呼ぶ
4. CFRunLoopで待機（メインスレッドで実行する必要がある）

【必要な権限】
- アクセシビリティ: システム設定 > プライバシーとセキュリティ > アクセシビリティ
- 入力監視: システム設定 > プライバシーとセキュリティ > 入力監視（キーボード記録時）
"""

import sys
import time
import threading
from typing import Callable, Optional

if sys.platform != "darwin":
    raise ImportError("このモジュールはmacOS専用です")

import Quartz
from Quartz import (
    CGEventTapCreate,
    CGEventGetLocation,
    CGEventGetIntegerValueField,
    CGEventTapEnable,
    kCGSessionEventTap,
    kCGHeadInsertEventTap,
    kCGEventTapOptionListenOnly,
    kCGEventLeftMouseDown,
    kCGEventRightMouseDown,
    kCGEventKeyDown,
    kCGKeyboardEventKeycode,
)
from Quartz import CFMachPortCreateRunLoopSource, CFRunLoopGetCurrent, CFRunLoopAddSource, CFRunLoopRun, CFRunLoopStop, kCFRunLoopCommonModes


class EventMonitor:
    """CGEventTapでクリック・キーボードイベントを監視するクラス"""

    def __init__(
        self,
        on_click: Optional[Callable] = None,
        on_text_input: Optional[Callable] = None,
        click_debounce: float = 0.5,
        text_flush_sec: float = 1.0,
    ):
        """
        Input:
            on_click: クリック時コールバック fn({"button": str, "x": float, "y": float})
            on_text_input: テキスト入力フラッシュ時コールバック fn({"text": str})
            click_debounce: クリックデバウンス秒
            text_flush_sec: テキストフラッシュ秒
        """
        self._on_click = on_click
        self._on_text_input = on_text_input
        self._click_debounce = click_debounce
        self._text_flush_sec = text_flush_sec

        self._last_click_time = 0.0
        self._text_buffer = []
        self._text_timer: Optional[threading.Timer] = None
        self._run_loop = None
        self._running = False

    def _event_callback(self, proxy, event_type, event, refcon):
        """CGEventTapコールバック（軽量に保つ）"""
        try:
            if event_type in (kCGEventLeftMouseDown, kCGEventRightMouseDown):
                self._handle_click(event_type, event)
            elif event_type == kCGEventKeyDown:
                self._handle_key(event)
        except Exception:
            pass
        return event

    def _handle_click(self, event_type, event):
        """クリックイベント処理（デバウンス付き）"""
        now = time.time()
        if now - self._last_click_time < self._click_debounce:
            return
        self._last_click_time = now

        if self._on_click:
            loc = CGEventGetLocation(event)
            button = "left" if event_type == kCGEventLeftMouseDown else "right"
            self._on_click({"button": button, "x": loc.x, "y": loc.y})

    def _handle_key(self, event):
        """キーボードイベント処理（バッファに蓄積）"""
        if not self._on_text_input:
            return

        keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)

        # 簡易的にキーコードを文字に変換（主要キーのみ）
        char = self._keycode_to_char(keycode)
        if char:
            self._text_buffer.append(char)
            self._reset_text_timer()

    def _keycode_to_char(self, keycode: int) -> Optional[str]:
        """キーコードを文字に変換（簡易版）"""
        # Return/Enter/Tab/Deleteなどの特殊キーは無視しないが区切りとして扱う
        key_map = {
            36: "\n",  # Return
            48: "\t",  # Tab
            51: "",    # Delete (backspace)
            53: "",    # Escape
        }
        if keycode in key_map:
            if key_map[keycode]:
                return key_map[keycode]
            return None

        # 通常キーはキーコードで表現（正確な文字変換にはTISが必要だが簡易版）
        if 0 <= keycode <= 50 or 65 <= keycode <= 92:
            return f"[key:{keycode}]"
        return None

    def _reset_text_timer(self):
        """テキストフラッシュタイマーをリセット"""
        if self._text_timer:
            self._text_timer.cancel()
        self._text_timer = threading.Timer(self._text_flush_sec, self._flush_text)
        self._text_timer.daemon = True
        self._text_timer.start()

    def _flush_text(self):
        """テキストバッファをフラッシュしてコールバック呼び出し"""
        if self._text_buffer and self._on_text_input:
            text = "".join(self._text_buffer)
            self._text_buffer.clear()
            self._on_text_input({"text": text})

    def start(self):
        """
        イベント監視を開始（メインスレッドでブロッキング）
        停止するにはstop()を別スレッドから呼ぶ
        """
        event_mask = (
            (1 << kCGEventLeftMouseDown)
            | (1 << kCGEventRightMouseDown)
            | (1 << kCGEventKeyDown)
        )

        tap = CGEventTapCreate(
            kCGSessionEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionListenOnly,
            event_mask,
            self._event_callback,
            None,
        )

        if tap is None:
            raise RuntimeError(
                "CGEventTap作成失敗。アクセシビリティ権限を確認してください。"
                "システム設定 > プライバシーとセキュリティ > アクセシビリティ"
            )

        source = CFMachPortCreateRunLoopSource(None, tap, 0)
        self._run_loop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(self._run_loop, source, kCFRunLoopCommonModes)
        CGEventTapEnable(tap, True)

        self._running = True
        CFRunLoopRun()

    def stop(self):
        """イベント監視を停止"""
        self._running = False
        # テキストバッファをフラッシュ
        if self._text_timer:
            self._text_timer.cancel()
        self._flush_text()

        if self._run_loop:
            CFRunLoopStop(self._run_loop)
