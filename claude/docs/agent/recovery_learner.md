# recovery_learner.py

エラー復旧パターン学習モジュール。kework-agi RecoveryLearner準拠。実行履歴からエラー→復旧アクションのマッピングを学習し、信頼度の高いパターンのみ提案する。

## インプット

### `RecoveryLearner.__init__(patterns_path: str)`
- `patterns_path: str` - パターン永続化ファイルパス（例: `./workflows/recovery_patterns.json`）

### `RecoveryLearner.record_recovery(error_code, app_name, failed_action, recovery_action, success)`
- `error_code: str` - エラーコード（例: `HINT_NOT_FOUND`, `TIMEOUT`, `INPUT_FAILED`）
- `app_name: str` - アプリケーション名
- `failed_action: str` - 失敗したアクション種別
- `recovery_action: str` - 実行した復旧アクション
- `success: bool` - 復旧が成功したか

### `RecoveryLearner.get_learned_recovery(error_code, app_name="", failed_action="")`
- `error_code: str` - エラーコード
- `app_name: str` - アプリケーション名（省略可）
- `failed_action: str` - 失敗したアクション種別（省略可）

### `RecoveryLearner.get_reliable_patterns()`
- 引数なし

## アウトプット

### `record_recovery(...)` → None
- パターンを記録し `recovery_patterns.json` に永続化

### `get_learned_recovery(...)` → Optional[Dict]
- 学習済みパターンを段階的フォールバックで検索

```python
# フォールバック順序:
# 1. (error_code, app_name, failed_action) 完全一致
# 2. (error_code, "", failed_action) アプリ問わず
# 3. (error_code, "", "") エラーコードのみ

# 返却値:
{
    "error_code": str,
    "app_name": str,
    "failed_action": str,
    "recovery_action": str,
    "sample_count": int,
    "success_count": int,
    "success_rate": float,
}
```

### `get_reliable_patterns()` → List[Dict]
- 閾値を満たす信頼度の高いパターン一覧（成功率降順）

## 閾値設定

| パラメータ | 値 | 説明 |
|-----------|---|------|
| `MIN_SAMPLES_FOR_SUGGESTION` | 3 | パターン提案に必要な最低サンプル数 |
| `MIN_SUCCESS_RATE_FOR_SUGGESTION` | 0.6 | パターン提案に必要な最低成功率 |

## ストレージ

- 保存先: `workflows/recovery_patterns.json`
- 形式: JSONリスト（各要素がパターン辞書）

## 関数一覧

| 関数 | 説明 |
|------|------|
| `RecoveryLearner.__init__(patterns_path)` | パターンファイルを読み込み初期化 |
| `RecoveryLearner.record_recovery(...)` | 復旧結果を記録・永続化 |
| `RecoveryLearner.get_learned_recovery(...)` | 学習済みパターンをフォールバック検索 |
| `RecoveryLearner.get_reliable_patterns()` | 信頼度の高いパターン一覧を返却 |

## 依存

- Python標準ライブラリのみ（json, logging, pathlib, typing）
