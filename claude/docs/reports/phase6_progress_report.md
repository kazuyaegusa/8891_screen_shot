# 進捗報告書: マウス操作記録・自律再生システム

**報告日**: 2026年2月17日
**プロジェクト**: 8891_screen_shot — マウスカーソル位置 UI要素/ウィンドウ スクリーンショット自動撮影＋自律操作エージェント

---

## 1. プロジェクト概要

macOS 上でのユーザー操作（クリック・テキスト入力・ショートカット）を自動記録し、AI が操作パターンを学習して自律的に再現・応用するシステム。

**目標**: 人間の操作を観察→学習→自律再生する「操作のコパイロット」

---

## 2. 完了済みの開発フェーズ（Phase 1〜6）

| フェーズ | 内容 | 状態 |
|---------|------|------|
| Phase 1 | マウス位置スクリーンショット自動撮影（UI要素レベル検出） | **完了** |
| Phase 2 | 学習パイプライン（JSON → セッション分割 → AI スキル抽出） | **完了** |
| Phase 2.5 | プライバシー保護（パスワード・APIキー・カード番号の自動マスク） | **完了** |
| Phase 3 | 自律操作エージェント（ワークフロー学習・再生・目標ベース自律実行） | **完了** |
| Phase 3.5 | 常時学習フィードバックループ（daemon化・自動改善サイクル） | **完了** |
| Phase 4 | 再現性レポート＋業務パーツカタログ（A/B/Cランク評価） | **完了** |
| Phase 5 | 座標フォールバック問題解消（アプリ全体検索＋Vision連携） | **完了** |
| Phase 6 | **AI プロバイダー Gemini 対応（本フェーズ）** | **完了** |

---

## 3. 今回（Phase 6）で実施したこと

### 3.1 課題

OpenAI API キーが無効（Usage $0、API 未呼び出し）で、AI を使う機能が全て停止していた。

- ワークフロー分析（操作パターンの自動命名・パラメータ化）
- Vision 検索（画面から UI 要素の座標を推定）
- 自律実行時の状況判断・目標達成判定
- 実行結果の AI 検証

### 3.2 対応内容

**AI プロバイダーのマルチ対応化**（Gemini + OpenAI の切り替え可能に）

| 作業項目 | 詳細 |
|---------|------|
| AIClient リファクタリング | 7メソッド全てをプロバイダー共通ヘルパーで抽象化。Gemini/OpenAI固有の実装を分離 |
| デフォルト変更 | OpenAI → **Gemini（gemini-2.5-flash）** に変更。無料枠があり即座に利用開始可能 |
| 設定の自動判定 | `.env` に設定された API キーから使用プロバイダーを自動選択（Gemini 優先） |
| Vision フォールバック修正 | 画面要素検索の AI フォールバックが Gemini でも動作するよう修正 |
| Gemini 互換性対応 | JSON Schema の `additionalProperties` 除去、マークダウンブロック除去の2件を修正 |
| ドキュメント更新 | API仕様書、README、設定ガイド、イシュー記録を全て更新 |

### 3.3 変更ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `src/pipeline/ai_client.py` | Gemini プロバイダー追加、スキーマクリーニング、マークダウン除去 |
| `src/agent/config.py` | `ai_provider` / `gemini_api_key` / `gemini_model` 追加 |
| `src/agent/action_player.py` | Vision フォールバックのプロバイダー対応 |
| `docs/pipeline/ai_client.md` | Gemini 対応に全面更新 |
| `docs/agent/config.md` | 新規作成 |
| `README.md` | AI プロバイダー設定セクション追加 |
| `SESSION_SUMMARY.md` | Phase 5/6 完了を反映 |
| `CLAUDE_ISSUE.md` | Issue 12〜14 追記 |
| `.env` | Gemini API キーテンプレートに変更 |

---

## 4. 動作確認結果

Gemini API キー設定後、全3種類の AI 機能について動作確認を実施。

