# config.py ドキュメント

対応ソース: `claude/src/pipeline/config.py`

## 概要

パイプラインの設定管理モジュール。`.env` ファイルおよび環境変数からパイプライン設定値をロードし、`PipelineConfig` dataclass として提供する。

## データクラス

### `PipelineConfig`

| フィールド | 型 | デフォルト値 | 環境変数 | 説明 |
|---|---|---|---|---|
| `watch_dir` | `Path` | `./screenshots` | `PIPELINE_WATCH_DIR` | キャプチャJSONファイルの監視ディレクトリ |
| `skills_dir` | `Path` | `~/.claude/skills` | `PIPELINE_SKILLS_DIR` | スキル出力先ディレクトリ |
| `session_gap` | `int` | `300` | `PIPELINE_SESSION_GAP` | セッション区切りの時間間隔（秒） |
| `session_max` | `int` | `50` | `PIPELINE_SESSION_MAX` | 1セッションの最大レコード数 |
| `ai_provider` | `str` | `"openai"` | `PIPELINE_AI_PROVIDER` | AI プロバイダ名 |
| `ai_model` | `str` | `"gpt-5"` | `PIPELINE_AI_MODEL` | 使用するAIモデル名 |
| `cpu_limit` | `int` | `30` | `PIPELINE_CPU_LIMIT` | CPU使用率の上限（%） |
| `mem_limit` | `int` | `500` | `PIPELINE_MEM_LIMIT` | メモリ使用量の上限（MB） |
| `poll_sec` | `float` | `10.0` | `PIPELINE_POLL_SEC` | ファイル監視のポーリング間隔（秒） |
| `min_confidence` | `float` | `0.6` | `PIPELINE_MIN_CONFIDENCE` | スキル抽出の最小信頼度閾値 |

## メソッド

### `PipelineConfig.from_env() -> PipelineConfig`（クラスメソッド）

`.env` ファイルと環境変数から設定を読み込み、`PipelineConfig` インスタンスを生成する。

| 項目 | 内容 |
|------|------|
| **入力** | なし（`.env` ファイルおよび環境変数から自動読み込み） |
| **出力** | `PipelineConfig` インスタンス |

- `python-dotenv` の `load_dotenv()` で `.env` を自動読み込み
- 環境変数が未設定の場合はデフォルト値を使用
- 型変換は自動（`int()`, `float()`, `Path()`）

## 使用例

```python
# .env + 環境変数からロード
config = PipelineConfig.from_env()

# デフォルト値で生成
config = PipelineConfig()

# 個別指定
config = PipelineConfig(session_gap=600, ai_model="gpt-5")
```

## 依存ライブラリ

- python-dotenv
- Python標準ライブラリ (os, dataclasses, pathlib)
