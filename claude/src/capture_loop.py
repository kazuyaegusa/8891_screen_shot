#!/usr/bin/env python3
"""
マウスカーソル位置の赤枠スクリーンショットを撮り続けるスクリプト（timer/eventモード対応）

使用方法:
    # デフォルト: timerモード（3秒間隔）
    python3 capture_loop.py

    # 明示的にtimerモード
    python3 capture_loop.py --trigger timer --interval 5

    # イベント駆動モード（クリック・テキスト入力で撮影）
    python3 capture_loop.py --trigger event

    # イベントモードのパラメータ調整
    python3 capture_loop.py --trigger event --click-debounce 1.0 --text-flush 2.0

    # ウィンドウモード + クロップのみ
    python3 capture_loop.py --mode window --crop-only

    # 停止: Ctrl+C

処理内容:
    【timerモード】
    1. WindowScreenshot を初期化
    2. メインループで capture_window_at_cursor() を一定間隔で呼び出し
    3. SIGINT/SIGTERM で graceful shutdown

    【eventモード】
    1. EventMonitor（CGEventTap）でクリック・キーボードを監視
    2. イベント発生 → queue.Queue にジョブを投入
    3. ワーカースレッドがキューからジョブを取り出し capture_window_at_cursor() 実行
    ※ CGEventTapコールバック内で重い処理をするとOSがタップを無効化するためキュー経由

入力:
    --trigger:        撮影トリガー timer(デフォルト) / event
    --interval:       撮影間隔・秒 (timerモードのみ, default: 3.0)
    --output:         保存先ディレクトリ (default: ./screenshots)
    --mode:           検出モード element(デフォルト) / window
    --crop-only:      クロップ画像のみ保存
    --click-debounce: クリックデバウンス秒 (eventモードのみ, default: 0.5)
    --text-flush:     テキストフラッシュ秒 (eventモードのみ, default: 1.0)

出力:
    output_dir/full_YYYYMMDD_HHMMSS.png   全画面スクショ（赤枠付き）
    output_dir/crop_YYYYMMDD_HHMMSS.png   ターゲット部分のみ
    output_dir/cap_YYYYMMDD_HHMMSS.json   キャプチャ情報JSON
"""

import argparse
import queue
import signal
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent))

from window_screenshot import WindowScreenshot

_running = True


def _signal_handler(signum, frame):
    """graceful shutdown"""
    global _running
    _running = False


def _print_banner(args, trigger):
    """起動バナーを表示"""
    print("=" * 50)
    print("Capture Loop - 常駐スクリーンショット")
    print("=" * 50)
    print(f"  Trigger : {trigger}")
    if trigger == "timer":
        print(f"  Interval: {args.interval}s")
    else:
        print(f"  Click debounce: {args.click_debounce}s")
        print(f"  Text flush    : {args.text_flush}s")
    print(f"  Output  : {Path(args.output).resolve()}")
    print(f"  Mode    : {args.mode}")
    print(f"  Crop only: {args.crop_only}")
    print(f"  Stop    : Ctrl+C")
    print("=" * 50)


def _print_summary(count, errors):
    """終了サマリーを表示"""
    print()
    print("=" * 50)
    print(f"停止しました (撮影: {count}回, エラー: {errors}回)")
    print("=" * 50)


# ===== timerモード =====

def _run_timer_mode(ws, args):
    """timerモード: 一定間隔でキャプチャ"""
    count = 0
    errors = 0

    while _running:
        cycle_start = time.time()
        count += 1
        now = datetime.now().strftime("%H:%M:%S")

        try:
            result = ws.capture_window_at_cursor(crop_only=args.crop_only)
            if result:
                json_path = result.get("json_path", "-")
                mode = result.get("detection_mode", "?")
                name = result.get("window_info", {}).get("name", "")
                print(f"[{now}] #{count} {mode}: {name}  -> {json_path}")
            else:
                print(f"[{now}] #{count} (検出失敗: カーソル位置にウィンドウなし)")
        except Exception as e:
            errors += 1
            print(f"[{now}] #{count} ERROR: {e}")

        elapsed = time.time() - cycle_start
        sleep_time = max(0, args.interval - elapsed)
        if _running and sleep_time > 0:
            time.sleep(sleep_time)

    _print_summary(count, errors)


# ===== eventモード =====

