# image_analyzer.py - OpenAI Vision画像解析モジュール

対応ソース: `claude/src/daemon/image_analyzer.py`

## 概要

スクリーンショット画像をbase64エンコードし、OpenAI GPT-5 Vision APIに送信。画面内容を日本語で解説する。

## クラス

### `ImageAnalyzer`

#### `__init__(self, api_key: str, model: str = "gpt-5")`
**インプット:**
| パラメータ | 型 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `api_key` | `str` | - | OpenAI APIキー |
| `model` | `str` | `"gpt-5"` | 使用するモデル名 |

#### `analyze(self, image_path: Path) -> dict`
画像ファイルを解析し、画面内容の説明を返す。

**インプット:**
| パラメータ | 型 | 説明 |
|-----------|------|------|
| `image_path` | `Path` | 解析対象の画像ファイルパス |

**アウトプット:** `dict`
```json
{
  "timestamp": "2026-02-14 15:30:45",
  "filename": "screenshot_20260214_153045_123456.png",
  "description": "画面にはVSCodeが表示されており...",
  "model": "gpt-5"
}
```

**例外:**
- `FileNotFoundError`: 画像ファイルが存在しない場合
- `Exception`: API呼び出し失敗時

**備考:**
- `client.responses.create`パターンを使用（100_IMPORT/OPENAIGPT5.md準拠）
- `max_output_tokens=800`
- 画像はbase64でdata URLとして送信
