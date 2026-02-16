"""
window_detector + window_screenshot のテストスクリプト

【使用方法】
cd claude/src && python test_window_screenshot.py

【処理内容】
- macOS: Quartz, ApplicationServices, mss, Pillow確認 → UI要素検出 → elementモードスクショ → windowモードスクショ
- Linux: Xvfb仮想ディスプレイ上でxdotool, mss, Pillow確認 → ウィンドウ検出 → 赤枠スクショ
"""

import subprocess
import sys
import os
import json
import time


def test_environment():
    """環境テスト: DISPLAY, xdotool, mss, Pillow の確認"""
    print("=" * 50)
    print("【環境テスト】")
    print("=" * 50)

    errors = []

    # DISPLAY確認
    display = os.environ.get("DISPLAY", "")
    print(f"  DISPLAY: '{display}'")
    if not display:
        errors.append("DISPLAY環境変数が未設定")

    # xdotool確認
    try:
        result = subprocess.run(
            ["xdotool", "version"], capture_output=True, text=True
        )
        print(f"  xdotool: OK ({result.stdout.strip()})")
    except FileNotFoundError:
        errors.append("xdotoolがインストールされていない")
        print("  xdotool: NG (not found)")

    # mss確認
    try:
        import mss
        print(f"  mss: OK (v{mss.__version__})")
    except ImportError:
        errors.append("mssがインストールされていない")
        print("  mss: NG (not installed)")

    # Pillow確認
    try:
        from PIL import Image
        import PIL
        print(f"  Pillow: OK (v{PIL.__version__})")
    except ImportError:
        errors.append("Pillowがインストールされていない")
        print("  Pillow: NG (not installed)")

    if errors:
        print(f"\n  エラー: {len(errors)}件")
        for e in errors:
            print(f"    - {e}")
        return False

    print("  すべてOK")
    return True


def test_xdotool_commands():
    """xdotoolの各コマンドが動作するかテスト"""
    print("\n" + "=" * 50)
    print("【xdotoolコマンドテスト】")
    print("=" * 50)

    tests = {
        "getmouselocation": ["xdotool", "getmouselocation"],
        "getactivewindow": ["xdotool", "getactivewindow"],
        "getdisplaygeometry": ["xdotool", "getdisplaygeometry"],
    }

    results = {}
    for name, cmd in tests.items():
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print(f"  {name}: OK -> {result.stdout.strip()}")
                results[name] = {"status": "OK", "output": result.stdout.strip()}
            else:
                print(f"  {name}: NG (returncode={result.returncode}, stderr={result.stderr.strip()})")
                results[name] = {"status": "NG", "error": result.stderr.strip()}
        except Exception as e:
            print(f"  {name}: NG ({e})")
            results[name] = {"status": "NG", "error": str(e)}

    return results


def test_screenshot():
    """mssでスクリーンショットが撮れるかテスト"""
    print("\n" + "=" * 50)
    print("【スクリーンショットテスト】")
    print("=" * 50)

    try:
        import mss
        with mss.mss() as sct:
            monitors = sct.monitors
            print(f"  モニター数: {len(monitors) - 1}")
            for i, m in enumerate(monitors):
                print(f"    monitor[{i}]: {m}")

            # スクショ撮影
            screenshot = sct.grab(monitors[0])
            print(f"  スクショサイズ: {screenshot.size}")

            # 保存テスト
            from PIL import Image
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            test_path = "/tmp/test_screenshot.png"
            img.save(test_path)
            print(f"  保存テスト: OK -> {test_path}")
            return True

    except Exception as e:
        print(f"  スクショテスト失敗: {e}")
        return False


