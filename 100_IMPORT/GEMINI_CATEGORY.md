# category_abstractor.py
# -*- coding: utf-8 -*-
"""
カテゴリを抽象化してJSONで返すツール
- 依存: なし（標準ライブラリのみ）
- 使い方:
    from category_abstractor import abstract_registry
    data = abstract_registry(categories_data, locale="ja-JP", active_only=True)
"""

from __future__ import annotations
import json
from typing import Any, Dict, Iterable, List, Optional, Set


# ---- 抽象化ロジック ----
DEFAULT_FIELDS: List[str] = [
    "id",
    "code",
    "name",
    "description",
    "parent_id",
    "status",
    "tags",
    "aliases",
]

def _pick_locale_text(d: Any, locale: str, fallback_keys: Iterable[str] = ("ja-JP", "en")) -> Optional[str]:
    """
    names/description のような多言語辞書から優先ロケール→フォールバックの順で1つ選ぶ。
    """
    if not isinstance(d, dict):
        # 既に文字列ならそのまま返す（柔軟対応）
        return d if isinstance(d, str) else None
    if locale in d and isinstance(d[locale], str):
        return d[locale]
    for k in fallback_keys:
        if k in d and isinstance(d[k], str):
            return d[k]
    # 先頭の文字列値があればそれ
    for v in d.values():
        if isinstance(v, str):
            return v
    return None


def _abstract_category(raw: Dict[str, Any], locale: str, fields: Set[str]) -> Dict[str, Any]:
    """
    1カテゴリを抽象化（最小限・ベンダ非依存）へ正規化。
    - code が無い場合は id を流用
    - name/description はロケール優先で抽出
    - そのほかは存在すれば通す
    """
    abstract: Dict[str, Any] = {}
    # 必須系
    cid = raw.get("id") or raw.get("code")  # id が無ければ code をid扱い
    code = raw.get("code") or cid

    # 多言語から name/description を抽出
    name = _pick_locale_text(raw.get("names"), locale)
    description = _pick_locale_text(raw.get("description"), locale)

    # 共通フィールド候補
    candidate = {
        "id": cid,
        "code": code,
        "name": name,
        "description": description,
        "parent_id": raw.get("parent_id"),
        "status": raw.get("status", "active"),
        "tags": raw.get("tags", []),
        "aliases": raw.get("aliases", []),
    }

    # 指定 fields のみ残す
    for k, v in candidate.items():
        if k in fields:
            abstract[k] = v
    return abstract


def abstract_registry(
    registry: Dict[str, Any],
    *,
    locale: str = "ja-JP",
    active_only: bool = False,
    ids: Optional[Iterable[str]] = None,
    fields: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """
    レジストリ全体を抽象化した JSON オブジェクトにして返す。
    - locale: 表示ロケール（names/description の抽出に利用）
    - active_only: true の場合、status != "active" を除外
    - ids: 指定があれば該当 id/code のみ抽出
    - fields: 返却フィールドを制限（未指定は DEFAULT_FIELDS）
    """
    if "categories" not in registry or not isinstance(registry["categories"], list):
        raise ValueError("Invalid registry: 'categories' array is required")

    field_set: Set[str] = set(fields or DEFAULT_FIELDS)
    id_filter: Optional[Set[str]] = set(x.strip() for x in ids) if ids else None

    abstracted: List[Dict[str, Any]] = []
    for raw in registry["categories"]:
        if active_only and raw.get("status", "active") != "active":
            continue

        # id/code でフィルタ
        if id_filter:
            raw_id = raw.get("id") or raw.get("code")
            raw_code = raw.get("code")
            if raw_id not in id_filter and raw_code not in id_filter:
                continue

        abstracted.append(_abstract_category(raw, locale, field_set))

    # メタは最小限のみ継承（無ければ生成）
    src_meta = registry.get("meta", {})
    meta_out = {
        "id": src_meta.get("id", "categories.abstract"),
        "version": src_meta.get("version", "1.0.0"),
        "locale": locale,
        "generated_by": "category_abstractor.py",
    }

    return {"meta": meta_out, "categories": abstracted}