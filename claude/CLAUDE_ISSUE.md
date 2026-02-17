# CLAUDE_ISSUE - 解決に失敗した処理と解決方法

## Screenshot Daemon

### Issue 1: macOS画面収録権限（確認済み）
- **問題**: `screencapture`コマンドが `could not create image from display` エラーで失敗する
- **原因**: macOS 10.15以降、画面収録にはユーザー承認が必要。Claude Code等のサンドボックス環境では権限が付与されていない
- **解決方法**: システム設定 > プライバシーとセキュリティ > 画面収録 > 使用するターミナルアプリ（Terminal.app, iTerm2等）を追加
- **備考**: デーモンは解析失敗時もキャプチャを継続する設計。権限付与後にターミナルを再起動すれば動作する

### Issue 2: LaunchAgentでPython環境が見つからない
- **問題**: LaunchAgentから起動するとPythonやpipパッケージが見つからない
- **原因**: LaunchAgentはログインシェルの環境変数を引き継がない
- **解決方法**: `install.sh`でフルパスのPythonを`plist`に埋め込む。`which python3`の結果を使用

### Issue 3: .envファイルが見つからない
- **問題**: デーモン起動時に`OPENAI_API_KEY`が空で解析に失敗する
- **原因**: WorkingDirectoryが不正、または.envファイルが未作成
- **解決方法**: `config.py`でリポジトリルートからの相対パスで.envを読み込む。.envファイルを作成して`OPENAI_API_KEY=sk-...`を記載

## Screen & Mouse Recorder

### Issue 4: CGEventTapがバックグラウンドスレッドでマウス移動を検出できない
- **問題**: MouseTrackerをバックグラウンドスレッドで実行すると、CFRunLoopRunが正常に動作せずマウス移動イベントが0件になる
- **原因**: CGEventTapはRunLoopベースで動作し、バックグラウンドスレッドではRunLoopが適切に処理されない場合がある
- **解決方法**: CGEventTap+CFRunLoopからポーリング方式に変更。`CGEventCreate(None)` + `CGEventGetLocation()`で現在のマウス位置を取得し、`CGEventSourceButtonState()`でクリック状態を監視。この方式はどのスレッドからでも確実に動作する
- **結果**: 5秒間のテストで49件のマウス移動と2件のクリックを正常に検出

### Issue 5: Discord等のアプリでAXUIElement取得に失敗する (code: -25211)
- **問題**: Discordなどの一部アプリでマウス位置のUI要素取得時に`-25211`エラーが発生する
- **原因**: Electron系アプリはAccessibility APIのサポートが限定的で、一部の座標でUI要素が返されない
- **現状**: アプリ名・bundle_idは正常に取得可能。UI要素情報はerrorとして記録し、処理は継続する設計
- **将来の対策**: AI画像認識によるフォールバック検討

## Phase 2.5: プライバシー保護

### Issue 6: パスワード・個人情報が平文で記録される

- **発見日**: 2026-02-16
- **状態**: 解決済み
- **問題**:
  - テキスト入力の全文字（パスワード含む）がJSONに平文保存
  - AXValue にパスワードフィールドの値がそのまま入る
  - ブラウザURLにトークン・APIキーが含まれる
  - パスワード入力画面のスクリーンショットが撮影される
- **解決方法**:
  - `common/privacy_guard.py` を新規作成し全フィルタロジックを集約
  - PrivacyLevel 3段階（standard/strict/off）で制御
  - AXSecureTextField検出 → テキスト入力スキップ + AXValueマスク + スクショスキップ
  - URL機密パラメータマスク
  - テキスト内APIキー・カード番号パターン除去
- **影響ファイル**: privacy_guard.py(新規), app_inspector.py, event_monitor.py, json_saver.py, window_screenshot.py, capture_loop.py

## Phase 3: 自律操作エージェント

### Issue 7: Vision APIの座標推定精度

- **発見日**: 2026-02-17
- **状態**: 既知の制約
- **問題**: GPT-5 VisionでUI要素の座標を推定する際、ピクセル単位の精度が保証されない
- **対策**:
  - Accessibility API（AXUIElement）を第一優先で使用
  - Vision推定は最終フォールバックとして位置づけ
  - find_element_by_criteria の検索優先順位: identifier → value → description → title+role → 座標 → Vision
- **影響ファイル**: action_player.py, ai_client.py (find_element_by_vision)

### Issue 8: Electron系アプリ（Discord, Cursor等）のAX API制限

- **発見日**: 2026-02-17
- **状態**: 既知の制約（Issue 5の延長）
- **問題**: Electron系アプリではAccessibility APIの応答が限定的で、要素検索の成功率が低い
- **対策**:
  - 座標フォールバックを活用（記録時の座標を使用）
  - Vision APIで画面から要素位置を推定
  - 将来的にはアプリ固有のブリッジ（Chrome DevTools Protocol等）を検討
- **影響ファイル**: action_player.py, state_observer.py

### Issue 9: 危険操作の自動実行防止

