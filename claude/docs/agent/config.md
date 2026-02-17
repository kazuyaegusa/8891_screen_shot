# config.py ドキュメント

対応ソース: `claude/src/agent/config.py`

## 概要

エージェントシステムの設定を管理する。`.env` ファイルから環境変数をロードし、AIプロバイダー・実行制限・安全機構などの設定を提供する。
Gemini と OpenAI のマルチプロバイダーに対応し、利用可能なAPIキーから自動でプロバイダーを選択する。

## クラス

### `AgentConfig`

#### コンストラクタ

```python
AgentConfig(
    ai_provider="",          # "gemini" or "openai"（自動判定）
    gemini_api_key="",       # GEMINI_API_KEY 環境変数から自動取得
    gemini_model="gemini-2.5-flash",
    openai_api_key="",       # OPENAI_API_KEY 環境変数から自動取得
    openai_model="gpt-5",
    workflow_dir="",         # ワークフロー保存先（自動設定）
    max_steps=50,            # 最大ステップ数
    max_consecutive_failures=5,
    step_delay=1.0,
    dry_run=False,
    confirm_dangerous=True,
    dangerous_apps=[...],    # 送信系アプリリスト
    reasoning_effort="medium",
    max_output_tokens=2000,
    screenshot_dir="",
)
```

#### フィールド

| フィールド | 型 | デフォルト | 説明 |
|-----------|------|---------|------|
| `ai_provider` | str | `""` | AIプロバイダー（"gemini"/"openai"、空文字で自動判定） |
| `gemini_api_key` | str | `""` | Gemini APIキー（`GEMINI_API_KEY` 環境変数から自動取得） |
| `gemini_model` | str | `"gemini-2.5-flash"` | Gemini モデル名 |
| `openai_api_key` | str | `""` | OpenAI APIキー（`OPENAI_API_KEY` 環境変数から自動取得） |
| `openai_model` | str | `"gpt-5"` | OpenAI モデル名 |
| `workflow_dir` | str | `""` | ワークフロー保存先（自動設定） |
| `max_steps` | int | `50` | 自律実行の最大ステップ数 |
| `max_consecutive_failures` | int | `5` | 連続失敗上限 |
| `step_delay` | float | `1.0` | ステップ間の待機秒数 |
| `dry_run` | bool | `False` | ドライランモード |
| `confirm_dangerous` | bool | `True` | 危険アプリ操作時の確認 |
| `dangerous_apps` | List[str] | Mail, Slack等 | 危険アプリリスト |
| `reasoning_effort` | str | `"medium"` | AI推論の労力レベル |
| `max_output_tokens` | int | `2000` | AI出力の最大トークン数 |
| `screenshot_dir` | str | `""` | スクリーンショット保存先（自動設定） |

#### プロバイダー自動判定ロジック

`ai_provider` が未指定（空文字）の場合、以下の優先順位で自動判定:

1. `AI_PROVIDER` 環境変数が設定されていればそれを使用
2. `GEMINI_API_KEY` があれば `"gemini"`
3. `OPENAI_API_KEY` があれば `"openai"`
4. どちらもなければ `"gemini"`（デフォルト）

#### メソッド

##### `is_dangerous_app(app_name: str) -> bool`

送信系アプリかどうかを判定する。

| 項目 | 内容 |
|------|------|
| **入力** | `app_name`: アプリ名 |
| **出力** | `True`（危険アプリ）/ `False` |

## 環境変数

| 変数名 | 説明 |
|--------|------|
| `AI_PROVIDER` | AIプロバイダーの明示指定（"gemini" or "openai"） |
| `GEMINI_API_KEY` | Gemini APIキー（Google AI Studio で取得） |
| `OPENAI_API_KEY` | OpenAI APIキー |

## 依存ライブラリ

- python-dotenv
- os, dataclasses, pathlib
