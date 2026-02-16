#!/usr/bin/env python3
"""
マウスカーソル位置の赤枠スクリーンショットを一定間隔で撮り続けるスクリプト

使用方法:
    # デフォルト（3秒間隔、./screenshots に保存）
    python3 claude/src/capture_loop.py

    # 間隔・出力先を指定
    python3 claude/src/capture_loop.py --interval 5 --output /tmp/capture

    # ウィンドウモード（UI要素ではなくウィンドウ全体に赤枠）
    python3 claude/src/capture_loop.py --mode window

    # クロップのみ保存（全画面スクショなし）
    python3 claude/src/capture_loop.py --crop-only

    # 停止: Ctrl+C

処理内容:
    1. WindowScreenshot を初期化（detection_mode 選択可能）
    2. メインループで capture_window_at_cursor() を繰り返し呼び出し
    3. 撮影結果（JSONパス・画像パス）をコンソールに出力
    4. SIGINT/SIGTERM で graceful shutdown（撮影回数サマリーを表示）

入力:
    --interval: 撮影間隔（秒）デフォルト3.0
    --output:   保存先ディレクトリ デフォルト ./screenshots
    --mode:     検出モード element(デフォルト) / window
    --crop-only: クロップ画像のみ保存

出力:
    output_dir/full_YYYYMMDD_HHMMSS.png   全画面スクショ（赤枠付き）
    output_dir/crop_YYYYMMDD_HHMMSS.png   ターゲット部分のみ
    output_dir/cap_YYYYMMDD_HHMMSS.json   キャプチャ情報JSON
"""

import argparse
import signal
import sys
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


def main():
    parser = argparse.ArgumentParser(
        description="マウスカーソル位置の赤枠スクリーンショットを撮り続ける"
    )
    parser.add_argument(
        "--interval", type=float, default=3.0,
        help="撮影間隔(秒) (default: 3.0)",
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
    args = parser.parse_args()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    ws = WindowScreenshot(output_dir=args.output, detection_mode=args.mode)

    print("=" * 50)
    print("Capture Loop - 常駐スクリーンショット")
    print("=" * 50)
    print(f"  Interval : {args.interval}s")
    print(f"  Output   : {Path(args.output).resolve()}")
    print(f"  Mode     : {args.mode}")
    print(f"  Crop only: {args.crop_only}")
    print(f"  Stop     : Ctrl+C")
    print("=" * 50)

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

    print()
    print("=" * 50)
    print(f"停止しました (撮影: {count}回, エラー: {errors}回)")
    print("=" * 50)


if __name__ == "__main__":
    main()
