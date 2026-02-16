"""
macOS CGEventTapでクリック・キーボードイベントを監視するモジュール

【使用方法】
from common.event_monitor import EventMonitor

def on_click(data):
    print(f"Click: {data['button']} at ({data['x']}, {data['y']})")

def on_text(data):
    print(f"Text: {data['text']}")

def on_shortcut(data):
    print(f"Shortcut: {data['modifiers']}+{data['key']}")

monitor = EventMonitor(
    on_click=on_click,
    on_text_input=on_text,
    on_shortcut=on_shortcut,
    click_debounce=0.5,
    text_flush_sec=1.0,
)
monitor.start()   # メインスレッドでブロッキング（CFRunLoop）
# monitor.stop()  # 別スレッドから呼ぶ or SIGINTで停止

【処理内容】
1. CGEventTapでマウスクリック・キーボードイベントを監視
2. クリック: デバウンス後にon_clickコールバックを呼ぶ
3. キーボード: 修飾キー情報付きで入力バッファに蓄積し、flush_sec経過後にon_text_inputを呼ぶ
4. 修飾キー+通常キーはon_shortcutで通知
5. テキスト入力: CGEventKeyboardGetUnicodeStringで実際の文字に変換
6. CFRunLoopで待機（メインスレッドで実行する必要がある）

【必要な権限】
- アクセシビリティ: システム設定 > プライバシーとセキュリティ > アクセシビリティ
- 入力監視: システム設定 > プライバシーとセキュリティ > 入力監視（キーボード記録時）
"""

import sys
import time
import threading
from typing import Callable, List, Optional

if sys.platform != "darwin":
    raise ImportError("このモジュールはmacOS専用です")

import Quartz
from Quartz import (
    CGEventTapCreate,
    CGEventGetLocation,
    CGEventGetIntegerValueField,
    CGEventGetFlags,
    CGEventKeyboardGetUnicodeString,
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

# 修飾キーフラグ定数
_MOD_FLAGS = [(0x00100000, "Cmd"), (0x00020000, "Shift"), (0x00080000, "Option"), (0x00040000, "Control")]
_SHORTCUT_MODS = {"Cmd", "Control"}


class EventMonitor:
    """CGEventTapでクリック・キーボードイベントを監視するクラス"""

    def __init__(
        self,
        on_click: Optional[Callable] = None,
        on_text_input: Optional[Callable] = None,
        on_shortcut: Optional[Callable] = None,
        click_debounce: float = 0.5,
        text_flush_sec: float = 1.0,
        privacy_guard=None,
    ):
        """
        Input:
            on_click: クリック時コールバック fn({"button": str, "x": float, "y": float, "modifiers": list, "timestamp": float})
            on_text_input: テキスト入力フラッシュ時コールバック fn({"text": str, "key_events": list})
            on_shortcut: ショートカット時コールバック fn({"modifiers": list, "key": str, "keycode": int, "timestamp": float})
            click_debounce: クリックデバウンス秒
            text_flush_sec: テキストフラッシュ秒
            privacy_guard: PrivacyGuardインスタンス（Noneならフィルタなし）
        """
        self._on_click = on_click
        self._on_text_input = on_text_input
        self._on_shortcut = on_shortcut
        self._click_debounce = click_debounce
        self._text_flush_sec = text_flush_sec
        self._privacy_guard = privacy_guard

        self._last_click_time = 0.0
        self._text_buffer = []
        self._key_events: List[dict] = []
        self._text_timer: Optional[threading.Timer] = None
        self._run_loop = None
        self._running = False

    @staticmethod
    def _get_modifiers(event) -> List[str]:
        """CGEventGetFlagsでアクティブな修飾キーのリストを返す"""
        flags = CGEventGetFlags(event)
        return [name for mask, name in _MOD_FLAGS if flags & mask]

    @staticmethod
    def _get_unicode_char(event) -> str:
        """CGEventKeyboardGetUnicodeStringで実際の入力文字を取得。取得失敗時は空文字を返す"""
        try:
            length, chars = CGEventKeyboardGetUnicodeString(event, 1, None, None)
            if length > 0 and chars:
                return chars
            return ""
        except Exception:
            return ""

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
            modifiers = self._get_modifiers(event)
            self._on_click({
                "button": button,
                "x": loc.x,
                "y": loc.y,
                "modifiers": modifiers,
                "timestamp": now,
            })

    def _handle_key(self, event):
        """キーボードイベント処理（修飾キー判定・Unicode変換付き）"""
        keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
        modifiers = self._get_modifiers(event)
        now = time.time()

        # Cmd/Controlを含む場合はショートカットとして通知
        if _SHORTCUT_MODS & set(modifiers):
            if self._on_shortcut:
                char = self._get_unicode_char(event)
                self._on_shortcut({
                    "modifiers": modifiers,
                    "key": char if char else f"[key:{keycode}]",
                    "keycode": keycode,
                    "timestamp": now,
                })
            return

        # 通常入力
        if not self._on_text_input:
            return

        # 特殊キー処理
        if keycode == 36:  # Return
            self._text_buffer.append("\n")
            self._key_events.append({"char": "\n", "keycode": keycode, "timestamp": now})
            self._reset_text_timer()
            return
        if keycode == 48:  # Tab
            self._text_buffer.append("\t")
            self._key_events.append({"char": "\t", "keycode": keycode, "timestamp": now})
            self._reset_text_timer()
            return
        if keycode in (51, 53):  # Delete, Escape
            return

        # CGEventKeyboardGetUnicodeStringで実際の文字を取得
        char = self._get_unicode_char(event)
        if char:
            self._text_buffer.append(char)
            self._key_events.append({"char": char, "keycode": keycode, "timestamp": now})
            self._reset_text_timer()

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
            key_events = list(self._key_events)
            self._text_buffer.clear()
            self._key_events.clear()
            # プライバシーフィルタ: テキスト内の機密パターンを除去
            if self._privacy_guard:
                text = self._privacy_guard.redact_sensitive_patterns(text)
            self._on_text_input({"text": text, "key_events": key_events})

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
