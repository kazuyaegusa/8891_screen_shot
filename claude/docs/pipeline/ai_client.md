# ai_client.py ドキュメント

対応ソース: `claude/src/pipeline/ai_client.py`

## 概要

セッション分析・スキル抽出・ワークフロー分析・アクション選択・実行検証・目標判定・要素検出を行うマルチプロバイダー対応AIクライアントモジュール。
Gemini（Google AI）と OpenAI をサポートし、環境変数で切り替え可能。デフォルトは Gemini（gemini-2.5-flash）。

## プロバイダー

| プロバイダー | モデル | 環境変数 | 備考 |
|-------------|--------|---------|------|
| `gemini`（デフォルト） | gemini-2.5-flash | `GEMINI_API_KEY` | 無料枠あり、Vision対応 |
| `openai` | gpt-5 | `OPENAI_API_KEY` | 従来のプロバイダー |

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

### `_WORKFLOW_SCHEMA`

ワークフロー分析時に使用する JSON Schema 定義。

### `_ACTION_SELECTION_SCHEMA`

アクション選択時に使用する JSON Schema 定義。

## クラス

### `AIClient`

#### コンストラクタ

```python
AIClient(provider: str = "gemini", model: str = None)
```

| 項目 | 内容 |
|------|------|
| **入力** | `provider`: AIプロバイダ名（"gemini" or "openai"）, `model`: モデル名（未指定時はプロバイダーのデフォルト） |
| **例外** | `NotImplementedError`: provider が "gemini"/"openai" 以外の場合 |

#### 内部ヘルパー（プロバイダー抽象化）

| メソッド | 説明 |
|---------|------|
| `_generate_text(prompt, effort, max_tokens)` | テキスト生成（プロバイダー自動分岐） |
| `_generate_json(prompt, schema, effort, max_tokens)` | JSON構造化出力（プロバイダー自動分岐） |
| `_generate_vision(prompt, image_paths, effort)` | Vision画像入力（プロバイダー自動分岐） |

#### `analyze_session(session: Session) -> Dict`

セッション内の操作列を要約・分析する。

| 項目 | 内容 |
|------|------|
| **入力** | `session`: Session オブジェクト（操作レコード群） |
| **出力** | `{"summary": str, "session_id": str}` （成功時）または `{"error": str, "session_id": str}` （失敗時） |

#### `extract_skill(session: Session) -> Optional[ExtractedSkill]`

セッションから繰り返し操作パターンをスキルとして抽出する。

| 項目 | 内容 |
|------|------|
| **入力** | `session`: Session オブジェクト |
| **出力** | `ExtractedSkill`（抽出成功時）または `None`（スキルなし/失敗時） |

#### `analyze_workflow_segment(actions_text, app_name) -> Optional[Dict]`

ワークフローセグメントを分析し、名前・説明・パラメータ化・confidenceを返す。

#### `select_next_action(goal, current_state, available_actions, history) -> Optional[Dict]`

目標と現在の状態から次のアクションを選択する。

#### `verify_execution(before_screenshot, after_screenshot, expected_change) -> Dict`

実行前後のスクリーンショットをVisionで比較し、成功/失敗を判定する。

#### `check_goal_achieved(goal, current_state, history) -> Dict`

目標が達成されたか判定する。

#### `find_element_by_vision(screenshot_path, element_description) -> Optional[Dict]`

スクリーンショットからVisionで要素の座標を推定する。

## 内部関数

### `_encode_image(path: str) -> str`

画像ファイルをbase64エンコードして返す（OpenAI用）。

### `_build_analysis_prompt(session: Session) -> str`

セッション分析用プロンプトを生成する。

### `_build_extraction_prompt(session: Session) -> str`

スキル抽出用プロンプトを生成する。

## 依存ライブラリ

- google-genai（Gemini プロバイダー）
- openai（OpenAI プロバイダー）
- pipeline.models (Session, ExtractedSkill)
- 環境変数: `GEMINI_API_KEY`（Gemini使用時）または `OPENAI_API_KEY`（OpenAI使用時）
