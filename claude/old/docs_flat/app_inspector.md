# app_inspector.py ドキュメント

対応ソース: `claude/src/app_inspector.py`

## 概要

macOS Accessibility APIを使って、マウス座標位置にあるUI要素のアプリケーション情報を取得する共通モジュール。

## クラス: AppInspector

### コンストラクタ

```python
inspector = AppInspector()
```

- Quartz/AppKitが利用できない場合はRuntimeErrorを送出

### メソッド

#### `get_frontmost_app() -> Dict[str, str]`

最前面のアプリケーション情報を取得する。

- **入力**: なし
- **出力**:
  ```python
  {"name": "Safari", "bundle_id": "com.apple.Safari"}
  ```
  エラー時: `{"name": "Unknown", "bundle_id": "", "error": "..."}`

#### `get_element_at_position(x: float, y: float) -> Dict[str, Any]`

指定座標のUI要素情報を取得する。

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
      "value": None,
      "frame": {"x": 100, "y": 200, "width": 80, "height": 30}
  }
  ```
  エラー時: `{"error": "No element found at (x, y)", "code": ...}`

#### `get_full_info(x: float, y: float) -> Dict[str, Any]`

アプリ情報+UI要素情報をまとめて取得する。

- **入力**: `x`, `y` 座標
- **出力**:
  ```python
  {
      "app": {"name": "...", "bundle_id": "..."},
      "element": {"role": "...", ...},
      "coordinates": {"x": x, "y": y}
  }
  ```

## 依存ライブラリ

- `pyobjc-framework-ApplicationServices`
- `pyobjc-framework-Cocoa`
