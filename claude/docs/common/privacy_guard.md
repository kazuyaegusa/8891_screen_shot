# privacy_guard.py ドキュメント

対応ソース: `claude/src/common/privacy_guard.py`

## 概要

パスワード・機密情報（APIキー、クレジットカード番号、URLトークン等）がキャプチャデータに平文記録されるのを防ぐプライバシー保護フィルタモジュール。
`capture_loop.py`、`window_screenshot.py`、`event_monitor.py`、`json_saver.py`、`app_inspector.py` から横断的に利用される疎結合ユーティリティ。

## Enum: PrivacyLevel

プライバシー保護の強度を3段階で制御する。

| レベル | 値 | 動作 |
|--------|------|------|
| `STANDARD` | `"standard"` | パスワードフィールド（AXSecureTextField）のみフィルタ。テキスト内の機密パターンも除去 |
| `STRICT` | `"strict"` | 全テキスト入力をマスク。URLの全パラメータをマスク。AXValueを常にマスク |
| `OFF` | `"off"` | フィルタなし（全データをそのまま記録） |

## クラス: PrivacyGuard

### コンストラクタ

```python
guard = PrivacyGuard(level=PrivacyLevel.STANDARD)
```

| 引数 | 型 | デフォルト | 説明 |
|------|------|-----------|------|
| `level` | `PrivacyLevel` | `STANDARD` | プライバシー保護レベル |

### メソッド

#### `is_secure_field(role, role_description=None) -> bool`

対象フィールドがパスワード等のセキュアフィールドかを判定する。

| 項目 | 内容 |
|------|------|
| **入力** | `role`: Accessibility API の role 文字列（例: `"AXSecureTextField"`, `"AXTextField"`） |
| | `role_description`: Accessibility API の role_description 文字列（オプション） |
| **出力** | `bool` - セキュアフィールドなら `True` |

判定条件:
- `role == "AXSecureTextField"` → `True`
- `role_description` に `"password"`, `"パスワード"`, `"passwd"`, `"passcode"`, `"pin"` のいずれかを含む → `True`（大文字小文字不問）

#### `filter_text_input(text, is_secure) -> Optional[str]`

テキスト入力をフィルタリングする。`None` を返した場合は記録しない。

| 項目 | 内容 |
|------|------|
| **入力** | `text`: 入力テキスト文字列 |
| | `is_secure`: セキュアフィールドかどうか（`is_secure_field()` の結果） |
| **出力** | `Optional[str]` - フィルタ済みテキスト、または `None`（記録しない） |

動作:
| PrivacyLevel | is_secure=True | is_secure=False |
|-------------|----------------|-----------------|
| OFF | そのまま返す | そのまま返す |
| STRICT | `"[TEXT_INPUT]"` | `"[TEXT_INPUT]"` |
| STANDARD | `None`（記録しない） | 機密パターン除去して返す |

#### `sanitize_url(url) -> str`

URLから機密パラメータをマスクする。

| 項目 | 内容 |
|------|------|
| **入力** | `url`: URL文字列 |
| **出力** | `str` - マスク済みURL |

マスク対象パラメータ名（STANDARD モード）:
`token`, `access_token`, `api_key`, `apikey`, `api-key`, `password`, `passwd`, `secret`, `session`, `session_id`, `jwt`, `auth`, `authorization`, `key`, `private_key`, `client_secret`, `refresh_token`, `id_token`

- STRICT モード: 上記に加え、全パラメータの値をマスク
- OFF モード: そのまま返す

例:
```
入力: "https://example.com?token=abc123&page=1"
STANDARD: "https://example.com?token=[MASKED]&page=1"
STRICT:   "https://example.com?token=[MASKED]&page=[MASKED]"
OFF:      "https://example.com?token=abc123&page=1"
```

#### `mask_value(value, role, role_description=None) -> Optional[str]`

Accessibility API の AXValue をマスキングする。

| 項目 | 内容 |
|------|------|
| **入力** | `value`: AXValue の値（`None` 可） |
| | `role`: Accessibility API の role 文字列 |
| | `role_description`: Accessibility API の role_description 文字列（オプション） |
| **出力** | `Optional[str]` - マスク済み値、または `None` |

動作:
| PrivacyLevel | セキュアフィールド | 通常フィールド |
|-------------|-------------------|--------------|
| OFF | そのまま返す | そのまま返す |
| STRICT | `"[MASKED]"` | `"[MASKED]"` |
| STANDARD | `"[MASKED]"` | そのまま返す |

#### `should_skip_capture(role, focused, role_description=None) -> bool`

スクリーンショット撮影をスキップすべきかを判定する。

| 項目 | 内容 |
|------|------|
| **入力** | `role`: Accessibility API の role 文字列 |
| | `focused`: フィールドがフォーカスされているか |
| | `role_description`: Accessibility API の role_description 文字列（オプション） |
| **出力** | `bool` - スキップすべきなら `True` |

判定条件:
- OFF モード → 常に `False`
- `focused == True` かつ `is_secure_field()` が `True` → `True`（パスワード入力画面はスクショしない）

#### `redact_sensitive_patterns(text) -> str`

テキスト内の機密パターン（APIキー、カード番号等）を除去する。

| 項目 | 内容 |
|------|------|
| **入力** | `text`: テキスト文字列 |
| **出力** | `str` - 機密パターンを置換済みテキスト |

検出対象パターン:

| パターン | 置換先 | 例 |
|---------|--------|-----|
| クレジットカード番号（4桁x4） | `[CARD_NUMBER]` | `1234 5678 9012 3456` |
| OpenAI APIキー (`sk-...`) | `[API_KEY]` | `sk-abc123def456...` |
| GitHub トークン (`gh[ps]_...`) | `[API_KEY]` | `ghp_xxxxxxxxxxxx...` |
| Slack トークン (`xox[bpras]-...`) | `[API_KEY]` | `xoxb-xxx-xxx-xxx` |
| Google APIキー (`AIza...`) | `[API_KEY]` | `AIzaSyDxxxxxxxx...` |
| AWS アクセスキー (`AKIA...`) | `[API_KEY]` | `AKIAIOSFODNN7...` |
| Bearer トークン | `[BEARER_TOKEN]` | `Bearer eyJhbGci...` |

## 依存ライブラリ

- Python標準ライブラリのみ (re, enum, urllib.parse, typing)