def test_window_detection():
    """ウィンドウ検出のフルテスト"""
    print("\n" + "=" * 50)
    print("【ウィンドウ検出テスト】")
    print("=" * 50)

    try:
        from window_detector import WindowDetector

        detector = WindowDetector()

        # マウス位置取得
        mouse_x, mouse_y = detector.get_mouse_position()
        print(f"  マウス位置: ({mouse_x}, {mouse_y})")

        # ウィンドウ情報取得
        window_info = detector.get_window_at_cursor()
        if window_info:
            print(f"  ウィンドウ検出: OK")
            print(f"    ID: {window_info['window_id']}")
            print(f"    名前: {window_info['name']}")
            print(f"    位置: ({window_info['x']}, {window_info['y']})")
            print(f"    サイズ: {window_info['width']}x{window_info['height']}")
            return window_info
        else:
            print("  ウィンドウ検出: NG (window_info is None)")
            return None

    except Exception as e:
        print(f"  ウィンドウ検出エラー: {e}")
        return None


def test_full_capture():
    """赤枠スクショのフルテスト"""
    print("\n" + "=" * 50)
    print("【赤枠スクショ フルテスト】")
    print("=" * 50)

    try:
        from window_screenshot import WindowScreenshot

        ws = WindowScreenshot(output_dir="/tmp/test_window_screenshots")

        result = ws.capture_window_at_cursor(
            crop_only=False,
            add_label=True,
            border_width=3,
            prefix="test"
        )

        if result:
            print("  赤枠スクショ: OK")
            print(f"    フルスクショ: {result['full_screenshot']}")
            print(f"    クロップスクショ: {result['cropped_screenshot']}")
            print(f"    ウィンドウ: {result['window_info']['name']}")
            return result
        else:
            print("  赤枠スクショ: NG (result is None)")
            return None

    except Exception as e:
        print(f"  赤枠スクショエラー: {e}")
        import traceback
        traceback.print_exc()
        return None


## ================================
## JSON出力・ブラウザ情報・全ウィンドウ・モニター テスト
## ================================

