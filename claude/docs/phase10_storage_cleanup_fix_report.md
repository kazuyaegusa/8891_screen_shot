# Phase 10 完了レポート: ストレージクリーンアップ修正（重複排除 + 即時削除）

## 実施日
2026-03-08

## 環境
- macOS Darwin 25.2.0
- Python 3.9 (system)
- LaunchAgent: com.kework.capture-loop (RunAtLoad + KeepAlive)

## 概要

キャプチャシステムのストレージが約41GBに膨張していた問題を修正。CleanupManagerのglobパターンが実際のファイル名と不一致で、クリーンアップが一度も動作していなかったことが根本原因。3層防御（入口・出口・セーフティネット）を実装し、今後の再発を防止。

## 変更内容

### 変更ファイル（4ファイル, +123行/-12行）

| ファイル | 変更 | 内容 |
|---|---|---|
| `src/pipeline/cleanup_manager.py` | +87/-3 | globパターン修正、`cleanup_processed_files()` 追加、`cleanup_duplicates()` 追加 |
| `src/pipeline/learning_pipeline.py` | +12/-3 | 毎サイクルで処理済みファイル即時削除を呼び出し |
| `src/window_screenshot.py` | +15/-0 | 保存前にMD5で前回画像と比較、同一ならスキップ |
| `CLAUDE_ISSUE.md` | +21/-0 | Issue 15 追記 |

### 主要な変更点

1. **CleanupManager globパターン修正**
   - Before: `cap_*.json`, `full_*.png`, `crop_*.png`（一致するファイルなし）
   - After: `*_cap_*.json`, `*_cap_*.png`, `*_full_*.png`, `*_crop_*.png`

2. **`cleanup_processed_files()` 新規追加**
   - `_processed.txt` に記録された学習済みJSONと関連画像を即座に削除
   - JSON内のscreenshotsパスを読み取って関連PNGも連鎖削除

3. **`cleanup_duplicates()` 新規追加**
   - MD5ハッシュで完全重複PNGを検出、各グループの最古1枚のみ残す

4. **保存前重複チェック（window_screenshot.py）**
   - `_last_image_hash` で前回画像とMD5比較
   - 同一画像の場合は保存をスキップし `None` を返す

### ストレージ削減結果

| 項目 | Before | After | 削減量 |
|---|---|---|---|
| screenshots/ | 4.9GB (12,276枚) | 275MB (665枚) | -4.6GB |
| recordings/ | 36GB (3ファイル) | 0B | -36GB |
| 合計 | ~41GB | 275MB | **-40.7GB** |

## テスト結果

テストディレクトリなし。手動検証で以下を確認:
- 重複画像7,672枚の削除成功
- 孤立JSON 3,607件の削除成功
- recordings/ 36GBの削除成功
- capture_loopプロセスの正常再起動（PID 8691）
- LaunchAgent KeepAliveによる自動復旧確認

## 発見された問題

- **Issue 15**: CleanupManagerのglobパターンが実際のファイル名と一致していなかった（Phase 8で実装されたが、パターンが誤っていた）
- Gemini APIのレート制限で学習パイプラインが頻繁に失敗（既知、今回のスコープ外）

## 次のフェーズへの申し送り

- ストレージ監視の自動アラート機能の検討（閾値超過時に通知）
- Gemini APIレート制限への対策（バッチ処理化、キュー制御）
- ワークフロー数が785件に到達、品質評価と整理が必要
