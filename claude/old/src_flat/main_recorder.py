#!/usr/bin/env python3
"""
統合レコーダー (main_recorder.py)

マウス移動追跡 + スクリーンショット撮影 + アプリ情報取得を統合し、
画面操作の完全な記録を残すメインスクリプト。

使用方法:
    python3 main_recorder.py                    # 300枚、1秒間隔
    python3 main_recorder.py --count 100        # 100枚
    python3 main_recorder.py --interval 0.5     # 0.5秒間隔
    python3 main_recorder.py --move-interval 0.1  # マウス移動100ms間隔で記録
    python3 main_recorder.py --output ./my_session  # 出力先指定

処理:
    1. バックグラウンドスレッドでマウス移動を常時追跡(MouseTracker)
    2. 指定間隔でスクリーンショットを撮影(ScreenshotRecorder)
    3. 各スクリーンショット撮影時にマウス位置のUI要素・アプリ情報を取得(AppInspector)
    4. マウス軌跡 + スクリーンショット + アプリ情報をJSONセッションファイルに保存
    5. Ctrl+Cで途中停止しても記録済みデータを保存

出力:
    output_YYYYMMDD_HHMMSS/
    ├── session.json          # 全データ(スクリーンショット情報+マウス軌跡+アプリ情報)
    ├── screenshots/          # スクリーンショット画像(shot_0000.png ~ shot_0299.png)
    └── mouse_trail.json      # マウス移動ログ(詳細)

必要な権限:
    - アクセシビリティ: システム設定 > プライバシーとセキュリティ > アクセシビリティ
    - 画面収録: システム設定 > プライバシーとセキュリティ > 画面収録
"""

import argparse
import json
import os
import sys
import threading
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

# 同じsrcフォルダ内のモジュールをインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app_inspector import AppInspector
from mouse_tracker import MouseTracker
from screenshot_recorder import ScreenshotRecorder


