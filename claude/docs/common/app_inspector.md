# app_inspector.py ドキュメント

対応ソース: `claude/src/common/app_inspector.py`

## 概要

macOS Accessibility APIを使って、マウス座標位置にあるUI要素のアプリケーション情報を取得する共通モジュール。
ブラウザのURL/タイトル情報取得にも対応。

## クラス: AppInspector

### コンストラクタ

```python
inspector = AppInspector()
```

- Quartz/AppKitが利用できない場合はRuntimeErrorを送出

### メソッド

#### `get_frontmost_app() -> Dict[str, Any]`

最前面のアプリケーション情報を取得する。

- **入力**: なし
- **出力**:
  ```python
  {"name": "Safari", "bundle_id": "com.apple.Safari", "pid": 1234}
  ```
  エラー時: `{"name": "Unknown", "bundle_id": "", "pid": 0, "error": "..."}`

#### `get_element_at_position(x: float, y: float) -> Dict[str, Any]`

指定座標のUI要素情報を取得する。拡張AX属性を含む。

- **入力**:
  - `x`: 画面X座標
  - `y`: 画面Y座標
- **出力**:
  ```python
  {
      "role": "AXButton",
      "title": "OK",
      "description": "OKボタン",
      "identifier": "ok-button",
      "value": "入力テキスト（最大2000文字）",
      "frame": {"x": 100, "y": 200, "width": 80, "height": 30},
      "document_url": "https://example.com",
      "help": "ヘルプテキスト",
      "role_description": "ボタン",
      "focused": true,
      "enabled": true,
      "placeholder": "検索..."
  }
  ```
  エラー時: `{"error": "No element found at (x, y)", "code": ...}`

| 属性 | AX属性名 | 説明 |
|------|----------|------|
| `role` | AXRole | 要素のロール（AXButton等） |
| `title` | AXTitle | 要素のタイトル |
| `description` | AXDescription | 要素の説明 |
| `identifier` | AXIdentifier | 要素の識別子 |
| `value` | AXValue | 入力テキスト等の値（最大2000文字） |
| `document_url` | AXDocument | ブラウザのURL |
| `help` | AXHelp | ヘルプテキスト |
| `role_description` | AXRoleDescription | 要素のロール説明（日本語: "テキストフィールド"等） |
| `focused` | AXFocused | フォーカス状態 |
| `enabled` | AXEnabled | 有効/無効状態 |
| `placeholder` | AXPlaceholderValue | プレースホルダーテキスト |

#### `get_full_info(x: float, y: float) -> Dict[str, Any]`

アプリ情報+UI要素情報をまとめて取得する。

- **入力**: `x`, `y` 座標
- **出力**:
  ```python
  {
      "app": {"name": "...", "bundle_id": "...", "pid": 1234},
      "element": {"role": "...", ...},
      "coordinates": {"x": x, "y": y}
  }
  ```

#### `get_browser_info(pid: int) -> Dict[str, Any]`

指定PIDのアプリがブラウザの場合、URL・タイトル情報を取得する。

- **入力**: `pid` — プロセスID
- **出力**:
  ```python
  {
      "is_browser": true,
      "url": "https://example.com/page",
      "page_title": "Example Page"
  }
  ```
  ブラウザでない場合: `{"is_browser": false, "url": null, "page_title": null}`

- **ブラウザ判定**: bundle_idに以下のキーワードが含まれるかで判定
  - `safari`, `chrome`, `firefox`, `edge`, `arc`, `brave`

## 依存ライブラリ

- `pyobjc-framework-ApplicationServices`
- `pyobjc-framework-Cocoa`
