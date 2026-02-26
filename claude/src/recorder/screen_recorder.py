#!/usr/bin/env python3
"""
マウスクリック・キーボード操作を全て捕捉しながら画面を録画するプログラム（macOS専用）

使用方法:
    # デフォルト（15FPS、./recordings に保存）
    cd claude/src && python3 -m recorder.screen_recorder

    # FPSと出力先を指定
    python3 -m recorder.screen_recorder --fps 10 --output /tmp/rec

    # Retinaスケール半分（ファイルサイズ削減）
    python3 -m recorder.screen_recorder --scale 0.5

    # オーバーレイ無しで録画のみ
    python3 -m recorder.screen_recorder --no-overlay

    # 停止: Ctrl+C

処理内容:
    1. CGEventTap でマウスクリック・キーボード・ショートカットを監視（メインスレッド）
    2. バックグラウンドスレッドで mss によるスクリーンキャプチャ + cv2 で動画エンコード
    3. InputOverlay で入力イベントをフレーム上に視覚的に描画
    4. 録画停止時にイベントログ JSON を動画と同じディレクトリに保存

入力:
    --fps:        フレームレート（デフォルト: 15）
    --output:     保存先ディレクトリ（デフォルト: ./recordings）
    --scale:      スケール倍率（デフォルト: 1.0、Retina時は0.5推奨）
    --no-overlay: オーバーレイ描画を無効化
    --monitor:    録画対象モニター番号（デフォルト: 1 = プライマリ）

出力:
    output_dir/rec_YYYYMMDD_HHMMSS.mp4    録画動画ファイル
    output_dir/rec_YYYYMMDD_HHMMSS.json   イベントログ（全クリック・キー入力の時刻と座標）

必要な権限:
    - スクリーン録画: システム設定 > プライバシーとセキュリティ > 画面収録
    - アクセシビリティ: システム設定 > プライバシーとセキュリティ > アクセシビリティ
    - 入力監視: システム設定 > プライバシーとセキュリティ > 入力監視

必要パッケージ:
    pip install mss opencv-python-headless numpy pyobjc-framework-Quartz
"""

import argparse
import json
import signal
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import cv2
import mss
import numpy as np

# macOS 専用インポート
if sys.platform != "darwin":
    print("エラー: このプログラムはmacOS専用です")
    sys.exit(1)

try:
    from Quartz import (
        CGEventTapCreate,
        CGEventTapEnable,
        CGEventGetLocation,
        CGEventGetIntegerValueField,
        CGEventGetFlags,
        CGEventKeyboardGetUnicodeString,
        CFMachPortCreateRunLoopSource,
        CFRunLoopGetCurrent,
        CFRunLoopAddSource,
        CFRunLoopRun,
        CFRunLoopStop,
        kCGSessionEventTap,
        kCGHeadInsertEventTap,
        kCGEventTapOptionListenOnly,
        kCGEventLeftMouseDown,
        kCGEventRightMouseDown,
        kCGEventKeyDown,
        kCGKeyboardEventKeycode,
        kCFRunLoopCommonModes,
    )
except ImportError:
    print("エラー: pyobjc-framework-Quartz がインストールされていません")
    print("  pip install pyobjc-framework-Quartz")
    sys.exit(1)

from recorder.input_overlay import InputOverlay

# 修飾キーフラグ
_MOD_FLAGS = [
    (0x00100000, "Cmd"),
    (0x00020000, "Shift"),
    (0x00080000, "Option"),
    (0x00040000, "Control"),
]
_SHORTCUT_MODS = {"Cmd", "Control"}

# 特殊キーコードのマッピング
_KEYCODE_NAMES = {
    36: "Enter", 48: "Tab", 51: "Delete", 53: "Escape",
    123: "Left", 124: "Right", 125: "Down", 126: "Up",
    49: "Space", 116: "PageUp", 121: "PageDown",
    115: "Home", 119: "End", 117: "FwdDel",
}


def _get_modifiers(event) -> List[str]:
    """CGEventFlags から修飾キーリストを返す"""
    flags = CGEventGetFlags(event)
    return [name for mask, name in _MOD_FLAGS if flags & mask]


def _get_unicode_char(event) -> str:
    """CGEvent から入力文字を取得"""
    try:
        length, chars = CGEventKeyboardGetUnicodeString(event, 1, None, None)
        if length > 0 and chars:
            return chars
        return ""
    except Exception:
        return ""


