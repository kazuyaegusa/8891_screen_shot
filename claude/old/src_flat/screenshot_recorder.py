#!/usr/bin/env python3
"""
スクリーンショット撮影モジュール (screenshot_recorder.py)

指定回数のスクリーンショットを一定間隔で撮影するモジュール。
撮影タイミングでのマウス位置情報も合わせて記録できる。

使用方法:
    from screenshot_recorder import ScreenshotRecorder
    recorder = ScreenshotRecorder(
        output_dir="output/screenshots",
        total_count=300,
        interval=1.0,
    )
    recorder.take_one("shot_001")  # 1枚撮影
    results = recorder.take_batch(on_capture=callback)  # バッチ撮影

処理:
    - macOS標準の screencapture コマンドでスクリーンショット撮影
    - 指定間隔(デフォルト1秒)で指定回数(デフォルト300)撮影
    - 撮影ごとにコールバックを呼び出し、付加情報を受け取れる
    - 結果をリストで返却

必要な権限:
    - 画面収録: システム設定 > プライバシーとセキュリティ > 画面収録
"""

import os
import subprocess
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


class ScreenshotRecorder:
    """スクリーンショットを撮影・管理するクラス"""

    def __init__(
        self,
        output_dir: str = "output/screenshots",
        total_count: int = 300,
        interval: float = 1.0,
    ):
        """
        Args:
            output_dir: スクリーンショット保存先ディレクトリ
            total_count: 撮影する合計枚数
            interval: 撮影間隔(秒)
        """
        self.output_dir = output_dir
        self.total_count = total_count
        self.interval = interval
        os.makedirs(self.output_dir, exist_ok=True)

    def take_one(self, name: str) -> Optional[str]:
        """1枚スクリーンショットを撮影

        Args:
            name: ファイル名(拡張子なし)

        Returns:
            保存先ファイルパス or None(失敗時)
        """
        filename = f"{name}.png"
        filepath = os.path.join(self.output_dir, filename)
        try:
            subprocess.run(
                ["screencapture", "-x", "-C", filepath],
                check=True,
                capture_output=True,
            )
            return filepath
        except Exception as e:
            print(f"  Screenshot failed: {e}")
            return None

    def take_batch(
        self,
        on_capture: Optional[Callable[[int, str], Dict[str, Any]]] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> List[Dict[str, Any]]:
        """バッチでスクリーンショットを撮影

        Args:
            on_capture: 撮影ごとのコールバック。
                        引数: (index, filepath) -> 付加情報dict
            on_progress: 進捗コールバック。
                         引数: (current, total)

        Returns:
            撮影結果のリスト。各要素:
            {
                "index": int,
                "filepath": str,
                "timestamp": str,
                "elapsed": float,
                "extra": dict  # on_captureの戻り値
            }
        """
        results = []
        start_time = time.time()

        for i in range(self.total_count):
            name = f"shot_{i:04d}"
            filepath = self.take_one(name)

            elapsed = round(time.time() - start_time, 3)
            record = {
                "index": i,
                "filepath": filepath,
                "timestamp": datetime.now().isoformat(),
                "elapsed": elapsed,
                "extra": {},
            }

            if filepath and on_capture:
                try:
                    extra = on_capture(i, filepath)
                    if extra:
                        record["extra"] = extra
                except Exception as e:
                    record["extra"] = {"error": str(e)}

            results.append(record)

            if on_progress:
                on_progress(i + 1, self.total_count)

            # 最後の1枚以外はインターバルを待つ
            if i < self.total_count - 1:
                time.sleep(self.interval)

        return results

    def get_output_dir(self) -> str:
        """出力ディレクトリパスを返す"""
        return self.output_dir
