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
