#!/usr/bin/env python3
"""
マウスカーソル位置の赤枠スクリーンショットを撮り続けるスクリプト（timer/eventモード対応）

使用方法:
    # ワンコマンド推奨（イベント駆動 + プライバシー保護 + 学習パイプライン）
    python3 capture_loop.py --trigger event --auto-learn

    # デフォルト: timerモード（3秒間隔）
    python3 capture_loop.py

    # 明示的にtimerモード
    python3 capture_loop.py --trigger timer --interval 5

    # イベント駆動モード（クリック・テキスト入力で撮影）
    python3 capture_loop.py --trigger event

    # プライバシーレベル指定
    python3 capture_loop.py --trigger event --privacy-level strict

    # プライバシー保護OFF（テスト用）
    python3 capture_loop.py --trigger event --privacy-level off

    # イベントモードのパラメータ調整
    python3 capture_loop.py --trigger event --click-debounce 1.0 --text-flush 2.0

    # ウィンドウモード + クロップのみ
    python3 capture_loop.py --mode window --crop-only

    # 停止: Ctrl+C

処理内容:
    【共通】
    - 起動時に session_id (UUID) を生成、全キャプチャに連番 sequence を付与
    - 各キャプチャに user_action（操作メタデータ）を付与してJSON保存
    - プライバシー保護（standard/strict/off）でパスワード・機密情報をフィルタ

    【timerモード】
    1. WindowScreenshot を初期化
    2. メインループで capture_window_at_cursor() を一定間隔で呼び出し（user_action.type="timer"）
    3. SIGINT/SIGTERM で graceful shutdown

    【eventモード】
    1. EventMonitor（CGEventTap）でクリック・キーボード・ショートカットを監視
    2. クリック時にAppInspectorでis_secureフラグを取得・追跡
    3. テキスト入力: secureフィールドなら記録スキップ
    4. イベント発生 → queue.Queue にジョブを投入（user_action付き）
    5. ワーカースレッドがキューからジョブを取り出し capture_window_at_cursor() 実行
    ※ CGEventTapコールバック内で重い処理をするとOSがタップを無効化するためキュー経由

    【--auto-learn】
    LearningPipeline をdaemonスレッドでバックグラウンド起動。Ctrl+C で両方停止。

入力:
    --trigger:        撮影トリガー timer(デフォルト) / event
    --interval:       撮影間隔・秒 (timerモードのみ, default: 3.0)
    --output:         保存先ディレクトリ (default: ./screenshots)
    --mode:           検出モード element(デフォルト) / window
    --crop-only:      クロップ画像のみ保存
    --click-debounce: クリックデバウンス秒 (eventモードのみ, default: 0.5)
    --text-flush:     テキストフラッシュ秒 (eventモードのみ, default: 1.0)
    --privacy-level:  プライバシーレベル standard(デフォルト) / strict / off
    --auto-learn:     学習パイプラインをバックグラウンドで自動起動

出力:
    output_dir/full_YYYYMMDD_HHMMSS.png   全画面スクショ（赤枠付き）
    output_dir/crop_YYYYMMDD_HHMMSS.png   ターゲット部分のみ
    output_dir/cap_YYYYMMDD_HHMMSS.json   キャプチャ情報JSON（プライバシーフィルタ適用済み）
"""

import argparse
import queue
import signal
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common.privacy_guard import PrivacyGuard, PrivacyLevel
from window_screenshot import WindowScreenshot

_running = True


def _signal_handler(signum, frame):
    """graceful shutdown"""
    global _running
    _running = False


def _print_banner(args, trigger, session_id):
    """起動バナーを表示"""
    print("=" * 50)
    print("Capture Loop - 常駐スクリーンショット")
    print("=" * 50)
    print(f"  Session : {session_id}")
    print(f"  Trigger : {trigger}")
    if trigger == "timer":
        print(f"  Interval: {args.interval}s")
    else:
        print(f"  Click debounce: {args.click_debounce}s")
        print(f"  Text flush    : {args.text_flush}s")
    print(f"  Output  : {Path(args.output).resolve()}")
    print(f"  Mode    : {args.mode}")
    print(f"  Crop only: {args.crop_only}")
    print(f"  Privacy : {args.privacy_level}")
    if args.auto_learn:
        print(f"  Auto-learn: ON (background)")
    print(f"  Stop    : Ctrl+C")
    print("=" * 50)


def _print_summary(count, errors):
    """終了サマリーを表示"""
    print()
    print("=" * 50)
    print(f"停止しました (撮影: {count}回, エラー: {errors}回)")
    print("=" * 50)


# ===== timerモード =====

def _run_timer_mode(ws, args, session_id):
    """timerモード: 一定間隔でキャプチャ"""
    count = 0
    errors = 0
    sequence = 0

    while _running:
        cycle_start = time.time()
        count += 1
        sequence += 1
        now = datetime.now().strftime("%H:%M:%S")

        session = {"session_id": session_id, "sequence": sequence}
        user_action = {"type": "timer"}

        try:
            result = ws.capture_window_at_cursor(
                crop_only=args.crop_only,
                user_action=user_action,
                session=session,
            )
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

