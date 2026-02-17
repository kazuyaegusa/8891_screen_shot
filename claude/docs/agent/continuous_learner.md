# continuous_learner.py

常時ワークフロー学習モジュール。キャプチャJSONを定期的にポーリングし、増分でワークフロー抽出・改善を行うdaemon。

## インプット

### `ContinuousLearner.__init__(config: AgentConfig)`
- `config: AgentConfig` - エージェント設定（json_dir, batch_size等を含む）

### `ContinuousLearner.run()`
- 引数なし
- 常時学習ループを開始（30秒ポーリング）。Ctrl+Cで停止

### `ContinuousLearner.run_once()`
- 引数なし
- 1サイクルのみ実行

### `ContinuousLearner.stop()`
- 引数なし
- 学習ループを停止

## アウトプット

### `run()` → None
- 戻り値なし。バックグラウンドで継続実行

### `run_once()` → int
- 新規抽出されたワークフロー数を返却

### `stop()` → None
- 戻り値なし。ループ停止

## 関数一覧

| 関数 | 説明 |
|------|------|
| `ContinuousLearner.__init__(config)` | 設定からExtractor/Refiner/FeedbackStoreを初期化 |
| `ContinuousLearner.run()` | 常時学習ループ（30秒ポーリング、Ctrl+Cで停止） |
| `ContinuousLearner.run_once()` | 1サイクル実行、新規ワークフロー数を返却 |
| `ContinuousLearner.stop()` | 学習停止 |

## 設定

| パラメータ | デフォルト値 | 説明 |
|-----------|------------|------|
| `poll_interval` | 30秒 | ポーリング間隔 |
| `batch_size` | 5 | 1回の処理バッチサイズ |
| `refine_interval` | 10サイクル | WorkflowRefiner実行間隔 |
| `report_interval` | 86400秒（24時間） | レポート自動更新間隔 |

## 日次レポート自動更新

`watch` daemon 実行中、`report_interval`（デフォルト24時間）ごとに以下を自動実行:

1. `ReportGenerator.generate()` で Markdown レポート生成
2. `workflows/reports/report_YYYYMMDD.md` に保存
3. `workflows/parts/catalog.json` を更新

初回は daemon 起動直後に即座に生成。以降は24時間ごと。

## 依存

- `agent.config.AgentConfig`
- `agent.models`
- `agent.workflow_extractor.WorkflowExtractor`
- `agent.workflow_refiner.WorkflowRefiner`
- `agent.feedback_store.FeedbackStore`
- `agent.report_generator.ReportGenerator`
