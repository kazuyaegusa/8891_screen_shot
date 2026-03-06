# Phase 9 完了レポート: キャプチャシステム復旧 + 入力監視権限対応

## 実施日
2026-03-06

## 環境
- macOS Darwin 25.2.0 (Sequoia)
- Python 3.9
- anthropic SDK 0.37.1 → 0.84.0 にアップグレード

## 概要

PC再起動後にキャプチャシステム（capture_loop.py + 学習パイプライン）が完全停止していた問題を復旧した。

**発見された問題**:
- LaunchAgent プロセス（PID 78996）が SIGKILL で停止（2月28日以降6日間停止）
- 再起動後もプロセスは起動するが、イベントが一切キャプチャされない
- 原因: macOS の「入力監視（Input Monitoring）」権限が `/usr/bin/python3` に未付与
- CGEventTap は作成成功するが、イベントが配信されない状態
- Python stdout バッファリングにより LaunchAgent のログが一切書き出されず問題発見が遅延
- エージェント学習（agent/continuous_learner）が Anthropic API クレジット不足で失敗
- anthropic SDK 0.37.1 が httpx 0.28.x と非互換（`proxies` キーワード引数エラー）

## 変更内容

### LaunchAgent plist (`~/Library/LaunchAgents/com.kework.capture-loop.plist`)
- `python3 -u` フラグ追加（stdout バッファリング無効化）
- `PYTHONUNBUFFERED=1` 環境変数追加
- ログがリアルタイムで書き出されるようになった

### agent/config.py
- AIプロバイダー自動判定の優先順を変更: `anthropic` → `gemini` → `openai` から `gemini` → `anthropic` → `openai` に
- デフォルトプロバイダーを `anthropic` → `gemini` に変更
- Anthropic API クレジット不足の回避

### common/event_monitor.py
- CGEventTap 作成成功・有効化完了のデバッグログを追加
- 起動時の権限問題の診断を容易にした

### anthropic SDK アップグレード
- `pip install --upgrade anthropic`: 0.37.1 → 0.84.0
- httpx 0.28.x との `proxies` キーワード引数非互換を解消

### 入力監視権限（手動対応）
- システム設定 > プライバシーとセキュリティ > 入力監視 に `/usr/bin/python3` を追加
- これにより LaunchAgent 経由のプロセスが CGEventTap イベントを受信可能に

## 統計
- 変更ファイル: 3ファイル（+9行 / -6行）
- SDK アップグレード: anthropic 0.37.1 → 0.84.0

## テスト結果
テストディレクトリなし。実環境で動作確認を実施。

## 検証結果
- LaunchAgent プロセス（PID 34362）が正常稼働中
- クリック・テキスト入力・ショートカットイベントのキャプチャを確認
- スクリーンショットファイル生成を確認（click_cap_20260306_121043.json 等）
- 学習パイプライン（Gemini）がバックグラウンドで稼働中
- stderr にエラーなし

## 次フェーズへの申し送り
- PC再起動後に入力監視権限が再度リセットされないか経過観察
- 学習パイプラインの実際のスキル抽出結果を確認（セッション蓄積後）
- ストレージ使用量の経時モニタリング（定期クリーンアップの効果確認）
