"""
マウスカーソル位置のウィンドウまたはUI要素を赤枠で囲ってスクリーンショットを撮るモジュール

【使用方法】
from window_screenshot import WindowScreenshot

# UI要素レベルで赤枠（デフォルト: elementモード）
ws = WindowScreenshot(output_dir="./screenshots")
result = ws.capture_window_at_cursor()
# => 検索窓やボタンなど、クリック位置のUI要素だけに赤枠

# ウィンドウレベルで赤枠（従来動作）
ws = WindowScreenshot(output_dir="./screenshots", detection_mode="window")
result = ws.capture_window_at_cursor()
# => ウィンドウ全体に赤枠

# 結果形式:
# => {
#     "full_screenshot": "screenshots/full_20240101_120000.png",
#     "cropped_screenshot": "screenshots/crop_20240101_120000.png",
#     "window_info": {...},
#     "detection_mode": "element" or "window",
#     "json_path": "screenshots/cap_20240101_120000.json"
# }

# ウィンドウ部分だけ切り出し + 赤枠
result = ws.capture_window_at_cursor(crop_only=True)

【処理内容】
1. マウスカーソル位置のターゲットを検出（detection_modeに応じて）
   - element: Accessibility APIでUI要素フレームを取得（失敗時はwindowにフォールバック）
   - window: 従来のウィンドウレベル検出
2. カーソル位置のモニターを特定し、そのモニターだけスクリーンショットを撮影 + 全モニター情報収集
3. 全ウィンドウ一覧取得、ブラウザURL/タイトル取得
4. Pillowでターゲット範囲に赤枠を描画
5. オプションでターゲット部分のみクロップ
6. ファイルに保存 + 包括的JSON保存して結果を返却

【必要環境】
- Linux: X11ディスプレイサーバー + xdotool + DISPLAY環境変数
- macOS: pyobjc-framework-Quartz（スクリーン録画権限が必要）
  - elementモード: pyobjc-framework-ApplicationServices + アクセシビリティ権限
- pip: mss, Pillow
"""

import sys
import mss
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime


def _create_detector():
    """
    OSに応じたWindowDetectorを生成するファクトリ関数

    Output:
        WindowDetector or WindowDetectorMac: OS対応のdetectorインスタンス
    """
    if sys.platform == "darwin":
        from window_detector_mac import WindowDetectorMac
        return WindowDetectorMac()
    else:
        from window_detector import WindowDetector
        return WindowDetector()


def _create_element_inspector():
    """
    macOS専用: AppInspectorを生成するファクトリ関数
    macOS以外またはインポート失敗時はNoneを返す

    Output:
        AppInspector or None: Accessibility APIベースのUI要素インスペクター
    """
    if sys.platform != "darwin":
        return None
    try:
        from common.app_inspector import AppInspector
        return AppInspector()
    except Exception as e:
        print(f"AppInspector初期化失敗（windowモードで動作します）: {e}")
        return None