def _capture_worker(ws, job_queue, crop_only, stats):
    """ワーカースレッド: キューからジョブを取り出しキャプチャ実行

    CGEventTapコールバック内で重い処理をするとOSがタップを無効化する（1秒制限）
    ため、キュー経由でワーカースレッドに処理を委譲する。
    """
    while True:
        try:
            job = job_queue.get(timeout=1.0)
        except queue.Empty:
            continue

        if job is None:  # 終了シグナル
            break

        prefix = job.get("prefix", "event")
        detail = job.get("detail", "")
        stats["count"] += 1
        now = datetime.now().strftime("%H:%M:%S")

        try:
            result = ws.capture_window_at_cursor(
                crop_only=crop_only, prefix=prefix,
            )
            if result:
                json_path = result.get("json_path", "-")
                mode = result.get("detection_mode", "?")
                name = result.get("window_info", {}).get("name", "")
                print(f"[{now}] #{stats['count']} {prefix}({detail}) {mode}: {name}  -> {json_path}")
            else:
                print(f"[{now}] #{stats['count']} {prefix}({detail}) (検出失敗)")
        except Exception as e:
            stats["errors"] += 1
            print(f"[{now}] #{stats['count']} {prefix}({detail}) ERROR: {e}")


def _run_event_mode(ws, args):
    """eventモード: クリック・テキスト入力でキャプチャ"""
    from common.event_monitor import EventMonitor

    job_queue = queue.Queue()
    stats = {"count": 0, "errors": 0}

    # コールバック: キューにジョブを投入するだけ（軽量）
    def on_click(data):
        job_queue.put({
            "prefix": "click",
            "detail": f"{data['button']} ({data['x']:.0f},{data['y']:.0f})",
        })

    def on_text_input(data):
        text_preview = data["text"][:20]
        job_queue.put({
            "prefix": "text",
            "detail": f'"{text_preview}"',
        })

    monitor = EventMonitor(
        on_click=on_click,
        on_text_input=on_text_input,
        click_debounce=args.click_debounce,
        text_flush_sec=args.text_flush,
    )

    # ワーカースレッド起動
    worker = threading.Thread(
        target=_capture_worker,
        args=(ws, job_queue, args.crop_only, stats),
        daemon=True,
    )
    worker.start()

    # SIGINTでmonitor.stop()を呼ぶ
    def event_signal_handler(signum, frame):
        global _running
        _running = False
        monitor.stop()

    signal.signal(signal.SIGINT, event_signal_handler)
    signal.signal(signal.SIGTERM, event_signal_handler)

    print("Listening for clicks and text input...")
    print()

    try:
        monitor.start()  # メインスレッドでブロッキング（CFRunLoop）
    except KeyboardInterrupt:
        monitor.stop()

    # ワーカー終了
    job_queue.put(None)
    worker.join(timeout=5.0)

    _print_summary(stats["count"], stats["errors"])


# ===== main =====

def main():
    parser = argparse.ArgumentParser(
        description="マウスカーソル位置の赤枠スクリーンショットを撮り続ける"
    )
    parser.add_argument(
        "--trigger", choices=["timer", "event"], default="timer",
        help="撮影トリガー: timer=一定間隔 / event=クリック・テキスト入力 (default: timer)",
    )
    parser.add_argument(
        "--interval", type=float, default=3.0,
        help="撮影間隔・秒 (timerモードのみ, default: 3.0)",
    )
    parser.add_argument(
        "--output", type=str, default="./screenshots",
        help="保存先ディレクトリ (default: ./screenshots)",
    )
    parser.add_argument(
        "--mode", choices=["element", "window"], default="element",
        help="検出モード (default: element)",
    )
    parser.add_argument(
        "--crop-only", action="store_true",
        help="クロップ画像のみ保存（全画面スクショなし）",
    )
    parser.add_argument(
        "--click-debounce", type=float, default=0.5,
        help="クリックデバウンス秒 (eventモードのみ, default: 0.5)",
    )
    parser.add_argument(
        "--text-flush", type=float, default=1.0,
        help="テキストフラッシュ秒 (eventモードのみ, default: 1.0)",
    )
    args = parser.parse_args()

    trigger = args.trigger

    # timerモードではSIGINTハンドラを先に設定
    if trigger == "timer":
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

    ws = WindowScreenshot(output_dir=args.output, detection_mode=args.mode)

    _print_banner(args, trigger)

    if trigger == "timer":
        _run_timer_mode(ws, args)
    else:
        _run_event_mode(ws, args)


if __name__ == "__main__":
    main()
