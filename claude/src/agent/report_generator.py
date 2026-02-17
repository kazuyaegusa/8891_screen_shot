"""
再現性レポート + 業務パーツカタログ生成モジュール

【使用方法】
from agent.report_generator import ReportGenerator
from agent.workflow_store import WorkflowStore
from agent.feedback_store import FeedbackStore

store = WorkflowStore("./workflows")
feedback = FeedbackStore("./workflows/feedback")
gen = ReportGenerator(store, feedback)

# Markdownレポート生成
md = gen.generate(format="markdown")

# JSONレポート
js = gen.generate(format="json")

# カテゴリフィルタ
md = gen.generate(format="markdown", category="開発")

# catalog.json更新
path = gen.update_catalog()

【処理内容】
- 各ワークフローの再現性をA/B/Cランクで評価（AI不要・ローカル即時実行）
- ルールベースで業務カテゴリに分類
- Markdown/JSONレポートを生成
- catalog.json（パーツインデックス）を更新

【依存】
agent.workflow_store, agent.feedback_store, agent.models, json, pathlib, datetime
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.feedback_store import FeedbackStore
from agent.models import ActionStep, Workflow
from agent.workflow_store import WorkflowStore

logger = logging.getLogger(__name__)

# アプリAX対応度
_AX_COMPATIBILITY: Dict[str, float] = {
    "Finder": 0.95,
    "Safari": 0.90,
    "Google Chrome": 0.85,
    "Firefox": 0.85,
    "Arc": 0.80,
    "Cursor": 0.80,
    "Code": 0.80,
    "Visual Studio Code": 0.80,
    "Terminal": 0.75,
    "iTerm2": 0.75,
    "Ghostty": 0.60,
    "Notion": 0.70,
    "Slack": 0.65,
    "Discord": 0.40,
    "LINE": 0.50,
    "Messages": 0.70,
    "Mail": 0.80,
    "System Preferences": 0.90,
    "System Settings": 0.90,
}

# 業務カテゴリルール
CATEGORY_RULES: Dict[str, Dict[str, Any]] = {
    "開発": {
        "apps": ["Cursor", "Code", "Visual Studio Code", "Ghostty", "Terminal", "iTerm2", "Xcode"],
        "tags": ["開発", "コーディング", "ビルド", "デバッグ", "git"],
    },
    "コミュニケーション": {
        "apps": ["LINE", "Discord", "Slack", "Mail", "Messages", "メール", "Zoom", "Teams"],
        "tags": ["チャット", "メール", "通話", "会議"],
    },
    "ブラウザ/Web": {
        "apps": ["Google Chrome", "Safari", "Firefox", "Arc"],
        "tags": ["ブラウザ", "Web", "検索"],
    },
    "AI/LLM": {
        "apps": ["Claude", "Google Gemini", "ChatGPT"],
        "tags": ["AI", "LLM", "GPT", "Gemini", "Claude"],
    },
    "システム操作": {
        "apps": ["Finder", "System Preferences", "System Settings", "Activity Monitor"],
        "tags": ["Finder", "システム", "設定"],
    },
    "プロジェクト管理": {
        "apps": ["Linear", "Notion", "Jira", "Asana", "Trello"],
        "tags": ["タスク管理", "プロジェクト", "チケット"],
    },
}


class ReportGenerator:
    """再現性レポート + 業務パーツカタログ生成"""

    def __init__(self, store: WorkflowStore, feedback: FeedbackStore):
        self._store = store
        self._feedback = feedback

    def generate(self, format: str = "markdown", category: Optional[str] = None) -> str:
        """レポート生成（markdown または json）"""
        workflows = self._store.list_all()
        categorized_all = self._categorize_all(workflows)

        # catalog.json は常に全カテゴリで更新
        self._write_catalog(workflows, categorized_all)

        # レポート表示用はカテゴリフィルタ適用
        categorized = categorized_all
        if category:
            categorized = {k: v for k, v in categorized.items() if k == category}

        evaluated: Dict[str, list] = {}
        for cat, wfs in categorized.items():
            evaluated[cat] = []
            for wf in wfs:
                success_rate = self._feedback.get_success_rate(wf.workflow_id)
                repro = self._evaluate_reproducibility(wf, success_rate)
                evaluated[cat].append({
                    "workflow": wf,
                    "reproducibility": repro,
                    "success_rate": success_rate,
                })

        stats = self._calc_stats(evaluated)

        if format == "json":
            return self._render_json(evaluated, stats)
        return self._render_markdown(evaluated, stats)

    def update_catalog(self) -> str:
        """catalog.json を更新して保存パスを返す"""
        workflows = self._store.list_all()
        categorized = self._categorize_all(workflows)
        return self._write_catalog(workflows, categorized)

    def get_by_category(self, category: str) -> List[Workflow]:
        """カテゴリ別にワークフロー取得"""
        workflows = self._store.list_all()
        return [wf for wf in workflows if self._classify_category(wf) == category]

    # --- 内部メソッド ---

    def _write_catalog(self, workflows: List[Workflow], categorized: Dict[str, List[Workflow]]) -> str:
        """catalog.json 書き出し"""
        catalog: Dict[str, Any] = {
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "categories": {},
            "stats": {"total": len(workflows), "by_rank": {"A": 0, "B": 0, "C": 0}},
        }

        for cat, wfs in categorized.items():
            items = []
            for wf in wfs:
                success_rate = self._feedback.get_success_rate(wf.workflow_id)
                repro = self._evaluate_reproducibility(wf, success_rate)
                catalog["stats"]["by_rank"][repro["rank"]] += 1
                items.append({
                    "workflow_id": wf.workflow_id,
                    "name": wf.name,
                    "app_name": wf.app_name,
                    "reproducibility": {
                        "score": round(repro["score"], 2),
                        "rank": repro["rank"],
                    },
                    "steps_count": len(wf.steps),
                })
            catalog["categories"][cat] = {"workflows": items}

        parts_dir = Path(self._store._dir) / "parts"
        parts_dir.mkdir(parents=True, exist_ok=True)
        path = parts_dir / "catalog.json"
        path.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("カタログ更新: %s", path)
        return str(path)

    def _categorize_all(self, workflows: List[Workflow]) -> Dict[str, List[Workflow]]:
        """全ワークフローをカテゴリ別に分類"""
        result: Dict[str, List[Workflow]] = {}
        for wf in workflows:
            cat = self._classify_category(wf)
            result.setdefault(cat, []).append(wf)
        return result

    def _classify_category(self, wf: Workflow) -> str:
        """ルールベースでカテゴリ分類（app_name → tags の順でマッチ）"""
        for cat, rules in CATEGORY_RULES.items():
            if wf.app_name in rules["apps"]:
                return cat

        wf_tags_lower = [t.lower() for t in wf.tags]
        for cat, rules in CATEGORY_RULES.items():
            for tag in rules.get("tags", []):
                if tag.lower() in wf_tags_lower:
                    return cat

        return "その他"

    def _evaluate_reproducibility(self, wf: Workflow, success_rate: float) -> Dict[str, Any]:
        """再現性スコア算出

        score = confidence × 0.30
              + success_rate × 0.30  （実行データなし=0.15）
              + step_quality × 0.25
              + ax_compatibility × 0.15
        """
        has_feedback = len(self._feedback.get_by_workflow(wf.workflow_id)) > 0
        effective_sr = success_rate if has_feedback else 0.15

        step_quality = self._calc_step_quality(wf.steps) if wf.steps else 0.0
        ax_compat = self._calc_ax_compatibility(wf.app_name, wf.steps)

        score = (
            wf.confidence * 0.30
            + effective_sr * 0.30
            + step_quality * 0.25
            + ax_compat * 0.15
        )

        if score >= 0.7:
            rank = "A"
        elif score >= 0.4:
            rank = "B"
        else:
            rank = "C"

        return {
            "score": score,
            "rank": rank,
            "detail": {
                "confidence": wf.confidence,
                "success_rate": effective_sr,
                "step_quality": round(step_quality, 3),
                "ax_compatibility": round(ax_compat, 3),
            },
        }

    def _calc_step_quality(self, steps: List[ActionStep]) -> float:
        """ステップ品質スコア算出"""
        if not steps:
            return 0.0
        scores = []
        for step in steps:
            if step.action_type == "key_shortcut":
                scores.append(0.95)
            elif step.action_type == "text_input":
                scores.append(0.80)
            elif step.action_type in ("click", "right_click"):
                if step.target_identifier:
                    scores.append(0.90)
                elif step.target_role and step.target_title:
                    scores.append(0.70)
                else:
                    scores.append(0.30)
            else:
                scores.append(0.50)
        return sum(scores) / len(scores)

    def _calc_ax_compatibility(self, app_name: str, steps: List[ActionStep]) -> float:
        """アプリAX対応度算出"""
        if app_name in _AX_COMPATIBILITY:
            return _AX_COMPATIBILITY[app_name]
        # 未知アプリ: ステップのtarget情報充実度から推定
        if not steps:
            return 0.50
        has_target = sum(
            1 for s in steps
            if s.target_identifier or s.target_role or s.target_title
        )
        return 0.40 + (has_target / len(steps)) * 0.40

    def _calc_stats(self, evaluated: Dict[str, list]) -> Dict[str, Any]:
        """統計情報算出"""
        total = 0
        by_rank: Dict[str, int] = {"A": 0, "B": 0, "C": 0}
        for items in evaluated.values():
            for item in items:
                total += 1
                by_rank[item["reproducibility"]["rank"]] += 1
        return {"total": total, "by_rank": by_rank, "categories": len(evaluated)}

    def _render_markdown(self, evaluated: Dict[str, list], stats: Dict[str, Any]) -> str:
        """Markdownレポート生成"""
        lines: List[str] = []
        now = datetime.now().strftime("%Y-%m-%d %H:%M")

        lines.append(f"# 再現性レポート ({now})")
        lines.append("")
        lines.append("## サマリー")
        lines.append("")
        lines.append(f"- 総ワークフロー数: {stats['total']}")
        lines.append(f"- カテゴリ数: {stats['categories']}")
        lines.append(f"- ランク A（再現可能）: {stats['by_rank']['A']}")
        lines.append(f"- ランク B（要検証）: {stats['by_rank']['B']}")
        lines.append(f"- ランク C（再現困難）: {stats['by_rank']['C']}")
        lines.append("")

        rank_icon = {"A": "●", "B": "▲", "C": "×"}

        for cat in sorted(evaluated.keys()):
            items = evaluated[cat]
            lines.append(f"## {cat} ({len(items)}件)")
            lines.append("")
            lines.append("| ランク | ワークフロー | アプリ | スコア | ステップ数 | ステータス |")
            lines.append("|--------|------------|-------|--------|-----------|-----------|")

            items_sorted = sorted(
                items, key=lambda x: x["reproducibility"]["score"], reverse=True
            )
            for item in items_sorted:
                wf = item["workflow"]
                repro = item["reproducibility"]
                icon = rank_icon[repro["rank"]]
                lines.append(
                    f"| {icon} {repro['rank']} | {wf.name} | {wf.app_name} | "
                    f"{repro['score']:.2f} | {len(wf.steps)} | {wf.status} |"
                )
            lines.append("")

        return "\n".join(lines)

    def _render_json(self, evaluated: Dict[str, list], stats: Dict[str, Any]) -> str:
        """JSONレポート生成"""
        data: Dict[str, Any] = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "stats": stats,
            "categories": {},
        }
        for cat, items in evaluated.items():
            cat_data = []
            for item in items:
                wf = item["workflow"]
                cat_data.append({
                    "workflow_id": wf.workflow_id,
                    "name": wf.name,
                    "app_name": wf.app_name,
                    "status": wf.status,
                    "steps_count": len(wf.steps),
                    "reproducibility": {
                        "score": round(item["reproducibility"]["score"], 2),
                        "rank": item["reproducibility"]["rank"],
                        "detail": item["reproducibility"]["detail"],
                    },
                })
            data["categories"][cat] = cat_data
        return json.dumps(data, ensure_ascii=False, indent=2)
