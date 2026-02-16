# ai_client.py ドキュメント

対応ソース: `claude/src/pipeline/ai_client.py`

## 概要

セッション分析・スキル抽出を行うプラガブルなAIクライアントモジュール。
OpenAI API（gpt-5）を使用し、操作ログからセッション要約とスキル抽出を行う。
JSON Schema による構造化出力で ExtractedSkill を生成する。

## 定数

### `_SKILL_SCHEMA`

スキル抽出時に使用する JSON Schema 定義。`strict: True` で厳密な型チェックを強制する。

| フィールド | 型 | 説明 |
|-----------|------|------|
| name | string | スキル名 |
| description | string | スキルの説明 |
| steps | array[string] | 手順リスト |
| app | string | 対象アプリ名 |
| triggers | array[string] | トリガーキーワード |
| confidence | number (0-1) | 抽出の確信度 |
| is_skill | boolean | スキルとして抽出可能か |

## クラス

### `AIClient`

#### コンストラクタ

```python
AIClient(provider: str = "openai", model: str = "gpt-5")
```

| 項目 | 内容 |
|------|------|
| **入力** | `provider`: AIプロバイダ名（現在 "openai" のみ対応）, `model`: モデル名 |
| **例外** | `NotImplementedError`: provider が "openai" 以外の場合 |

#### `analyze_session(session: Session) -> Dict`

セッション内の操作列を要約・分析する。

| 項目 | 内容 |
|------|------|
| **入力** | `session`: Session オブジェクト（操作レコード群） |
| **出力** | `{"summary": str, "session_id": str}` （成功時）または `{"error": str, "session_id": str}` （失敗時） |

- OpenAI Responses API を `reasoning.effort="low"` で呼び出す
- API 呼び出し失敗時はログ出力して error キー付き Dict を返す

#### `extract_skill(session: Session) -> Optional[ExtractedSkill]`

セッションから繰り返し操作パターンをスキルとして抽出する。

| 項目 | 内容 |
|------|------|
| **入力** | `session`: Session オブジェクト |
| **出力** | `ExtractedSkill`（抽出成功時）または `None`（スキルなし/失敗時） |

- JSON Schema (`_SKILL_SCHEMA`) による構造化出力で API を呼び出す
- レスポンスの `is_skill` が False の場合は `None` を返す
- API 呼び出し失敗時はログ出力して `None` を返す

## 内部関数

### `_build_analysis_prompt(session: Session) -> str`

セッション分析用プロンプトを生成する。アプリ名・期間・操作数・操作リストを含む。

### `_build_extraction_prompt(session: Session) -> str`

スキル抽出用プロンプトを生成する。操作リスト（タイムスタンプ、アクション種別、ボタン、ターゲット名、ウィンドウ名）と分析指示を含む。

## 依存ライブラリ

- openai
- pipeline.models (Session, ExtractedSkill)
- 環境変数: `OPENAI_API_KEY`