| テスト項目 | 結果 | 詳細 |
|-----------|------|------|
| テキスト生成 | **OK** | `_generate_text("Hello")` → "OK" を正常に返却 |
| JSON 構造化出力 | **OK** | ワークフロー分析で `{"name": "ゴミ箱を空にする", "confidence": 1.0}` を返却 |
| Vision（画像入力） | **OK** | スクリーンショットからゴミ箱アイコンの座標 `(31, 993)` を confidence 0.9 で検出 |

---

## 5. 現在動作する機能一覧

| 機能 | コマンド | 状態 |
|------|---------|------|
| 操作キャプチャ | `python3 capture_loop.py --trigger event` | **動作確認済み** |
| ワンコマンド運用 | `python3 capture_loop.py --trigger event --auto-learn` | **動作確認済み** |
| ワークフロー一覧 | `python3 -m agent.agent_cli list` | **動作確認済み** |
| 再現性レポート | `python3 -m agent.agent_cli report` | **動作確認済み** |
| AI ワークフロー分析 | `python3 -m agent.agent_cli learn --json-dir ./screenshots` | **Gemini で動作可能** |
| AI 自律実行 | `python3 -m agent.agent_cli run "目標テキスト"` | **Gemini で動作可能** |
| AI Vision 要素検出 | `find_element_by_vision()` | **Gemini で動作確認済み** |

---

## 6. 蓄積データ

| データ種別 | 件数 | 備考 |
|-----------|------|------|
| キャプチャ JSON | 1,275件 | click: 909, text: 266, shortcut: 100 |
| ワークフロー | 39件 | A ランク 6件、B ランク 33件 |
| フィードバック | 0件 | 偽データ退避済み、正規データはこれから蓄積 |

---

## 7. 今後のタスク（優先順）

### 短期（次回作業）

| タスク | 説明 | 見込み |
|--------|------|--------|
| ワークフロー再学習 | 1,275件のキャプチャを Gemini で再分析。AI 分析が初めて正常動作するため品質向上が期待 | API 呼び出し回数に依存 |
| 再現性レポート再生成 | 再学習後のデータでレポート・カタログを更新 | 自動生成 |
| 本番実行テスト | A ランクワークフローの実機再生テスト（Vision フォールバック込み） | 要手動確認 |

### 中期

| タスク | 説明 |
|--------|------|
| フィードバック蓄積 | 本番実行の成否データを蓄積し、ワークフロー品質を向上 |
| ステータスライフサイクル | DRAFT → TESTED → ACTIVE → DEPRECATED の自動昇降格 |
| 日常運用開始 | `--auto-learn` での継続キャプチャ＋学習サイクルを定常化 |

---

## 8. 技術的な解決事項（Issue 一覧）

| Issue | 内容 | 状態 |
|-------|------|------|
| #10 | AI 検証が全エラーパスで success=True を返す偽陽性 | 解決済み |
| #11 | 座標フォールバックによるクリック位置のずれ | 解決済み |
| #12 | OpenAI API キー無効で全 AI 機能停止 | **解決済み（Gemini 移行）** |
| #13 | Gemini JSON 出力で additionalProperties エラー | **解決済み** |
| #14 | Gemini Vision が ```json``` ブロックで応答し解析失敗 | **解決済み** |

---

## 9. システムアーキテクチャ

```
[操作記録層]
capture_loop.py → event_monitor.py → window_screenshot.py → cap_*.json + PNG

[学習層]
learning_pipeline.py → session_builder.py → ai_client.py (Gemini/OpenAI) → skill_writer.py → SKILL.md

[エージェント層]
agent_cli.py → autonomous_loop.py
                ├── state_observer.py（画面状態観測）
                ├── action_selector.py → ai_client.py（次アクション選択）
                ├── action_player.py → Quartz API（操作再生）+ Vision フォールバック
                └── execution_verifier.py → ai_client.py（実行検証）

[改善層]
continuous_learner.py → workflow_refiner.py → meta_analyzer.py → recovery_learner.py
```