def _capture_worker(ws, job_queue, crop_only, stats, session_id):
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
        user_action = job.get("user_action", {})
        stats["count"] += 1
        now = datetime.now().strftime("%H:%M:%S")

        session = {"session_id": session_id, "sequence": stats["count"]}

        try:
            result = ws.capture_window_at_cursor(
                crop_only=crop_only,
                prefix=prefix,
                user_action=user_action,
                session=session,
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


def _run_event_mode(ws, args, session_id, privacy_guard=None):
    """eventモード: クリック・テキスト入力・ショートカットでキャプチャ"""
    from common.event_monitor import EventMonitor

    job_queue = queue.Queue()
    stats = {"count": 0, "errors": 0}

    # secureフィールドフォーカス追跡（クリック先がパスワードフィールドか）
    _is_secure_focused = {"value": False}

    # AppInspectorインスタンス（is_secure判定用）
    _inspector = ws.inspector

    # コールバック: キューにジョブを投入するだけ（軽量）
    def on_click(data):
        # クリック先のis_secureフラグを取得
        if privacy_guard and _inspector:
            try:
                elem = _inspector.get_element_at_position(data["x"], data["y"])
                _is_secure_focused["value"] = elem.get("is_secure", False)
            except Exception:
                _is_secure_focused["value"] = False

        job_queue.put({
            "prefix": "click",
            "detail": f"{data['button']} ({data['x']:.0f},{data['y']:.0f})",
            "user_action": {
                "type": "click",
                "button": data["button"],
                "x": data["x"],
                "y": data["y"],
                "modifiers": data.get("modifiers", []),
                "timestamp": data.get("timestamp", time.time()),
            },
        })

    def on_text_input(data):
        # secureフィールドへの入力は記録しない
        if privacy_guard and _is_secure_focused["value"]:
            filtered = privacy_guard.filter_text_input(data["text"], is_secure=True)
            if filtered is None:
                print("[privacy] secureフィールドのテキスト入力をスキップ")
                return

        text_preview = data["text"][:20]
        job_queue.put({
            "prefix": "text",
            "detail": f'"{text_preview}"',
            "user_action": {
                "type": "text_input",
                "text": data["text"],
                "key_events": data.get("key_events", []),
            },
        })

    def on_shortcut(data):
        mod_str = "+".join(data["modifiers"])
        job_queue.put({
            "prefix": "shortcut",
            "detail": f"{mod_str}+{data['key']}",
            "user_action": {
                "type": "shortcut",
                "modifiers": data["modifiers"],
                "key": data["key"],
                "keycode": data.get("keycode", 0),
                "timestamp": data.get("timestamp", time.time()),
            },
        })

    monitor = EventMonitor(
        on_click=on_click,
        on_text_input=on_text_input,
        on_shortcut=on_shortcut,
        click_debounce=args.click_debounce,
        text_flush_sec=args.text_flush,
        privacy_guard=privacy_guard,
    )

    # ワーカースレッド起動
    worker = threading.Thread(
        target=_capture_worker,
        args=(ws, job_queue, args.crop_only, stats, session_id),
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

    print("Listening for clicks, text input, and shortcuts...")
    print()

    try:
        monitor.start()  # メインスレッドでブロッキング（CFRunLoop）
    except KeyboardInterrupt:
        monitor.stop()

    # ワーカー終了
    job_queue.put(None)
    worker.join(timeout=5.0)

    _print_summary(stats["count"], stats["errors"])


# ===== auto-learn =====

def _start_auto_learn(watch_dir: str):
    """LearningPipelineをdaemonスレッドでバックグラウンド起動"""
    try:
        from pipeline.config import PipelineConfig
        from pipeline.learning_pipeline import LearningPipeline

        config = PipelineConfig.from_env()
        config.watch_dir = Path(watch_dir).resolve()
        pipeline = LearningPipeline(config)

        thread = threading.Thread(target=pipeline.run, daemon=True)
        thread.start()
        print(f"[auto-learn] バックグラウンドでパイプライン起動: {config.watch_dir}")
        return pipeline
    except Exception as e:
        print(f"[auto-learn] パイプライン起動失敗（キャプチャは継続します）: {e}")
        return None


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
    parser.add_argument(
        "--privacy-level", choices=["standard", "strict", "off"], default="standard",
        help="プライバシーレベル: standard(デフォルト) / strict / off",
    )
    parser.add_argument(
        "--auto-learn", action="store_true",
        help="学習パイプラインをバックグラウンドで自動起動",
    )
    args = parser.parse_args()

    trigger = args.trigger

    # プライバシーガード初期化
    privacy_level = PrivacyLevel(args.privacy_level)
    privacy_guard = PrivacyGuard(privacy_level)

    # timerモードではSIGINTハンドラを先に設定
    if trigger == "timer":
        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

    ws = WindowScreenshot(output_dir=args.output, detection_mode=args.mode, privacy_guard=privacy_guard)

    # セッションID: 起動ごとにユニーク
    session_id = str(uuid.uuid4())

    _print_banner(args, trigger, session_id)

    # --auto-learn: LearningPipelineをdaemonスレッドで起動
    pipeline = None
    if args.auto_learn:
        pipeline = _start_auto_learn(args.output)

    if trigger == "timer":
        _run_timer_mode(ws, args, session_id)
    else:
        _run_event_mode(ws, args, session_id, privacy_guard=privacy_guard)

    # パイプライン停止
    if pipeline:
        pipeline.stop()


if __name__ == "__main__":
    main()
