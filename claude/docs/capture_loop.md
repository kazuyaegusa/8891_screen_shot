# capture_loop.py

マウスカーソル位置の赤枠スクリーンショットを撮り続けるスクリプト。
timer（一定間隔）と event（クリック・テキスト入力駆動）の2モードに対応。

## 入力（コマンドライン引数）

| 引数 | 型 | デフォルト | 説明 |
|------|-----|-----------|------|
| `--trigger` | str | `timer` | 撮影トリガー (`timer` / `event`) |
| `--interval` | float | 3.0 | 撮影間隔・秒 (timerモードのみ) |
| `--output` | str | `./screenshots` | 保存先ディレクトリ |
| `--mode` | str | `element` | 検出モード (`element` / `window`) |
| `--crop-only` | flag | false | クロップ画像のみ保存 |
| `--click-debounce` | float | 0.5 | クリックデバウンス秒 (eventモードのみ) |
| `--text-flush` | float | 1.0 | テキストフラッシュ秒 (eventモードのみ) |

## 出力

撮影ごとに以下のファイルを出力:

| ファイル | 説明 |
|---------|------|
| `full_YYYYMMDD_HHMMSS.png` | 全画面スクショ（赤枠付き） |
| `crop_YYYYMMDD_HHMMSS.png` | ターゲット部分のみ |
| `cap_YYYYMMDD_HHMMSS.json` | キャプチャ情報JSON |

eventモードでは prefix が `click` または `text` になる:
| ファイル | 説明 |
|---------|------|
| `click_full_YYYYMMDD_HHMMSS.png` | クリック時の全画面スクショ |
| `text_full_YYYYMMDD_HHMMSS.png` | テキスト入力フラッシュ時の全画面スクショ |

## トリガーモード

### timer（デフォルト）
- 一定間隔で `capture_window_at_cursor()` を呼び出す
- 既存動作と完全に互換

### event（イベント駆動）
- CGEventTapでクリック・キーボードを監視
- イベント発生 → `queue.Queue` 経由でワーカースレッドがキャプチャ実行
- CGEventTapコールバック内では軽量処理のみ（キュー投入）
- クリック: デバウンス付き（デフォルト0.5秒）
- テキスト入力: バッファリング → 一定時間無入力でフラッシュ（デフォルト1.0秒）

## スレッディングモデル（eventモード）

```
Main Thread (CFRunLoop):
  SIGINT → monitor.stop() → CFRunLoopStop()
  EventMonitor.start()
    → CGEventTapコールバック:
        click → queue.put({"prefix": "click"})
        text flush → queue.put({"prefix": "text"})

Worker Thread (daemon):
  queue.get() → WindowScreenshot.capture_window_at_cursor()
```

## 関数

### `main()`
- メインエントリーポイント
- argparseで引数をパース → triggerモードに応じてtimerまたはeventモードを実行

### `_run_timer_mode(ws, args)`
- timerモード実行。sleepループでキャプチャを繰り返す

### `_run_event_mode(ws, args)`
- eventモード実行。EventMonitor + ワーカースレッドでキャプチャ

### `_capture_worker(ws, job_queue, crop_only, stats)`
- ワーカースレッド。キューからジョブを取り出しキャプチャ実行

### `_signal_handler(signum, frame)`
- timerモード用シグナルハンドラ

### `_print_banner(args, trigger)` / `_print_summary(count, errors)`
- 起動バナー / 終了サマリー表示

## 依存モジュール

- `window_screenshot.WindowScreenshot` — 赤枠スクショ撮影の本体
- `common.event_monitor.EventMonitor` — イベント監視 (eventモードのみ)
