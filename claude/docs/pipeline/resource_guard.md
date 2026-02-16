# resource_guard.py ドキュメント

対応ソース: `claude/src/pipeline/resource_guard.py`

## 概要

リソース監視・スロットリングモジュール。パイプライン処理がシステムリソースを占有しないよう、CPU使用率・メモリ使用量を監視し、閾値超過時に自動的にスリープで負荷を抑制する。

## クラス

### `ResourceGuard`

#### コンストラクタ

```python
ResourceGuard(cpu_limit: int = 30, mem_limit_mb: int = 500)
```

| 引数 | 型 | デフォルト | 説明 |
|---|---|---|---|
| `cpu_limit` | `int` | `30` | CPU使用率の上限（%） |
| `mem_limit_mb` | `int` | `500` | メモリ使用量の上限（MB） |

## メソッド

### `setup_low_priority() -> None`

プロセス優先度を最低に設定する。

| 項目 | 内容 |
|------|------|
| **入力** | なし |
| **出力** | `None` |

- `os.nice(19)` で最低優先度に設定
- 権限不足（`PermissionError`）やOS制約（`OSError`）の場合はwarningログを出力し、通常優先度で継続

### `check_and_throttle() -> None`

現在のCPU使用率・メモリ使用量を確認し、閾値超過時に適応的スリープを実行する。

| 項目 | 内容 |
|------|------|
| **入力** | なし |
| **出力** | `None`（閾値超過時は内部で `time.sleep` を実行） |

- CPU超過時のスリープ時間: `min((cpu - cpu_limit) / cpu_limit * 2, 5.0)` 秒
- メモリ超過時のスリープ時間: `min((mem - mem_limit) / mem_limit * 2, 5.0)` 秒
- 最大スリープ時間は5.0秒

### `get_stats() -> Dict`

現在のリソース使用状況を取得する。

| 項目 | 内容 |
|------|------|
| **入力** | なし |
| **出力** | リソース情報Dict |

出力例:

```json
{
  "cpu_percent": 15.2,
  "memory_mb": 120.5,
  "disk_usage_mb": 450.3
}
```

| キー | 型 | 説明 |
|---|---|---|
| `cpu_percent` | `float` | 現在のCPU使用率（%） |
| `memory_mb` | `float` | 現在のプロセスメモリ使用量（MB、小数点1桁） |
| `disk_usage_mb` | `float` | 監視ディレクトリのディスク使用量（MB、小数点1桁） |

## 依存ライブラリ

- psutil
- Python標準ライブラリ (os, time, logging, pathlib)
