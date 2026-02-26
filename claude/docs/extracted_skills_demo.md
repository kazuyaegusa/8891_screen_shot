# extracted_skills_demo.json

## 概要
Anthropic API（Claude Sonnet）を使って、キャプチャデータから業務スキルを自動抽出した結果ファイル。

## インプット
- `screenshots/*_cap_*.json` — セッション `7be892b8` のSlack操作55件 + Chrome(Cost)操作5件

## アウトプット
- `extracted_skills_demo.json` — 抽出された2つの業務スキル（JSON）

## 関数/処理の説明
直接的なPythonモジュールではなく、`pipeline/ai_client.py` の `AIClient` + Anthropic API を使ったワンショット抽出の結果。

## スキル一覧
| skill_id | name | automation_potential |
|---|---|---|
| skill-001 | Slackでのメンション付きメッセージ作成・編集 | medium |
| skill-002 | Claude API コスト確認 | high |
