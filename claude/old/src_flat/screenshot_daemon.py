"""
スクリーンショット自動撮影＆画像解析システム - メインデーモン

処理内容:
  3秒間隔でスクリーンショットを撮影し、OpenAI Vision APIで画面内容を解析。
  結果をJSONLに保存し、古い画像を自動クリーンアップする。
  SIGTERM/SIGINTでgraceful shutdownを行う。

使用方法:
  # 直接実行
  python claude/src/screenshot_daemon.py

  # 制御スクリプトから
  ./claude/setup/screenshot_ctl.sh start
"""

import logging
import signal
import sys
import time
from pathlib import Path

# srcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import get_config
from screenshot_capture import capture_screenshot
from image_analyzer import ImageAnalyzer
from storage_manager import cleanup_old_screenshots, append_analysis, get_disk_usage_mb

# グローバルフラグ
_running = True


def _signal_handler(signum, frame):
    """シグナルハンドラ: graceful shutdownをトリガー"""
    global _running
    sig_name = signal.Signals(signum).name
    logging.info(f"Received {sig_name}, shutting down gracefully...")
    _running = False


def setup_logging(log_file: Path):
    """ロギングの設定"""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def run_daemon():
    """デーモンのメインループ"""
    global _running

    cfg = get_config()
    cfg.ensure_dirs()

    setup_logging(cfg.LOG_FILE)

    # 設定バリデーション
    errors = cfg.validate()
    if errors:
        for e in errors:
            logging.error(e)
        sys.exit(1)

    # シグナルハンドラ登録
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    # 画像解析クライアント初期化
    analyzer = ImageAnalyzer(api_key=cfg.OPENAI_API_KEY, model=cfg.OPENAI_MODEL)

    logging.info("Screenshot daemon started")
    logging.info(f"  Interval: {cfg.CAPTURE_INTERVAL}s")
    logging.info(f"  Retention: {cfg.RETENTION_SECONDS}s")
    logging.info(f"  Screenshots: {cfg.SCREENSHOT_DIR}")
    logging.info(f"  Analysis: {cfg.ANALYSIS_DIR}")

    cycle_count = 0

    while _running:
        cycle_start = time.time()
        cycle_count += 1

        try:
            # 1. スクリーンショット撮影
            image_path = capture_screenshot(cfg.SCREENSHOT_DIR, cfg.IMAGE_FORMAT)
            logging.info(f"[{cycle_count}] Captured: {image_path.name}")

            # 2. 画像解析（失敗してもキャプチャは継続）
            try:
                result = analyzer.analyze(image_path)
                append_analysis(cfg.ANALYSIS_DIR, result)
                desc_preview = result["description"][:80]
                logging.info(f"[{cycle_count}] Analyzed: {desc_preview}...")
            except Exception as e:
                logging.warning(f"[{cycle_count}] Analysis failed (non-fatal): {e}")

            # 3. クリーンアップ（10サイクルごと）
            if cycle_count % 10 == 0:
                deleted = cleanup_old_screenshots(cfg.SCREENSHOT_DIR, cfg.RETENTION_SECONDS)
                if deleted:
                    logging.info(f"[{cycle_count}] Cleaned up {len(deleted)} old screenshots")

                usage_mb = get_disk_usage_mb(cfg.SCREENSHOT_DIR)
                logging.info(f"[{cycle_count}] Disk usage: {usage_mb:.1f} MB")

        except Exception as e:
            logging.error(f"[{cycle_count}] Cycle error: {e}")

        # 4. 自己調整インターバル
        elapsed = time.time() - cycle_start
        sleep_time = max(0, cfg.CAPTURE_INTERVAL - elapsed)
        if _running and sleep_time > 0:
            time.sleep(sleep_time)

    logging.info(f"Screenshot daemon stopped after {cycle_count} cycles")


if __name__ == "__main__":
    run_daemon()
