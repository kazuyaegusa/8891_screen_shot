"""
スクリーンショット自動撮影＆画像解析システム - スクリーンショット撮影モジュール

処理内容:
  macOSのscreencaptureコマンドをsubprocessで呼び出し、画面全体のスクリーンショットを撮影する。
  タイムスタンプベースのファイル名で衝突を回避。

使用方法:
  from screenshot_capture import capture_screenshot
  path = capture_screenshot(output_dir=Path("./screenshots"), fmt="png")
  print(f"保存先: {path}")
"""

import subprocess
from datetime import datetime
from pathlib import Path


def capture_screenshot(output_dir: Path, fmt: str = "png") -> Path:
    """
    スクリーンショットを撮影し、指定ディレクトリに保存する。

    Args:
        output_dir: 画像の保存先ディレクトリ
        fmt: 画像フォーマット（png, jpg, tiff等）

    Returns:
        保存されたファイルのPath

    Raises:
        RuntimeError: screencaptureコマンドの実行に失敗した場合
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"screenshot_{timestamp}.{fmt}"
    filepath = output_dir / filename

    result = subprocess.run(
        ["screencapture", "-x", "-t", fmt, str(filepath)],
        capture_output=True,
        text=True,
        timeout=10,
    )

    if result.returncode != 0:
        raise RuntimeError(f"screencapture failed: {result.stderr}")

    if not filepath.exists():
        raise RuntimeError(f"Screenshot file was not created: {filepath}")

    return filepath