class ScreenRecorder:
    """
    画面録画 + 入力イベント捕捉のメインクラス。

    Input:
        fps: フレームレート
        output_dir: 出力先ディレクトリ
        scale: スケール倍率（1.0 = 等倍）
        overlay_enabled: オーバーレイ描画の有効/無効
        monitor: 録画対象モニター番号

    Output:
        .mp4 動画ファイル + .json イベントログ
    """

    def __init__(
        self,
        fps: int = 15,
        output_dir: str = "./recordings",
        scale: float = 1.0,
        overlay_enabled: bool = True,
        monitor: int = 1,
    ):
        self._fps = fps
        self._output_dir = Path(output_dir)
        self._scale = scale
        self._overlay_enabled = overlay_enabled
        self._monitor = monitor

        self._overlay = InputOverlay() if overlay_enabled else None
        self._event_log: List[dict] = []
        self._event_lock = threading.Lock()

        self._running = False
        self._run_loop = None
        self._recording_id = str(uuid.uuid4())[:8]
        self._start_time: Optional[float] = None

        # 出力ファイルパス
        self._output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._video_path = self._output_dir / f"rec_{ts}.mp4"
        self._json_path = self._output_dir / f"rec_{ts}.json"

        # クリックデバウンス
        self._last_click_time = 0.0
        self._click_debounce = 0.15

        # キーボードバッファ（テキスト入力集約用）
        self._text_buffer: List[str] = []
        self._text_timer: Optional[threading.Timer] = None
        self._text_flush_sec = 1.0

    def _log_event(self, event_data: dict):
        """イベントをログに記録"""
        event_data["relative_time"] = time.time() - (self._start_time or time.time())
        with self._event_lock:
            self._event_log.append(event_data)

    def _event_callback(self, proxy, event_type, event, refcon):
        """CGEventTap コールバック"""
        try:
            if event_type in (kCGEventLeftMouseDown, kCGEventRightMouseDown):
                self._handle_click(event_type, event)
            elif event_type == kCGEventKeyDown:
                self._handle_key(event)
        except Exception:
            pass
        return event

    def _handle_click(self, event_type, event):
        """クリック処理"""
        now = time.time()
        if now - self._last_click_time < self._click_debounce:
            return
        self._last_click_time = now

        loc = CGEventGetLocation(event)
        button = "left" if event_type == kCGEventLeftMouseDown else "right"
        modifiers = _get_modifiers(event)

        # スケール適用（Retina座標 → ピクセル座標）
        x = int(loc.x * self._scale)
        y = int(loc.y * self._scale)

        if self._overlay:
            self._overlay.add_click(x, y, button)

        self._log_event({
            "type": "click",
            "button": button,
            "x": loc.x,
            "y": loc.y,
            "modifiers": modifiers,
            "timestamp": now,
        })

    def _handle_key(self, event):
        """キーボード処理"""
        keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
        modifiers = _get_modifiers(event)
        now = time.time()
        char = _get_unicode_char(event)

        # ショートカット（Cmd/Control + キー）
        if _SHORTCUT_MODS & set(modifiers):
            key_name = char if char else _KEYCODE_NAMES.get(keycode, f"[{keycode}]")
            display = "+".join(modifiers) + "+" + key_name

            if self._overlay:
                self._overlay.add_key(display)

            self._log_event({
                "type": "shortcut",
                "key": key_name,
                "keycode": keycode,
                "modifiers": modifiers,
                "timestamp": now,
            })
            return

        # 特殊キー
        if keycode in _KEYCODE_NAMES:
            key_name = _KEYCODE_NAMES[keycode]
            if self._overlay:
                self._overlay.add_key(key_name)

            self._log_event({
                "type": "key",
                "key": key_name,
                "keycode": keycode,
                "modifiers": modifiers,
                "timestamp": now,
            })
            return

        # 通常テキスト入力 → バッファに集約
        if char:
            self._text_buffer.append(char)
            self._reset_text_timer()

            self._log_event({
                "type": "key",
                "key": char,
                "keycode": keycode,
                "modifiers": modifiers,
                "timestamp": now,
            })

    def _reset_text_timer(self):
        """テキストフラッシュタイマーをリセット"""
        if self._text_timer:
            self._text_timer.cancel()
        self._text_timer = threading.Timer(self._text_flush_sec, self._flush_text)
        self._text_timer.daemon = True
        self._text_timer.start()

    def _flush_text(self):
        """テキストバッファをフラッシュしてオーバーレイに表示"""
        if self._text_buffer and self._overlay:
            text = "".join(self._text_buffer)
            # 長すぎるテキストは省略
            if len(text) > 30:
                text = text[:27] + "..."
            self._overlay.add_key(text)
        self._text_buffer.clear()

    def _capture_thread(self):
        """スクリーンキャプチャ + 動画書き込みスレッド"""
        with mss.mss() as sct:
            mon = sct.monitors[self._monitor]
            width = int(mon["width"] * self._scale)
            height = int(mon["height"] * self._scale)

            # VideoWriter 初期化
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(
                str(self._video_path), fourcc, self._fps, (width, height),
            )

            if not writer.isOpened():
                print(f"エラー: VideoWriter を開けませんでした: {self._video_path}")
                self._running = False
                return

            frame_interval = 1.0 / self._fps
            frame_count = 0

            print(f"録画開始: {width}x{height} @ {self._fps}FPS")
            print(f"動画: {self._video_path}")
            print(f"ログ: {self._json_path}")

            while self._running:
                t0 = time.time()

                # スクリーンキャプチャ
                img = sct.grab(mon)
                frame = np.array(img)

                # BGRA → BGR
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                # スケーリング
                if self._scale != 1.0:
                    frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

                # オーバーレイ描画
                if self._overlay:
                    frame = self._overlay.draw(frame)

                writer.write(frame)
                frame_count += 1

                # FPS制御
                elapsed = time.time() - t0
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

            writer.release()
            duration = time.time() - self._start_time if self._start_time else 0
            print(f"\n録画完了: {frame_count}フレーム, {duration:.1f}秒")

    def _save_event_log(self):
        """イベントログをJSONに保存"""
        duration = time.time() - self._start_time if self._start_time else 0
        with self._event_lock:
            events = list(self._event_log)

        log = {
            "recording_id": self._recording_id,
            "started_at": datetime.fromtimestamp(self._start_time).isoformat() if self._start_time else None,
            "ended_at": datetime.now().isoformat(),
            "duration_sec": round(duration, 2),
            "video_path": str(self._video_path),
            "fps": self._fps,
            "scale": self._scale,
            "total_events": len(events),
            "events": events,
        }

        with open(self._json_path, "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=2)

        click_count = sum(1 for e in events if e["type"] == "click")
        key_count = sum(1 for e in events if e["type"] in ("key", "shortcut"))
        print(f"イベントログ保存: クリック {click_count}件, キー入力 {key_count}件")

    def start(self):
        """
        録画を開始する。メインスレッドでCGEventTapを実行し、
        バックグラウンドスレッドでスクリーンキャプチャを行う。
        Ctrl+C で停止。
        """
        self._running = True
        self._start_time = time.time()

        # キャプチャスレッド開始
        capture = threading.Thread(target=self._capture_thread, daemon=True)
        capture.start()

        # CGEventTap 設定（メインスレッドで実行する必要がある）
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
            self._running = False
            capture.join(timeout=2)
            raise RuntimeError(
                "CGEventTap作成失敗。以下の権限を確認してください:\n"
                "  - システム設定 > プライバシーとセキュリティ > アクセシビリティ\n"
                "  - システム設定 > プライバシーとセキュリティ > 入力監視"
            )

        source = CFMachPortCreateRunLoopSource(None, tap, 0)
        self._run_loop = CFRunLoopGetCurrent()
        CFRunLoopAddSource(self._run_loop, source, kCFRunLoopCommonModes)
        CGEventTapEnable(tap, True)

        # SIGINT/SIGTERM ハンドラ
        def _signal_handler(sig, frame):
            print("\n停止中...")
            self.stop()

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        print("=" * 50)
        print("Screen Recorder - マウス/キーボード操作録画")
        print("=" * 50)
        print("Ctrl+C で停止")
        print()

        # メインスレッドで CFRunLoop 実行
        CFRunLoopRun()

        # 停止後の後処理
        capture.join(timeout=5)
        self._flush_text()
        self._save_event_log()

    def stop(self):
        """録画を停止する"""
        self._running = False
        if self._text_timer:
            self._text_timer.cancel()
        if self._run_loop:
            CFRunLoopStop(self._run_loop)


def main():
    parser = argparse.ArgumentParser(
        description="画面録画+マウス/キーボード操作キャプチャ (macOS)",
    )
    parser.add_argument("--fps", type=int, default=15, help="フレームレート (デフォルト: 15)")
    parser.add_argument("--output", type=str, default="./recordings", help="保存先ディレクトリ")
    parser.add_argument("--scale", type=float, default=1.0, help="スケール倍率 (Retina時 0.5 推奨)")
    parser.add_argument("--no-overlay", action="store_true", help="オーバーレイ描画を無効化")
    parser.add_argument("--monitor", type=int, default=1, help="録画対象モニター番号 (デフォルト: 1)")
    args = parser.parse_args()

    recorder = ScreenRecorder(
        fps=args.fps,
        output_dir=args.output,
        scale=args.scale,
        overlay_enabled=not args.no_overlay,
        monitor=args.monitor,
    )

    try:
        recorder.start()
    except RuntimeError as e:
        print(f"エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