class WindowScreenshot:
    """
    マウスカーソル位置のウィンドウを赤枠で囲ってスクリーンショットを撮るクラス
    Linux (X11) と macOS に対応
    """

    def __init__(self, output_dir: str = "./screenshots", detection_mode: str = "element"):
        """
        初期化（OSを自動判別してdetectorを選択）

        Input:
            output_dir: スクリーンショット保存先ディレクトリ
            detection_mode: 検出モード
                "element" (デフォルト): UI要素レベルで検出（macOS専用、失敗時windowにフォールバック）
                "window": 従来のウィンドウレベル検出
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # OS自動判別で適切なdetectorを生成（疎結合）
        self.detector = _create_detector()

        # elementモード用のインスペクター
        self.detection_mode = detection_mode
        self.inspector = None
        if detection_mode == "element":
            self.inspector = _create_element_inspector()
            if self.inspector is None:
                print("AppInspector利用不可: windowモードにフォールバック")
                self.detection_mode = "window"

    def _normalize_element_info(self, element_info: Dict, mouse_x: int, mouse_y: int) -> Dict:
        """
        AppInspectorの出力をwindow_info互換形式に変換（できる限り多くの情報を保持）

        Input:
            element_info: AppInspector.get_element_at_position()の戻り値
            mouse_x: マウスX座標
            mouse_y: マウスY座標
        Output:
            Dict: window_info互換形式（UI要素の全情報を含む）
        """
        frame = element_info.get("frame", {})
        role = element_info.get("role", "")
        title = element_info.get("title", "")
        description = element_info.get("description", "")
        identifier = element_info.get("identifier", "")
        value = element_info.get("value", "")

        # 表示名: title > description > role の優先順
        name = title or description or role or "UI Element"

        return {
            "x": int(frame.get("x", 0)),
            "y": int(frame.get("y", 0)),
            "width": int(frame.get("width", 0)),
            "height": int(frame.get("height", 0)),
            "name": name,
            "role": role,
            "title": title,
            "description": description,
            "identifier": identifier,
            "value": value,
            "placeholder": element_info.get("placeholder"),
            "focused": element_info.get("focused"),
            "enabled": element_info.get("enabled"),
            "role_description": element_info.get("role_description"),
            "detection_type": "element",
            "mouse_x": mouse_x,
            "mouse_y": mouse_y,
        }

    def _detect_target(self) -> Optional[Dict]:
        """
        detection_modeに応じたターゲット検出。elementモードではUI要素を検出し、
        失敗時はwindowにフォールバック。

        Input: なし
        Output:
            Dict: ターゲット情報（window_info互換形式）
                detection_type="element" or "window" を含む
            None: 検出失敗
        """
        if self.detection_mode == "element" and self.inspector is not None:
            try:
                # まずウィンドウ情報を取得（コンテキスト用）
                window_info = self.detector.get_window_at_cursor()
                if window_info is None:
                    return None

                mouse_x = window_info.get("mouse_x", 0)
                mouse_y = window_info.get("mouse_y", 0)

                # UI要素を検出
                element_info = self.inspector.get_element_at_position(mouse_x, mouse_y)

                # アプリ情報を取得
                app_info = self.inspector.get_frontmost_app()

                # frameが有効かチェック
                frame = element_info.get("frame")
                if frame and frame.get("width", 0) > 0 and frame.get("height", 0) > 0:
                    normalized = self._normalize_element_info(element_info, mouse_x, mouse_y)
                    # ウィンドウ・アプリ情報も保持（できる限り多くの情報）
                    normalized["window_id"] = window_info.get("window_id", 0)
                    normalized["window_owner"] = window_info.get("owner", "")
                    normalized["window_owner_pid"] = window_info.get("owner_pid", 0)
                    normalized["window_name"] = window_info.get("name", "")
                    normalized["window_x"] = window_info.get("x", 0)
                    normalized["window_y"] = window_info.get("y", 0)
                    normalized["window_width"] = window_info.get("width", 0)
                    normalized["window_height"] = window_info.get("height", 0)
                    normalized["app_name"] = app_info.get("name", "")
                    normalized["app_bundle_id"] = app_info.get("bundle_id", "")
                    normalized["app_pid"] = app_info.get("pid", 0)
                    return normalized

                # frame無効 → windowにフォールバック（アプリ情報は付与）
                print("UI要素のframe取得失敗: windowモードにフォールバック")
                window_info["detection_type"] = "window"
                window_info["app_name"] = app_info.get("name", "")
                window_info["app_bundle_id"] = app_info.get("bundle_id", "")
                window_info["app_pid"] = app_info.get("pid", 0)
                return window_info

            except Exception as e:
                print(f"UI要素検出エラー: {e} → windowモードにフォールバック")
                window_info = self.detector.get_window_at_cursor()
                if window_info:
                    window_info["detection_type"] = "window"
                return window_info

        # windowモード: 従来通り（macOSならアプリ情報も付与）
        window_info = self.detector.get_window_at_cursor()
        if window_info:
            window_info["detection_type"] = "window"
            if sys.platform == "darwin" and self.inspector is not None:
                try:
                    app_info = self.inspector.get_frontmost_app()
                    window_info["app_name"] = app_info.get("name", "")
                    window_info["app_bundle_id"] = app_info.get("bundle_id", "")
                except Exception:
                    pass
        return window_info

    def _find_monitor_at(self, x: int, y: int) -> Tuple[dict, int]:
        """
        指定座標を含むモニターを返す

        Input:
            x: グローバルX座標
            y: グローバルY座標
        Output:
            Tuple[dict, int]: (mssモニター辞書, モニターインデックス1始まり)
            座標がどのモニターにも含まれない場合はプライマリモニター(index=1)を返す
        """
        with mss.mss() as sct:
            # monitors[1:]が個別モニター（[0]は全結合）
            for i, mon in enumerate(sct.monitors[1:], start=1):
                if (mon["left"] <= x < mon["left"] + mon["width"]
                        and mon["top"] <= y < mon["top"] + mon["height"]):
                    return mon, i
            # 見つからなければプライマリ
            return sct.monitors[1], 1

    def take_full_screenshot(self, monitor: dict = None) -> Image.Image:
        """
        スクリーンショットを撮影してPIL Imageで返す

        Input:
            monitor: mssモニター辞書。Noneならプライマリモニターをキャプチャ
        Output:
            Image.Image: スクリーンショット画像
        """
        with mss.mss() as sct:
            if monitor is None:
                monitor = sct.monitors[1]  # プライマリモニター
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            return img

    def draw_red_border(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        height: int,
        border_width: int = 3
    ) -> Image.Image:
        """
        画像の指定領域に赤枠を描画

        Input:
            image: 描画対象の画像
            x: 枠の左上X座標
            y: 枠の左上Y座標
            width: 枠の幅
            height: 枠の高さ
            border_width: 枠線の太さ（デフォルト3px）

        Output:
            Image.Image: 赤枠を描画した画像（元画像のコピー）
        """
        img_copy = image.copy()
        draw = ImageDraw.Draw(img_copy)

        # 赤枠を描画
        for i in range(border_width):
            draw.rectangle(
                [
                    (x - i, y - i),
                    (x + width + i, y + height + i)
                ],
                outline=(255, 0, 0)
            )

        return img_copy

    def crop_window_area(
        self,
        image: Image.Image,
        x: int,
        y: int,
        width: int,
        height: int,
        padding: int = 5
    ) -> Image.Image:
        """
        ウィンドウ領域を切り出す

        Input:
            image: 切り出し元の画像
            x: ウィンドウ左上X座標
            y: ウィンドウ左上Y座標
            width: ウィンドウ幅
            height: ウィンドウ高さ
            padding: 切り出し領域の余白（デフォルト5px）

        Output:
            Image.Image: 切り出した画像
        """
        # 画像範囲内にクリッピング
        left = max(0, x - padding)
        top = max(0, y - padding)
        right = min(image.width, x + width + padding)
        bottom = min(image.height, y + height + padding)

        return image.crop((left, top, right, bottom))

    def add_window_info_label(
        self,
        image: Image.Image,
        window_info: Dict,
        position: str = "bottom"
    ) -> Image.Image:
        """
        画像の外側にウィンドウ情報ラベルバーを追加（画面に被らない）

        Input:
            image: ラベルを追加する画像
            window_info: ウィンドウ情報辞書
            position: ラベル位置 ("top" or "bottom")

        Output:
            Image.Image: ラベルバーを外側に追加した画像（元画像より高さが増える）
        """
        detection_type = window_info.get("detection_type", "window")
        if detection_type == "element":
            role = window_info.get("role", "")
            app_name = window_info.get("window_owner", "")
            label_text = (
                f"Element: {window_info.get('name', '不明')} [{role}] | "
                f"App: {app_name} | "
                f"Position: ({window_info.get('x', 0)}, {window_info.get('y', 0)}) | "
                f"Size: {window_info.get('width', 0)}x{window_info.get('height', 0)}"
            )
        else:
            label_text = (
                f"Window: {window_info.get('name', '不明')} | "
                f"Position: ({window_info.get('x', 0)}, {window_info.get('y', 0)}) | "
                f"Size: {window_info.get('width', 0)}x{window_info.get('height', 0)}"
            )

        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        # テキストサイズを計算
        temp_img = Image.new("RGB", (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), label_text, font=font)
        text_height = bbox[3] - bbox[1]

        padding = 5
        bar_height = text_height + padding * 2

        # 元画像の外側にバーを追加した新しいキャンバスを作成
        new_width = image.width
        new_height = image.height + bar_height

        new_img = Image.new("RGB", (new_width, new_height), (0, 0, 0))

        if position == "top":
            # ラベルバーを上に、画像を下に
            new_img.paste(image, (0, bar_height))
            text_y = padding
        else:
            # 画像を上に、ラベルバーを下に
            new_img.paste(image, (0, 0))
            text_y = image.height + padding

        draw = ImageDraw.Draw(new_img)
        draw.text(
            (padding, text_y),
            label_text,
            fill=(255, 255, 255),
            font=font
        )

        return new_img

    def _collect_monitors(self) -> list:
        """
        全モニター情報を収集

        Output:
            list: mss.monitorsの全モニター情報
        """
        try:
            with mss.mss() as sct:
                return list(sct.monitors)
        except Exception as e:
            print(f"モニター情報取得失敗: {e}")
            return []

    def _collect_all_windows(self) -> list:
        """
        全ウィンドウ一覧を取得

        Output:
            list: detector.get_all_windows()の戻り値
        """
        try:
            if hasattr(self.detector, "get_all_windows"):
                return self.detector.get_all_windows()
            return []
        except Exception as e:
            print(f"全ウィンドウ取得失敗: {e}")
            return []

    def _collect_browser_info(self, window_info: Dict) -> Dict:
        """
        ブラウザ情報を取得

        Input:
            window_info: ターゲット情報（app_pid or owner_pid を含む）
        Output:
            dict: ブラウザ情報 {"is_browser": bool, "url": str, "page_title": str}
        """
        if self.inspector is None:
            return {"is_browser": False, "url": None, "page_title": None}
        try:
            pid = window_info.get("app_pid") or window_info.get("window_owner_pid") or window_info.get("owner_pid", 0)
            if pid:
                return self.inspector.get_browser_info(pid)
            return {"is_browser": False, "url": None, "page_title": None}
        except Exception as e:
            print(f"ブラウザ情報取得失敗: {e}")
            return {"is_browser": False, "url": None, "page_title": None}

    def capture_window_at_cursor(
        self,
        crop_only: bool = False,
        add_label: bool = True,
        border_width: int = 3,
        prefix: str = ""
    ) -> Optional[Dict]:
        """
        マウスカーソル位置のウィンドウを赤枠で囲ってスクショ撮影 + JSON保存

        Input:
            crop_only: Trueの場合、ウィンドウ部分のみ切り出し
            add_label: ウィンドウ情報ラベルを追加するか
            border_width: 赤枠の太さ
            prefix: ファイル名プレフィックス

        Output:
            Dict: 結果情報
                {
                    "full_screenshot": str (フルスクショのパス),
                    "cropped_screenshot": str or None (クロップ画像のパス),
                    "window_info": Dict (ウィンドウ情報),
                    "timestamp": str,
                    "json_path": str (JSONファイルのパス)
                }
            None: ウィンドウ検出に失敗した場合
        """
        # ターゲット情報を取得（element or windowモード）
        window_info = self._detect_target()
        if window_info is None:
            print("ターゲットを検出できませんでした")
            return None

        # カーソル位置のモニターを特定してキャプチャ
        mouse_x = window_info.get("mouse_x", window_info.get("x", 0))
        mouse_y = window_info.get("mouse_y", window_info.get("y", 0))
        active_mon, _ = self._find_monitor_at(mouse_x, mouse_y)
        full_img = self.take_full_screenshot(monitor=active_mon)

        # グローバル座標 → モニターローカル座標に変換
        mon_left = active_mon["left"]
        mon_top = active_mon["top"]
        local_x = window_info["x"] - mon_left
        local_y = window_info["y"] - mon_top

        # 赤枠描画（ローカル座標）
        bordered_img = self.draw_red_border(
            full_img,
            local_x,
            local_y,
            window_info["width"],
            window_info["height"],
            border_width=border_width
        )

        # タイムスタンプ
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_prefix = f"{prefix}_" if prefix else ""

        # 結果格納用
        result = {
            "window_info": window_info,
            "timestamp": timestamp,
            "detection_mode": window_info.get("detection_type", self.detection_mode),
            "full_screenshot": None,
            "cropped_screenshot": None,
            "json_path": None,
        }

        # フルスクショ保存
        if not crop_only:
            if add_label:
                bordered_img = self.add_window_info_label(bordered_img, window_info)

            full_path = self.output_dir / f"{file_prefix}full_{timestamp}.png"
            bordered_img.save(str(full_path))
            result["full_screenshot"] = str(full_path.absolute())

        # クロップ画像保存（ローカル座標）
        cropped_img = self.crop_window_area(
            self.draw_red_border(
                full_img,
                local_x,
                local_y,
                window_info["width"],
                window_info["height"],
                border_width=border_width
            ),
            local_x,
            local_y,
            window_info["width"],
            window_info["height"],
        )

        if add_label:
            cropped_img = self.add_window_info_label(cropped_img, window_info)

        crop_path = self.output_dir / f"{file_prefix}crop_{timestamp}.png"
        cropped_img.save(str(crop_path))
        result["cropped_screenshot"] = str(crop_path.absolute())

        # 包括的JSON保存
        try:
            from common.json_saver import build_capture_payload, save_capture_json

            monitors = self._collect_monitors()
            all_windows = self._collect_all_windows()
            browser_info = self._collect_browser_info(window_info)

            payload = build_capture_payload(
                capture_result=result,
                monitors=monitors,
                all_windows=all_windows,
                browser_info=browser_info,
            )

            json_path = self.output_dir / f"{file_prefix}cap_{timestamp}.json"
            payload["screenshots"]["json"] = str(json_path.absolute())
            result["json_path"] = save_capture_json(payload, str(json_path))
        except Exception as e:
            print(f"JSON保存失敗（スクショは正常保存済み）: {e}")

        return result

    def capture_with_window_info(
        self,
        window_info: Dict,
        crop_only: bool = False,
        add_label: bool = True,
        border_width: int = 3,
        prefix: str = ""
    ) -> Dict:
        """
        外部から渡されたウィンドウ情報を使ってスクショ撮影
        （マウストラッカーと連携する場合に使用）

        Input:
            window_info: ウィンドウ情報辞書
                {"x": int, "y": int, "width": int, "height": int, "name": str}
            crop_only: ウィンドウ部分のみ切り出し
            add_label: ラベル追加
            border_width: 赤枠の太さ
            prefix: ファイル名プレフィックス

        Output:
            Dict: capture_window_at_cursorと同じ形式
        """
        # ウィンドウ位置のモニターを特定してキャプチャ
        wx = window_info.get("x", 0)
        wy = window_info.get("y", 0)
        active_mon, _ = self._find_monitor_at(wx, wy)
        full_img = self.take_full_screenshot(monitor=active_mon)

        # グローバル座標 → モニターローカル座標
        mon_left = active_mon["left"]
        mon_top = active_mon["top"]
        local_x = wx - mon_left
        local_y = wy - mon_top

        bordered_img = self.draw_red_border(
            full_img,
            local_x,
            local_y,
            window_info["width"],
            window_info["height"],
            border_width=border_width
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_prefix = f"{prefix}_" if prefix else ""

        result = {
            "window_info": window_info,
            "timestamp": timestamp,
            "full_screenshot": None,
            "cropped_screenshot": None,
        }

        if not crop_only:
            if add_label:
                bordered_img = self.add_window_info_label(bordered_img, window_info)
            full_path = self.output_dir / f"{file_prefix}full_{timestamp}.png"
            bordered_img.save(str(full_path))
            result["full_screenshot"] = str(full_path.absolute())

        cropped_img = self.crop_window_area(
            self.draw_red_border(
                full_img,
                local_x,
                local_y,
                window_info["width"],
                window_info["height"],
                border_width=border_width
            ),
            local_x,
            local_y,
            window_info["width"],
            window_info["height"],
        )
        if add_label:
            cropped_img = self.add_window_info_label(cropped_img, window_info)
        crop_path = self.output_dir / f"{file_prefix}crop_{timestamp}.png"
        cropped_img.save(str(crop_path))
        result["cropped_screenshot"] = str(crop_path.absolute())

        return result
