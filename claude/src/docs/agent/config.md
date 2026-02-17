# config.py

## 概要
エージェント設定を.envファイルからロードする設定管理モジュール

## 主要クラス

### AgentConfig
設定値を保持するクラス。.envから自動ロード。

- 入力フィールド:
  - openai_api_key: str - OpenAI APIキー
  - workflow_dir: str - ワークフロー保存ディレクトリパス
  - max_steps: int - 最大実行ステップ数
  - dangerous_apps: List[str] - 送信系アプリ一覧 (Mail, Slack 等)
- 出力: なし（データ保持用）

## 主要関数

### is_dangerous_app(app_name)
- 入力: app_name: str - アプリケーション名
- 出力: bool - 送信系アプリの場合True
- 説明: メール・チャット等の送信操作が危険なアプリかどうかを判定する

## 依存
- os (標準ライブラリ)
- dotenv

## 使用例
```python
from config import AgentConfig

config = AgentConfig()
print(config.openai_api_key)
print(config.workflow_dir)

if config.is_dangerous_app("Mail"):
    print("送信系アプリです。確認が必要です。")
```