def test_json_output():
    """JSON保存 + 内容検証テスト"""
    print("\n" + "=" * 50)
    print("【JSON出力テスト】")
    print("=" * 50)

    try:
        from window_screenshot import WindowScreenshot
        import tempfile

        output_dir = tempfile.mkdtemp(prefix="test_json_")
        ws = WindowScreenshot(output_dir=output_dir, detection_mode="element")

        result = ws.capture_window_at_cursor(prefix="json_test")

        if result is None:
            print("  JSON出力テスト: NG (result is None)")
            return None

        json_path = result.get("json_path")
        if not json_path:
            print("  JSON出力テスト: NG (json_path not found)")
            return None

        # JSONファイルの読み込みと検証
        with open(json_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        required_keys = [
            "capture_id", "timestamp", "detection_mode", "mouse",
            "target", "app", "browser", "window", "all_windows",
            "monitors", "screenshots"
        ]
        missing_keys = [k for k in required_keys if k not in payload]
        if missing_keys:
            print(f"  JSON出力テスト: NG (missing keys: {missing_keys})")
            return None

        print(f"  JSON出力テスト: OK")
        print(f"    json_path: {json_path}")
        print(f"    capture_id: {payload['capture_id']}")
        print(f"    timestamp: {payload['timestamp']}")
        print(f"    detection_mode: {payload['detection_mode']}")
        print(f"    target.name: {payload['target'].get('name')}")
        print(f"    target.value: {str(payload['target'].get('value', ''))[:50]}")
        print(f"    app.name: {payload['app'].get('name')}")
        print(f"    browser.is_browser: {payload['browser'].get('is_browser')}")
        if payload['browser'].get('url'):
            print(f"    browser.url: {payload['browser']['url'][:80]}")
        if payload['browser'].get('page_title'):
            print(f"    browser.page_title: {payload['browser']['page_title'][:80]}")
        print(f"    monitors数: {len(payload.get('monitors', []))}")
        print(f"    all_windows数: {len(payload.get('all_windows', []))}")
        return payload

    except Exception as e:
        print(f"  JSON出力テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_browser_info():
    """ブラウザ情報取得テスト"""
    print("\n" + "=" * 50)
    print("【ブラウザ情報テスト】")
    print("=" * 50)

    try:
        from common.app_inspector import AppInspector

        inspector = AppInspector()
        app_info = inspector.get_frontmost_app()
        pid = app_info.get("pid", 0)
        bundle_id = app_info.get("bundle_id", "")

        print(f"  最前面アプリ: {app_info.get('name')} (pid={pid})")
        print(f"  bundle_id: {bundle_id}")

        browser_info = inspector.get_browser_info(pid)
        print(f"  is_browser: {browser_info.get('is_browser')}")
        if browser_info.get("url"):
            print(f"  url: {browser_info['url'][:100]}")
        if browser_info.get("page_title"):
            print(f"  page_title: {browser_info['page_title'][:100]}")

        return browser_info

    except Exception as e:
        print(f"  ブラウザ情報テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_all_windows():
    """全ウィンドウ一覧テスト"""
    print("\n" + "=" * 50)
    print("【全ウィンドウ一覧テスト】")
    print("=" * 50)

    try:
        from window_detector_mac import WindowDetectorMac

        detector = WindowDetectorMac()
        windows = detector.get_all_windows()

        print(f"  ウィンドウ数: {len(windows)}")
        for i, win in enumerate(windows[:10]):  # 最初の10個
            print(f"    [{i}] id={win['window_id']} "
                  f"owner={win['owner']} "
                  f"name={win.get('name', '')[:30]} "
                  f"({win['x']},{win['y']}) {win['width']}x{win['height']}")
        if len(windows) > 10:
            print(f"    ... 他 {len(windows) - 10} ウィンドウ")

        return windows

    except Exception as e:
        print(f"  全ウィンドウ一覧テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_monitor_info():
    """モニター情報テスト"""
    print("\n" + "=" * 50)
    print("【モニター情報テスト】")
    print("=" * 50)

    try:
        import mss as mss_lib

        with mss_lib.mss() as sct:
            monitors = sct.monitors
            print(f"  モニター数: {len(monitors) - 1} (+ 全体結合)")
            for i, m in enumerate(monitors):
                label = "全体結合" if i == 0 else f"モニター{i}"
                print(f"    [{label}] left={m.get('left',0)} top={m.get('top',0)} "
                      f"width={m.get('width',0)} height={m.get('height',0)}")
            return monitors

    except Exception as e:
        print(f"  モニター情報テストエラー: {e}")
        import traceback
        traceback.print_exc()
        return None


## ================================
## macOS専用テスト
## ================================

def test_environment_mac():
    """macOS環境テスト: Quartz, ApplicationServices, mss, Pillow の確認"""
    print("=" * 50)
    print("【macOS 環境テスト】")
    print("=" * 50)

    errors = []

    # Quartz確認
    try:
        import Quartz
        print(f"  Quartz: OK")
    except ImportError:
        errors.append("pyobjc-framework-Quartzがインストールされていない")
        print("  Quartz: NG (not installed)")

    # ApplicationServices確認
    try:
        from ApplicationServices import AXUIElementCreateSystemWide
        print(f"  ApplicationServices: OK")
    except ImportError:
        errors.append("pyobjc-framework-ApplicationServicesがインストールされていない")
        print("  ApplicationServices: NG (not installed)")

    # mss確認
    try:
        import mss
        print(f"  mss: OK (v{mss.__version__})")
    except ImportError:
        errors.append("mssがインストールされていない")
        print("  mss: NG (not installed)")

    # Pillow確認
    try:
        from PIL import Image
        import PIL
        print(f"  Pillow: OK (v{PIL.__version__})")
    except ImportError:
        errors.append("Pillowがインストールされていない")
        print("  Pillow: NG (not installed)")

    if errors:
        print(f"\n  エラー: {len(errors)}件")
        for e in errors:
            print(f"    - {e}")
        return False

    print("  すべてOK")
    return True


def test_element_detection():
    """macOS: AppInspectorでUI要素検出テスト"""
    print("\n" + "=" * 50)
    print("【UI要素検出テスト】")
    print("=" * 50)

    try:
        from common.app_inspector import AppInspector
        from window_detector_mac import WindowDetectorMac

        inspector = AppInspector()
        detector = WindowDetectorMac()

        # マウス位置取得
        mouse_x, mouse_y = detector.get_mouse_position()
        print(f"  マウス位置: ({mouse_x}, {mouse_y})")

        # UI要素検出
        element_info = inspector.get_element_at_position(mouse_x, mouse_y)
        if "error" not in element_info:
            print(f"  UI要素検出: OK")
            print(f"    role: {element_info.get('role')}")
            print(f"    title: {element_info.get('title')}")
            print(f"    description: {element_info.get('description')}")
            frame = element_info.get("frame")
            if frame:
                print(f"    frame: x={frame['x']}, y={frame['y']}, "
                      f"w={frame['width']}, h={frame['height']}")
            else:
                print("    frame: なし（ウィンドウレベルにフォールバックされます）")
            return element_info
        else:
            print(f"  UI要素検出: NG ({element_info.get('error')})")
            return None

    except Exception as e:
        print(f"  UI要素検出エラー: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_element_screenshot():
    """macOS: elementモードで赤枠スクショテスト"""
    print("\n" + "=" * 50)
    print("【elementモード 赤枠スクショテスト】")
    print("=" * 50)

    try:
        from window_screenshot import WindowScreenshot

        ws = WindowScreenshot(
            output_dir="/tmp/test_window_screenshots",
            detection_mode="element"
        )

        result = ws.capture_window_at_cursor(
            crop_only=False,
            add_label=True,
            border_width=3,
            prefix="element_test"
        )

        if result:
            print(f"  elementモード赤枠スクショ: OK")
            print(f"    検出モード: {result.get('detection_mode')}")
            print(f"    フルスクショ: {result['full_screenshot']}")
            print(f"    クロップスクショ: {result['cropped_screenshot']}")
            print(f"    ターゲット名: {result['window_info']['name']}")
            detection_type = result['window_info'].get('detection_type', 'unknown')
            print(f"    detection_type: {detection_type}")
            if detection_type == "element":
                print(f"    role: {result['window_info'].get('role')}")
            return result
        else:
            print("  elementモード赤枠スクショ: NG (result is None)")
            return None

    except Exception as e:
        print(f"  elementモード赤枠スクショエラー: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_window_mode_screenshot():
    """macOS: windowモード（従来）で赤枠スクショテスト"""
    print("\n" + "=" * 50)
    print("【windowモード 赤枠スクショテスト（従来動作）】")
    print("=" * 50)

    try:
        from window_screenshot import WindowScreenshot

        ws = WindowScreenshot(
            output_dir="/tmp/test_window_screenshots",
            detection_mode="window"
        )

        result = ws.capture_window_at_cursor(
            crop_only=False,
            add_label=True,
            border_width=3,
            prefix="window_test"
        )

        if result:
            print(f"  windowモード赤枠スクショ: OK")
            print(f"    検出モード: {result.get('detection_mode')}")
            print(f"    フルスクショ: {result['full_screenshot']}")
            print(f"    クロップスクショ: {result['cropped_screenshot']}")
            print(f"    ウィンドウ名: {result['window_info']['name']}")
            return result
        else:
            print("  windowモード赤枠スクショ: NG (result is None)")
            return None

    except Exception as e:
        print(f"  windowモード赤枠スクショエラー: {e}")
        import traceback
        traceback.print_exc()
        return None


## ================================
## main（OS分岐）
## ================================

def main_mac():
    """macOS全テスト実行"""
    print("=" * 60)
    print("  マウス位置 UI要素/ウィンドウ 赤枠スクリーンショット テスト (macOS)")
    print("=" * 60)

    all_results = {}

    # 1. macOS環境テスト
    env_ok = test_environment_mac()
    all_results["environment"] = "OK" if env_ok else "NG"

    if not env_ok:
        print("\n環境テスト失敗。これ以上のテストを中止します。")
        all_results["conclusion"] = "環境不備のため実行不可"
        print(f"\n結果JSON: {json.dumps(all_results, ensure_ascii=False, indent=2)}")
        return all_results

    # 2. スクショテスト
    screenshot_ok = test_screenshot()
    all_results["screenshot"] = "OK" if screenshot_ok else "NG"

    # 3. モニター情報テスト
    monitor_info = test_monitor_info()
    all_results["monitor_info"] = "OK" if monitor_info else "NG"

    # 4. 全ウィンドウ一覧テスト
    all_windows = test_all_windows()
    all_results["all_windows"] = "OK" if all_windows else "NG"

    # 5. UI要素検出テスト
    element_info = test_element_detection()
    all_results["element_detection"] = "OK" if element_info else "NG"

    # 6. ブラウザ情報テスト
    browser_info = test_browser_info()
    all_results["browser_info"] = "OK" if browser_info else "NG"

    # 7. elementモードスクショテスト
    element_result = test_element_screenshot()
    all_results["element_screenshot"] = "OK" if element_result else "NG"

    # 8. windowモードスクショテスト（従来動作確認）
    window_result = test_window_mode_screenshot()
    all_results["window_screenshot"] = "OK" if window_result else "NG"

    # 9. JSON出力テスト
    json_result = test_json_output()
    all_results["json_output"] = "OK" if json_result else "NG"

    # 結論
    if element_result and window_result and json_result:
        all_results["conclusion"] = "全テスト成功 - element/windowモード + JSON出力 正常"
    elif element_result and window_result:
        all_results["conclusion"] = "スクショ成功、JSON出力に問題あり"
    elif element_result:
        all_results["conclusion"] = "elementモードは成功、windowモードに問題あり"
    elif window_result:
        all_results["conclusion"] = "windowモードは成功、elementモードに問題あり（フォールバック動作確認要）"
    else:
        all_results["conclusion"] = "スクショテストに失敗"

    print(f"\n{'='*60}")
    print(f"最終結果: {all_results['conclusion']}")
    print(f"{'='*60}")
    print(f"\n結果JSON: {json.dumps(all_results, ensure_ascii=False, indent=2)}")
    return all_results


def main_linux():
    """Linux全テスト実行（従来のテスト）"""
    print("=" * 60)
    print("  マウス位置ウィンドウ 赤枠スクリーンショット テスト (Linux)")
    print("=" * 60)

    all_results = {}

    # 1. 環境テスト
    env_ok = test_environment()
    all_results["environment"] = "OK" if env_ok else "NG"

    if not env_ok:
        print("\n環境テスト失敗。これ以上のテストを中止します。")
        all_results["conclusion"] = "環境不備のため実行不可"
        print(f"\n結果JSON: {json.dumps(all_results, ensure_ascii=False, indent=2)}")
        return all_results

    # 2. xdotoolテスト
    xdotool_results = test_xdotool_commands()
    all_results["xdotool"] = xdotool_results

    # 3. スクショテスト
    screenshot_ok = test_screenshot()
    all_results["screenshot"] = "OK" if screenshot_ok else "NG"

    # 4. ウィンドウ検出テスト
    window_info = test_window_detection()
    all_results["window_detection"] = "OK" if window_info else "NG"

    # 5. フルテスト
    capture_result = test_full_capture()
    all_results["full_capture"] = "OK" if capture_result else "NG"

    # 結論
    if capture_result:
        all_results["conclusion"] = "全テスト成功 - 機能は正常に動作"
    elif window_info:
        all_results["conclusion"] = "ウィンドウ検出は成功したがスクショ撮影に失敗"
    else:
        all_results["conclusion"] = "ウィンドウ検出またはスクショに失敗"

    print(f"\n{'='*60}")
    print(f"最終結果: {all_results['conclusion']}")
    print(f"{'='*60}")
    print(f"\n結果JSON: {json.dumps(all_results, ensure_ascii=False, indent=2)}")
    return all_results


def main():
    """OS判定してテストを実行"""
    if sys.platform == "darwin":
        return main_mac()
    else:
        return main_linux()


if __name__ == "__main__":
    main()