class MainRecorder:
    """マウス追跡+スクリーンショット+アプリ情報の統合レコーダー"""

    def __init__(
        self,
        output_base: Optional[str] = None,
        screenshot_count: int = 300,
        screenshot_interval: float = 1.0,
        move_interval: float = 0.05,
    ):
        """
        Args:
            output_base: 出力先ベースディレクトリ。Noneの場合自動生成
            screenshot_count: スクリーンショット撮影枚数
            screenshot_interval: スクリーンショット撮影間隔(秒)
            move_interval: マウス移動記録間隔(秒)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if output_base:
            self.output_dir = output_base
        else:
            self.output_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..",
                f"output_{timestamp}",
            )

        self.screenshot_dir = os.path.join(self.output_dir, "screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)

        self.inspector = AppInspector()
        self.screenshot_recorder = ScreenshotRecorder(
            output_dir=self.screenshot_dir,
            total_count=screenshot_count,
            interval=screenshot_interval,
        )

        self._move_interval = move_interval
        self._mouse_tracker: Optional[MouseTracker] = None
        self._mouse_thread: Optional[threading.Thread] = None
        self._session_id = str(uuid.uuid4())[:8]
        self._screenshot_count = screenshot_count
        self._screenshot_interval = screenshot_interval

        # スクリーンショット撮影時の付加情報
        self._capture_records: List[Dict[str, Any]] = []
        # クリック時のアプリ情報
        self._click_records: List[Dict[str, Any]] = []

    def _on_mouse_click(self, click_data: Dict[str, Any]):
        """マウスクリック時のコールバック: アプリ・UI要素情報を付加"""
        try:
            info = self.inspector.get_full_info(click_data["x"], click_data["y"])
            record = {**click_data, **info}
            self._click_records.append(record)
        except Exception as e:
            record = {**click_data, "inspect_error": str(e)}
            self._click_records.append(record)

    def _start_mouse_tracking(self):
        """マウス追跡をバックグラウンドで開始(ポーリング方式)"""
        self._mouse_tracker = MouseTracker(
            on_click=self._on_mouse_click,
            move_interval=self._move_interval,
        )
        self._mouse_tracker.start_background()

    def _on_capture(self, index: int, filepath: str) -> Dict[str, Any]:
        """スクリーンショット撮影ごとのコールバック"""
        # 現在のマウス位置はトラッカーの最新ログから取得
        move_log = self._mouse_tracker.get_move_log() if self._mouse_tracker else []
        if move_log:
            latest = move_log[-1]
            x, y = latest["x"], latest["y"]
        else:
            x, y = 0.0, 0.0

        # アプリ情報・UI要素情報を取得
        info = self.inspector.get_full_info(x, y)

        # この撮影時点までのマウス移動数・クリック数
        stats = self._mouse_tracker.get_stats() if self._mouse_tracker else {}

        return {
            "mouse_position": {"x": x, "y": y},
            "app": info.get("app", {}),
            "element": info.get("element", {}),
            "mouse_stats": stats,
        }

    def _on_progress(self, current: int, total: int):
        """進捗表示"""
        pct = current / total * 100
        bar_len = 40
        filled = int(bar_len * current / total)
        bar = "#" * filled + "-" * (bar_len - filled)

        # 現在のマウス位置を取得
        move_log = self._mouse_tracker.get_move_log() if self._mouse_tracker else []
        if move_log:
            latest = move_log[-1]
            pos_str = f"Mouse:({latest['x']:.0f},{latest['y']:.0f})"
        else:
            pos_str = "Mouse:(--,--)"

        stats = self._mouse_tracker.get_stats() if self._mouse_tracker else {}
        moves = stats.get("total_moves", 0)
        clicks = stats.get("total_clicks", 0)

        print(
            f"\r  [{bar}] {current}/{total} ({pct:.0f}%) "
            f"{pos_str} Moves:{moves} Clicks:{clicks}",
            end="",
            flush=True,
        )
        if current == total:
            print()  # 最後は改行

    def run(self):
        """記録を開始する"""
        print("=" * 60)
        print("Screen & Mouse Recorder")
        print("=" * 60)
        print(f"  Session ID   : {self._session_id}")
        print(f"  Output       : {self.output_dir}")
        print(f"  Screenshots  : {self._screenshot_count} shots")
        print(f"  SS Interval  : {self._screenshot_interval}s")
        print(f"  Mouse Interval: {self._move_interval}s")
        print(f"  Est. Duration: ~{self._screenshot_count * self._screenshot_interval:.0f}s")
        print("=" * 60)
        print()
        print("Starting mouse tracking...")

        # マウス追跡をバックグラウンドで開始
        self._start_mouse_tracking()
        # スレッドが起動するのを少し待つ
        time.sleep(0.5)

        print("Mouse tracking started.")
        print(f"Taking {self._screenshot_count} screenshots...")
        print()

        try:
            # スクリーンショットバッチ撮影
            capture_results = self.screenshot_recorder.take_batch(
                on_capture=self._on_capture,
                on_progress=self._on_progress,
            )
        except KeyboardInterrupt:
            print("\n\nInterrupted! Saving recorded data...")
            capture_results = []

        # マウス追跡を停止
        if self._mouse_tracker:
            self._mouse_tracker.stop()

        # セッションデータを構築
        session = self._build_session(capture_results)

        # 保存
        self._save_session(session)
        self._save_mouse_trail()

        print()
        print("=" * 60)
        print("Recording complete!")
        print(f"  Screenshots : {len(capture_results)}")
        mouse_stats = self._mouse_tracker.get_stats() if self._mouse_tracker else {}
        print(f"  Mouse moves : {mouse_stats.get('total_moves', 0)}")
        print(f"  Clicks      : {mouse_stats.get('total_clicks', 0)}")
        print(f"  Duration    : {mouse_stats.get('duration', 0)}s")
        print(f"  Output dir  : {self.output_dir}")
        print("=" * 60)

    def _build_session(self, capture_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """セッションJSONデータを構築"""
        mouse_stats = self._mouse_tracker.get_stats() if self._mouse_tracker else {}

        return {
            "session_id": self._session_id,
            "created_at": datetime.now().isoformat(),
            "config": {
                "screenshot_count": self._screenshot_count,
                "screenshot_interval": self._screenshot_interval,
                "move_interval": self._move_interval,
            },
            "summary": {
                "total_screenshots": len(capture_results),
                "total_mouse_moves": mouse_stats.get("total_moves", 0),
                "total_clicks": mouse_stats.get("total_clicks", 0),
                "duration_seconds": mouse_stats.get("duration", 0),
            },
            "screenshots": capture_results,
            "clicks": self._click_records,
        }

    def _save_session(self, session: Dict[str, Any]):
        """セッションをJSONに保存"""
        filepath = os.path.join(self.output_dir, "session.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session, f, ensure_ascii=False, indent=2)
        print(f"  Session saved: {filepath}")

    def _save_mouse_trail(self):
        """マウス移動ログを別ファイルに保存(詳細データ)"""
        if not self._mouse_tracker:
            return

        trail_data = {
            "session_id": self._session_id,
            "move_log": self._mouse_tracker.get_move_log(),
            "click_log": self._mouse_tracker.get_click_log(),
            "stats": self._mouse_tracker.get_stats(),
        }

        filepath = os.path.join(self.output_dir, "mouse_trail.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(trail_data, f, ensure_ascii=False, indent=2)
        print(f"  Mouse trail saved: {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Screen & Mouse Recorder - マウス移動+スクリーンショット+アプリ情報を統合記録"
    )
    parser.add_argument(
        "--count", type=int, default=300,
        help="スクリーンショット撮影枚数 (default: 300)",
    )
    parser.add_argument(
        "--interval", type=float, default=1.0,
        help="スクリーンショット撮影間隔(秒) (default: 1.0)",
    )
    parser.add_argument(
        "--move-interval", type=float, default=0.05,
        help="マウス移動記録間隔(秒) (default: 0.05)",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="出力先ディレクトリ (default: auto-generated)",
    )
    args = parser.parse_args()

    recorder = MainRecorder(
        output_base=args.output,
        screenshot_count=args.count,
        screenshot_interval=args.interval,
        move_interval=args.move_interval,
    )

    try:
        recorder.run()
    except KeyboardInterrupt:
        print("\n\nForce stopped.")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
