"""
座標依存ステップの要素検出精度テスト

テスト対象:
  方法A: macOS OCR (ocrmac) — APIなし、ローカルで無料
  方法B: OpenCV テンプレートマッチング — APIなし、ローカルで無料
  方法C: Vision AI (Anthropic Haiku) — API必要

テストケース: AXGroup/AXImage のみで識別情報がないステップ5件
"""
import json
import os
import sys
import time
from pathlib import Path

# --- テストケース定義 ---
TEST_CASES = [
    {
        "id": "TC1",
        "app": "ChatGPT",
        "description": "プロンプト入力欄をクリック",
        "screenshot": "screenshots/click_full_20260217_201245.png",
        "target": {"role": "AXGroup", "title": "AXGroup"},
        "coords": {"x": 984, "y": 985},
    },
    {
        "id": "TC2",
        "app": "Linear",
        "description": "ステータスアイコンをクリック",
        "screenshot": "screenshots/click_full_20260217_211828.png",
        "target": {"role": "AXImage", "title": "AXImage"},
        "coords": {"x": 187, "y": 332},
    },
    {
        "id": "TC3",
        "app": "Google Chrome",
        "description": "Google検索ボックスに入力",
        "screenshot": "screenshots/text_full_20260217_200104.png",
        "target": {"role": "AXGroup", "title": "AXGroup"},
        "coords": {"x": 479, "y": 345},
    },
    {
        "id": "TC4",
        "app": "Google Drive",
        "description": "ファイルメニューボタンをクリック",
        "screenshot": "screenshots/click_full_20260217_203657.png",
        "target": {"role": "AXGroup", "title": "AXGroup"},
        "coords": {"x": 940, "y": 699},
    },
    {
        "id": "TC5",
        "app": "Discord",
        "description": "メッセージエリアをクリック（選択解除）",
        "screenshot": "screenshots/click_full_20260217_194055.png",
        "target": {"role": "AXGroup", "title": "AXGroup"},
        "coords": {"x": 1518, "y": 733},
    },
]

BASE_DIR = Path(__file__).parent


def test_ocr(test_case: dict) -> dict:
    """方法A: macOS OCR (ocrmac) でスクリーンショットからテキストを抽出し、
    クリック座標付近にテキストが見つかるか検証する"""
    try:
        from ocrmac import ocrmac
    except ImportError:
        return {"method": "OCR", "status": "SKIP", "reason": "ocrmac not installed"}

    img_path = str(BASE_DIR / test_case["screenshot"])
    if not os.path.exists(img_path):
        return {"method": "OCR", "status": "SKIP", "reason": f"Screenshot not found: {img_path}"}

    start = time.time()
    # OCR実行（全テキスト抽出 + 座標付き）
    annotations = ocrmac.OCR(img_path, language_preference=["ja-JP", "en-US"]).recognize()
    elapsed = time.time() - start

    # annotations: [(text, confidence, (x, y, w, h)), ...]
    # 座標は正規化済み（0-1）。スクリーンショットのサイズが必要
    import cv2
    img = cv2.imread(img_path)
    if img is None:
        return {"method": "OCR", "status": "ERROR", "reason": "Cannot read image"}
    img_h, img_w = img.shape[:2]

    target_x = test_case["coords"]["x"]
    target_y = test_case["coords"]["y"]

    # クリック座標付近（半径100px以内）のテキストを検索
    RADIUS = 100
    nearby_texts = []
    for text, confidence, bbox in annotations:
        # bbox = (x, y, w, h) normalized 0-1, origin=bottom-left
        bx = bbox[0] * img_w
        by = (1 - bbox[1] - bbox[3]) * img_h  # flip Y (bottom-left → top-left)
        bw = bbox[2] * img_w
        bh = bbox[3] * img_h
        cx = bx + bw / 2
        cy = by + bh / 2

        dist = ((cx - target_x) ** 2 + (cy - target_y) ** 2) ** 0.5
        if dist < RADIUS:
            nearby_texts.append({
                "text": text,
                "confidence": round(confidence, 3),
                "center": (round(cx), round(cy)),
                "distance": round(dist),
            })

    # 半径200pxでも探す（結果がなかった場合の参考用）
    extended_texts = []
    if not nearby_texts:
        for text, confidence, bbox in annotations:
            bx = bbox[0] * img_w
            by = (1 - bbox[1] - bbox[3]) * img_h
            bw = bbox[2] * img_w
            bh = bbox[3] * img_h
            cx = bx + bw / 2
            cy = by + bh / 2
            dist = ((cx - target_x) ** 2 + (cy - target_y) ** 2) ** 0.5
            if dist < 200:
                extended_texts.append({
                    "text": text,
                    "confidence": round(confidence, 3),
                    "center": (round(cx), round(cy)),
                    "distance": round(dist),
                })

    found = len(nearby_texts) > 0
    return {
        "method": "OCR (ocrmac)",
        "status": "FOUND" if found else "NOT_FOUND",
        "nearby_texts_100px": nearby_texts[:5],
        "extended_texts_200px": extended_texts[:5] if not found else [],
        "total_texts_detected": len(annotations),
        "elapsed_sec": round(elapsed, 2),
        "usable_for_relocation": found and any(
            len(t["text"].strip()) >= 2 for t in nearby_texts
        ),
    }