- **発見日**: 2026-02-17
- **状態**: 解決済み
- **問題**: Mail/Slack等の送信系アプリで操作が自動実行されるリスク
- **解決方法**:
  - AgentConfig.dangerous_apps でアプリリストを管理
  - 該当アプリ操作時に確認プロンプトを表示
  - `--no-confirm` フラグで無効化可能（明示的なオプトイン）
- **影響ファイル**: config.py, autonomous_loop.py, action_selector.py

### Issue 10: AI検証がエラー時にsuccess=Trueを返す（偽陽性）

- **発見日**: 2026-02-17
- **状態**: 解決済み
- **問題**:
  - execution_verifier.py の全エラーパスが `success=True` を返していた
  - APIキー未設定、スクリーンショット未取得、API呼び出し失敗、すべてのケースで「成功」と判定
  - dry-run でも `success=True` が返り、フィードバックに「成功」として記録されていた
  - 結果として再現性スコアが不正に高く算出されていた（ランクB→A昇格）
  - OpenAI API は実際には一度も正常に呼ばれていなかった（両アカウントの Usage が $0）
- **解決方法**:
  - `verified` フラグを導入: AI検証が実行されたかどうかを明示的に返す
  - `verified=False` の場合: `success=False, confidence=0.0` を返す（嘘をつかない）
  - autonomous_loop.py: `verified=True` の場合のみAI判定で成否を上書き、`False` ならアクション結果を維持
  - dry-run 実行はフィードバックに記録しない
  - APIキー事前チェック: `os.environ.get("OPENAI_API_KEY")` が空なら即座に検証スキップ
  - 既存の偽フィードバック7件を `feedback/old/` に退避
- **影響ファイル**: execution_verifier.py, autonomous_loop.py
- **根本原因**: 「検証できない = 成功とみなす」という楽観的設計が、現実には「検証が動いていないのに成功データが蓄積される」問題を生んでいた

### Issue 13: Gemini JSON構造化出力で additionalProperties エラー

- **発見日**: 2026-02-17
- **状態**: 解決済み
- **問題**: Gemini API が `additionalProperties` フィールドを認識せず `400 INVALID_ARGUMENT` エラー
- **原因**: OpenAI 用 JSON Schema に含まれる `additionalProperties: false` が Gemini の `response_schema` では非サポート
- **解決方法**: `_clean_schema_for_gemini()` を追加し、`additionalProperties` を再帰的に除去してからスキーマを渡す
- **影響ファイル**: ai_client.py

### Issue 14: Gemini Vision レスポンスが ```json``` で囲まれてJSON解析失敗

- **発見日**: 2026-02-17
- **状態**: 解決済み
- **問題**: Gemini がフリーテキストで JSON を返す際、` ```json ... ``` ` のマークダウンブロックで囲むため `json.loads()` が失敗
- **解決方法**: `_strip_markdown_json()` を追加し、パース前にマークダウンブロックを除去（`verify_execution`, `check_goal_achieved`, `find_element_by_vision` の3メソッドに適用）
- **影響ファイル**: ai_client.py

### Issue 12: OpenAI APIキー無効で全AI機能停止

- **発見日**: 2026-02-17
- **状態**: 解決済み（Gemini プロバイダー追加で対応）
- **問題**:
  - OpenAI APIキーが無効（Usage $0、一度も正常呼び出しなし）
  - AI 機能（Vision検索、ワークフロー分析、自律実行）が全て停止
  - OpenAI の有料プランが必要で即座に復旧困難
- **解決方法**:
  - AIClient にマルチプロバイダー対応を追加（Gemini + OpenAI）
  - デフォルトプロバイダーを Gemini（gemini-2.5-flash）に変更
  - AgentConfig にプロバイダー自動判定ロジック追加（GEMINI_API_KEY 優先）
  - action_player.py の Vision fallback を provider 対応に修正
  - Google AI Studio で無料 API キーを即時取得可能
- **影響ファイル**: ai_client.py, config.py, action_player.py, .env

### Issue 11: 座標フォールバックによるクリック位置のずれ

- **発見日**: 2026-02-17
- **状態**: 解決済み（コード実装完了、APIキー設定後にVision動作確認要）
- **問題**:
  - 学習時の座標 (945, 531) がそのまま再生時に使用される
  - ウィンドウ位置・サイズが異なると全く違う場所をクリックする
  - identifier=null, role=null のワークフローでは座標フォールバックしか使えない
  - 実際の Finder ゴミ箱ワークフローで再現を確認
- **解決方法**:
  - `find_element_by_criteria()` にアプリ全体検索（ステップ6）を追加: ウィンドウ位置が変わっても identifier/value/description/title+role でアプリ内全要素から検索
  - `_find_element_with_vision_fallback()` を AIClient.find_element_by_vision() に接続: APIキー未設定時は None を返し既存動作に影響なし
  - `play_action_step()` をリライト: coordinate_fallback 検出時に Vision フォールバックを試行してからクリック（1回だけ）
  - 要素検索優先順位（修正後）: identifier → value → description → title+role → role → アプリ全体検索 → coordinate_fallback → Vision推定
- **影響ファイル**: action_player.py, ai_client.py
