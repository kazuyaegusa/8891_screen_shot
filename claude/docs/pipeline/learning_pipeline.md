# learning_pipeline.py ドキュメント

対応ソース: `claude/src/pipeline/learning_pipeline.py`

## 概要

常時学習パイプラインのメインオーケストレータ。
capture_loop.py が生成するキャプチャデータ（JSON + PNG）をバックグラウンドで処理し、操作パターンをスキルとして `~/.claude/skills/` に自動保存する。
CLI エントリポイントも提供する。

## クラス

### `LearningPipeline`

#### コンストラクタ

```python
LearningPipeline(config: PipelineConfig)
```

| 項目 | 内容 |
|------|------|
| **入力** | `config`: PipelineConfig オブジェクト（環境変数 or CLI引数から生成） |

内部で以下のコンポーネントを初期化:
- `ResourceGuard` — CPU/メモリ制限
- `FileWatcher` — ファイル監視
- `SessionBuilder` — セッション構築
- `AIClient` — AI API呼び出し
- `PatternExtractor` — パターン抽出
- `SkillWriter` — スキル書き出し
- `CleanupManager` — ファイル削除

#### `run() -> None`

パイプラインを常時実行する。

| 項目 | 内容 |
|------|------|
| **入力** | なし |
| **出力** | なし（`stop()` が呼ばれるまでループ） |

処理ループ:
1. `ResourceGuard.setup_low_priority()` で低優先度に設定
2. `_process_cycle()` を実行
3. `poll_sec` 秒待機
4. `_running` が False になるまで繰り返し

#### `run_once() -> None`

パイプラインを1サイクルだけ実行する（テスト用）。

| 項目 | 内容 |
|------|------|
| **入力** | なし |
| **出力** | なし |

- `_process_cycle()` を1回実行
- `SessionBuilder.flush()` でバッファ残りも処理

#### `stop() -> None`

パイプラインを停止する。

| 項目 | 内容 |
|------|------|
| **入力** | なし |
| **出力** | なし |

- `_running` を False に設定し、次のループで停止

### 内部メソッド

#### `_process_cycle() -> None`

1回分の処理サイクル。

1. `ResourceGuard.check_and_throttle()` でリソースチェック
2. `FileWatcher.scan_new_files()` で新規ファイルをスキャン
3. 各ファイルに対して:
   - `FileWatcher.load_record()` でレコード読み込み
   - `SessionBuilder.add_record()` でセッション構築
   - セッションが完成したら `_process_session()` を実行
   - `FileWatcher.mark_processed()` で処理済みマーク

#### `_process_session(session: Session) -> None`

セッションからスキル抽出・書き出し・クリーンアップを実行。

1. `PatternExtractor.extract()` でスキル抽出
2. スキルが存在すれば `SkillWriter.update_skill()`、なければ `write_skill()`
3. `CleanupManager.cleanup_session()` で処理済みファイル削除

## CLI 関数

### `main() -> None`

CLI エントリポイント。`python -m pipeline.learning_pipeline` で実行。

#### CLI引数

| 引数 | 型 | 説明 |
|------|------|------|
| `--watch-dir` | str | 監視ディレクトリ |
| `--provider` | str | AIプロバイダ（例: openai） |
| `--model` | str | AIモデル名（例: gpt-5） |
| `--once` | flag | 1回だけ実行して終了 |

- 引数が省略された場合は `PipelineConfig.from_env()` のデフォルト値を使用
- SIGINT / SIGTERM で `pipeline.stop()` を呼び出してグレースフル停止

## CLI 使用方法

```bash
# デフォルト起動（.env設定を使用）
cd claude/src && python -m pipeline.learning_pipeline

# 1回だけ実行（テスト用）
python -m pipeline.learning_pipeline --once

# カスタム設定
python -m pipeline.learning_pipeline --watch-dir ./screenshots --provider openai --model gpt-5
```

## 依存ライブラリ

- pipeline 全モジュール (ai_client, cleanup_manager, config, file_watcher, models, pattern_extractor, resource_guard, session_builder, skill_writer)
- Python標準ライブラリ (argparse, signal, time, logging)
