"""
マウスカーソル位置のウィンドウを検出するモジュール

【使用方法】
from window_detector import WindowDetector

detector = WindowDetector()

# マウスカーソル位置のウィンドウ情報を取得
window_info = detector.get_window_at_cursor()
# => {"window_id": "0x1234", "name": "Firefox", "x": 100, "y": 50, "width": 800, "height": 600}

# 指定座標のウィンドウ情報を取得
window_info = detector.get_window_at_position(500, 300)

【処理内容】
1. xdotoolを使ってマウスカーソル位置を取得
2. その座標にあるウィンドウIDを取得
3. ウィンドウのジオメトリ（位置・サイズ）を取得
4. ウィンドウ名を取得
5. 結果を辞書で返却

【必要環境】
- Linux + X11ディスプレイサーバー
- xdotool コマンド
- DISPLAY環境変数が設定されていること
"""

import subprocess
import re
from typing import Dict, Optional, Tuple


class WindowDetector:
    """
    マウスカーソル位置のウィンドウを検出するクラス
    X11環境 + xdotool が必要
    """

    def __init__(self):
        """初期化時にxdotoolの存在を確認"""
        self._check_xdotool()

    def _check_xdotool(self):
        """xdotoolがインストールされているか確認"""
        try:
            subprocess.run(
                ["which", "xdotool"],
                capture_output=True, text=True, check=True
            )
        except subprocess.CalledProcessError:
            raise EnvironmentError(
                "xdotoolが見つかりません。sudo apt install xdotool でインストールしてください"
            )

    def _run_cmd(self, cmd: list) -> str:
        """
        コマンドを実行して標準出力を返す

        Input:
            cmd: 実行するコマンドのリスト
        Output:
            str: 標準出力の文字列
        """
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"コマンド失敗: {' '.join(cmd)}\nstderr: {result.stderr}"
            )
        return result.stdout.strip()

    def get_mouse_position(self) -> Tuple[int, int]:
        """
        現在のマウスカーソル位置を取得

        Input: なし
        Output:
            Tuple[int, int]: (x, y) マウス座標
        """
        output = self._run_cmd(["xdotool", "getmouselocation"])
        # 出力例: x:500 y:300 screen:0 window:12345678
        match = re.search(r'x:(\d+)\s+y:(\d+)', output)
        if not match:
            raise RuntimeError(f"マウス位置の解析に失敗: {output}")
        return int(match.group(1)), int(match.group(2))

    def get_window_id_at_position(self, x: int, y: int) -> str:
        """
        指定座標にあるウィンドウのIDを取得

        Input:
            x: X座標
            y: Y座標
        Output:
            str: ウィンドウID (例: "12345678")
        """
        # マウスを指定位置に移動せずにウィンドウを取得
        # xdotool getmouselocation で現在のwindow IDを取得する方法を使用
        output = self._run_cmd(["xdotool", "getmouselocation"])
        match = re.search(r'window:(\d+)', output)
        if not match:
            raise RuntimeError(f"ウィンドウIDの取得に失敗: {output}")
        return match.group(1)

    def get_window_geometry(self, window_id: str) -> Dict[str, int]:
        """
        ウィンドウのジオメトリ（位置・サイズ）を取得

        Input:
            window_id: ウィンドウID
        Output:
            Dict[str, int]: {"x": int, "y": int, "width": int, "height": int}
        """
        # ウィンドウ位置を取得
        pos_output = self._run_cmd(
            ["xdotool", "getwindowgeometry", window_id]
        )
        # 出力例:
        # Window 12345678
        #   Position: 100,50 (screen: 0)
        #   Geometry: 800x600

        pos_match = re.search(r'Position:\s*(\d+),(\d+)', pos_output)
        geo_match = re.search(r'Geometry:\s*(\d+)x(\d+)', pos_output)

        if not pos_match or not geo_match:
            raise RuntimeError(
                f"ウィンドウジオメトリの解析に失敗: {pos_output}"
            )

        return {
            "x": int(pos_match.group(1)),
            "y": int(pos_match.group(2)),
            "width": int(geo_match.group(1)),
            "height": int(geo_match.group(2)),
        }

    def get_window_name(self, window_id: str) -> str:
        """
        ウィンドウ名を取得

        Input:
            window_id: ウィンドウID
        Output:
            str: ウィンドウ名（タイトルバーのテキスト）
        """
        try:
            return self._run_cmd(["xdotool", "getwindowname", window_id])
        except RuntimeError:
            return "(不明)"

    def get_window_at_cursor(self) -> Optional[Dict]:
        """
        現在のマウスカーソル位置にあるウィンドウの全情報を取得

        Input: なし
        Output:
            Dict: ウィンドウ情報
                {
                    "window_id": str,
                    "name": str,
                    "x": int,
                    "y": int,
                    "width": int,
                    "height": int,
                    "mouse_x": int,
                    "mouse_y": int
                }
            None: ウィンドウが見つからない場合
        """
        try:
            mouse_x, mouse_y = self.get_mouse_position()
            window_id = self.get_window_id_at_position(mouse_x, mouse_y)
            geometry = self.get_window_geometry(window_id)
            name = self.get_window_name(window_id)

            return {
                "window_id": window_id,
                "name": name,
                "x": geometry["x"],
                "y": geometry["y"],
                "width": geometry["width"],
                "height": geometry["height"],
                "mouse_x": mouse_x,
                "mouse_y": mouse_y,
            }
        except (RuntimeError, EnvironmentError) as e:
            print(f"ウィンドウ検出エラー: {e}")
            return None

    def get_window_at_position(self, x: int, y: int) -> Optional[Dict]:
        """
        指定座標にあるウィンドウの全情報を取得

        Input:
            x: X座標
            y: Y座標
        Output:
            Dict: get_window_at_cursorと同じ形式
            None: ウィンドウが見つからない場合
        """
        try:
            window_id = self.get_window_id_at_position(x, y)
            geometry = self.get_window_geometry(window_id)
            name = self.get_window_name(window_id)

            return {
                "window_id": window_id,
                "name": name,
                "x": geometry["x"],
                "y": geometry["y"],
                "width": geometry["width"],
                "height": geometry["height"],
                "mouse_x": x,
                "mouse_y": y,
            }
        except (RuntimeError, EnvironmentError) as e:
            print(f"ウィンドウ検出エラー: {e}")
            return None