def test_template_matching(test_case: dict) -> dict:
    """方法B: OpenCV テンプレートマッチング
    クリック座標周辺を切り出し、元画像から再検索する（位置ずれシミュレーション）"""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return {"method": "Template", "status": "SKIP", "reason": "opencv not installed"}

    img_path = str(BASE_DIR / test_case["screenshot"])
    if not os.path.exists(img_path):
        return {"method": "Template", "status": "SKIP", "reason": f"Screenshot not found"}

    img = cv2.imread(img_path)
    if img is None:
        return {"method": "Template", "status": "ERROR", "reason": "Cannot read image"}

    img_h, img_w = img.shape[:2]
    target_x = test_case["coords"]["x"]
    target_y = test_case["coords"]["y"]

    start = time.time()

    # テンプレート: クリック座標を中心に 80x80px を切り出し
    TMPL_SIZE = 40  # half-size
    x1 = max(0, target_x - TMPL_SIZE)
    y1 = max(0, target_y - TMPL_SIZE)
    x2 = min(img_w, target_x + TMPL_SIZE)
    y2 = min(img_h, target_y + TMPL_SIZE)
    template = img[y1:y2, x1:x2]

    if template.size == 0:
        return {"method": "Template", "status": "ERROR", "reason": "Template crop failed"}

    # テンプレートマッチング
    result = cv2.matchTemplate(img, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

    # ベストマッチの中心座標
    match_x = max_loc[0] + (x2 - x1) // 2
    match_y = max_loc[1] + (y2 - y1) // 2

    # 上位N個のマッチを取得（閾値0.8以上）
    threshold = 0.8
    locations = np.where(result >= threshold)
    match_count = len(locations[0])

    elapsed = time.time() - start

    # 元の座標との差
    diff_x = abs(match_x - target_x)
    diff_y = abs(match_y - target_y)

    # 自己マッチ（差0px）は当然成功するので、2番目以降のマッチの一意性を確認
    # → 一意性が高い（類似マッチが少ない）ほどテンプレートとして有用
    return {
        "method": "Template Matching (OpenCV)",
        "status": "MATCH",
        "best_match": {
            "x": int(match_x),
            "y": int(match_y),
            "score": round(float(max_val), 4),
        },
        "offset_from_original": {"dx": int(diff_x), "dy": int(diff_y)},
        "matches_above_0.8": int(match_count),
        "uniqueness": "HIGH" if match_count <= 5 else ("MEDIUM" if match_count <= 20 else "LOW"),
        "elapsed_sec": round(elapsed, 3),
        "usable_for_relocation": match_count <= 20 and max_val > 0.9,
    }


def test_vision_ai(test_case: dict) -> dict:
    """方法C: Vision AI (Anthropic Haiku) で要素位置を推定"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"method": "Vision AI", "status": "SKIP", "reason": "ANTHROPIC_API_KEY not set"}

    img_path = str(BASE_DIR / test_case["screenshot"])
    if not os.path.exists(img_path):
        return {"method": "Vision AI", "status": "SKIP", "reason": f"Screenshot not found"}

    try:
        import anthropic
        import base64
    except ImportError:
        return {"method": "Vision AI", "status": "SKIP", "reason": "anthropic package not installed"}

    with open(img_path, "rb") as f:
        img_data = base64.standard_b64encode(f.read()).decode("utf-8")

    mime = "image/png" if img_path.endswith(".png") else "image/jpeg"

    # 改善プロンプト: AXGroupではなく、操作の文脈から要素を特定する
    prompt = (
        f"このスクリーンショットは {test_case['app']} アプリの画面です。\n"
        f"以下の操作を行いたいです: 「{test_case['description']}」\n\n"
        f"この操作のターゲットとなるUI要素の中心座標（ピクセル）を特定してください。\n"
        f"参考: 記録時の座標は ({test_case['coords']['x']}, {test_case['coords']['y']}) でした。\n\n"
        f"以下のJSON形式で回答してください（他のテキストは不要）:\n"
        f'{{"x": 数値, "y": 数値, "confidence": 0.0~1.0, "description": "見つけた要素の説明"}}'
    )

    start = time.time()
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime,
                            "data": img_data,
                        },
                    },
                    {
                        "type": "text",
                        "text": prompt,
                    },
                ],
            }],
        )
        elapsed = time.time() - start
        raw_text = response.content[0].text

        # JSON抽出
        import re
        json_match = re.search(r'\{[^}]+\}', raw_text)
        if json_match:
            result_data = json.loads(json_match.group())
            pred_x = result_data.get("x", 0)
            pred_y = result_data.get("y", 0)
            diff_x = abs(pred_x - test_case["coords"]["x"])
            diff_y = abs(pred_y - test_case["coords"]["y"])
            return {
                "method": "Vision AI (Haiku 4.5)",
                "status": "FOUND",
                "predicted": {"x": pred_x, "y": pred_y},
                "offset_from_original": {"dx": diff_x, "dy": diff_y},
                "confidence": result_data.get("confidence", 0),
                "ai_description": result_data.get("description", ""),
                "elapsed_sec": round(elapsed, 2),
                "usable_for_relocation": diff_x < 50 and diff_y < 50,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            }
        else:
            return {
                "method": "Vision AI (Haiku 4.5)",
                "status": "PARSE_ERROR",
                "raw_response": raw_text[:200],
                "elapsed_sec": round(elapsed, 2),
            }
    except Exception as e:
        return {
            "method": "Vision AI (Haiku 4.5)",
            "status": "ERROR",
            "reason": str(e)[:200],
            "elapsed_sec": round(time.time() - start, 2),
        }


def main():
    print("=" * 70)
    print("座標依存ステップ 要素検出精度テスト")
    print("=" * 70)

    all_results = []

    for tc in TEST_CASES:
        print(f"\n{'─' * 60}")
        print(f"[{tc['id']}] {tc['app']} — {tc['description']}")
        print(f"  座標: ({tc['coords']['x']}, {tc['coords']['y']})")
        print(f"  ターゲット: {tc['target']['role']} / {tc['target']['title']}")
        print(f"{'─' * 60}")

        results = {"test_case": tc["id"], "app": tc["app"], "description": tc["description"]}

        # 方法A: OCR
        print("  [A] OCR テスト中...", end=" ", flush=True)
        ocr_result = test_ocr(tc)
        print(f"→ {ocr_result['status']}")
        if ocr_result.get("nearby_texts_100px"):
            for t in ocr_result["nearby_texts_100px"][:3]:
                print(f"      テキスト: \"{t['text']}\" (距離: {t['distance']}px, 信頼度: {t['confidence']})")
        elif ocr_result.get("extended_texts_200px"):
            print(f"      100px以内にテキストなし。200px以内:")
            for t in ocr_result["extended_texts_200px"][:3]:
                print(f"      テキスト: \"{t['text']}\" (距離: {t['distance']}px)")
        results["ocr"] = ocr_result

        # 方法B: テンプレートマッチング
        print("  [B] テンプレートマッチング テスト中...", end=" ", flush=True)
        tmpl_result = test_template_matching(tc)
        print(f"→ score={tmpl_result.get('best_match', {}).get('score', 'N/A')}, "
              f"一意性={tmpl_result.get('uniqueness', 'N/A')}")
        results["template"] = tmpl_result

        # 方法C: Vision AI
        print("  [C] Vision AI テスト中...", end=" ", flush=True)
        vision_result = test_vision_ai(tc)
        print(f"→ {vision_result['status']}")
        if vision_result.get("predicted"):
            print(f"      予測座標: ({vision_result['predicted']['x']}, {vision_result['predicted']['y']})")
            print(f"      ずれ: dx={vision_result['offset_from_original']['dx']}, "
                  f"dy={vision_result['offset_from_original']['dy']}")
            print(f"      AI説明: {vision_result.get('ai_description', '')}")
        results["vision_ai"] = vision_result

        all_results.append(results)

    # サマリー
    print("\n" + "=" * 70)
    print("サマリー")
    print("=" * 70)
    print(f"{'TC':>4} {'アプリ':<15} {'OCR':>10} {'Template':>12} {'Vision AI':>12}")
    print("-" * 60)
    for r in all_results:
        ocr_ok = "○" if r["ocr"].get("usable_for_relocation") else "×"
        tmpl_ok = "○" if r["template"].get("usable_for_relocation") else "×"
        vis_ok = "○" if r["vision_ai"].get("usable_for_relocation") else "×"
        vis_status = r["vision_ai"]["status"]
        if vis_status == "SKIP":
            vis_ok = "SKIP"
        print(f"{r['test_case']:>4} {r['app']:<15} {ocr_ok:>10} {tmpl_ok:>12} {vis_ok:>12}")

    print("\n○ = 再配置に使用可能  × = 精度不足/検出失敗  SKIP = 実行不可")

    # コスト計算
    total_input_tokens = sum(
        r["vision_ai"].get("input_tokens", 0) for r in all_results
    )
    total_output_tokens = sum(
        r["vision_ai"].get("output_tokens", 0) for r in all_results
    )
    if total_input_tokens > 0:
        cost = total_input_tokens / 1_000_000 * 1.0 + total_output_tokens / 1_000_000 * 5.0
        print(f"\nVision AI コスト: 入力 {total_input_tokens:,} tokens + 出力 {total_output_tokens:,} tokens = ${cost:.4f}")

    # JSON出力
    output_path = BASE_DIR / "test_detection_results.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\n詳細結果: {output_path}")


if __name__ == "__main__":
    main()
