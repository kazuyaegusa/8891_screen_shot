# report_generator.py API仕様

## 概要

再現性レポート生成 + 業務パーツカタログ管理モジュール。
各ワークフローの再現性をA/B/Cランクで評価し、業務カテゴリに分類してレポート・カタログを出力する。
AI呼び出し不要。ローカルで即時実行。

## インポート

```python
from agent.report_generator import ReportGenerator
from agent.workflow_store import WorkflowStore
from agent.feedback_store import FeedbackStore
```

## クラス: ReportGenerator

### コンストラクタ

```python
ReportGenerator(store: WorkflowStore, feedback: FeedbackStore)
```

| 引数 | 型 | 説明 |
|------|------|------|
| store | WorkflowStore | ワークフロー永続化ストア |
| feedback | FeedbackStore | 実行フィードバックストア |

### メソッド

#### generate(format, category) -> str

レポートを生成する。catalog.json も同時に更新。

| 引数 | 型 | デフォルト | 説明 |
|------|------|-----------|------|
| format | str | "markdown" | 出力形式（"markdown" or "json"） |
| category | Optional[str] | None | カテゴリフィルタ（Noneで全カテゴリ） |

**返却**: Markdown文字列 または JSON文字列

#### update_catalog() -> str

catalog.json を更新する。

**返却**: catalog.json の保存パス

#### get_by_category(category) -> List[Workflow]

指定カテゴリのワークフローを取得する。

| 引数 | 型 | 説明 |
|------|------|------|
| category | str | カテゴリ名（"開発", "ブラウザ/Web" 等） |

**返却**: Workflow のリスト

## 再現性評価ロジック

### スコア計算

```
score = confidence × 0.30
      + success_rate × 0.30   （実行データなし = 0.15）
      + step_quality × 0.25
      + ax_compatibility × 0.15
```

### ランク判定

| ランク | 条件 | 意味 |
|--------|------|------|
| A | score >= 0.7 | 再現可能 |
| B | score >= 0.4 | 要検証 |
| C | score < 0.4 | 再現困難 |

### ステップ品質スコア

| アクション種別 | ベーススコア | 補正 |
|-------------|-----------|------|
| key_shortcut | 0.95 | - |
| text_input | 0.80 | - |
| click | 可変 | identifier有=0.90, role+title=0.70, 座標のみ=0.30 |

### アプリAX対応度

主要アプリの対応度テーブル（_AX_COMPATIBILITY）で判定。未知アプリはステップのtarget情報充実度から推定。

## 業務カテゴリ分類

| カテゴリ | 対象アプリ |
|---------|-----------|
| 開発 | Cursor, Code, Ghostty, Terminal, iTerm2, Xcode |
| コミュニケーション | LINE, Discord, Slack, Mail, Messages, Zoom, Teams |
| ブラウザ/Web | Google Chrome, Safari, Firefox, Arc |
| AI/LLM | Claude, Google Gemini, ChatGPT |
| システム操作 | Finder, System Preferences, System Settings |
| プロジェクト管理 | Linear, Notion, Jira, Asana, Trello |
| その他 | 上記に該当しないアプリ |

分類ロジック: app_name → tags の順でマッチ。該当なしは「その他」。

## 出力ファイル

### catalog.json（パーツインデックス）

保存先: `workflows/parts/catalog.json`

```json
{
  "updated_at": "2026-02-17T15:00:00",
  "categories": {
    "開発": {
      "workflows": [
        {
          "workflow_id": "wf-xxx",
          "name": "...",
          "app_name": "Cursor",
          "reproducibility": {"score": 0.78, "rank": "A"},
          "steps_count": 11
        }
      ]
    }
  },
  "stats": {"total": 31, "by_rank": {"A": 8, "B": 15, "C": 8}}
}
```

### レポート（Markdown）

保存先: `workflows/reports/report_YYYYMMDD.md`（CLI経由で --output 指定時）

## CLI使用例

```bash
python3 -m agent.agent_cli report                    # 全カテゴリのレポート表示
python3 -m agent.agent_cli report --category "開発"   # カテゴリフィルタ
python3 -m agent.agent_cli report --format json      # JSON出力
python3 -m agent.agent_cli report --output report.md # ファイル保存
```
