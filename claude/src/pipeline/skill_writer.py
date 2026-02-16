"""
スキルファイル書き出しモジュール

【使用方法】
from pathlib import Path
from pipeline.skill_writer import SkillWriter
from pipeline.models import ExtractedSkill

writer = SkillWriter(skills_dir=Path.home() / ".claude" / "skills")

skill = ExtractedSkill(
    name="ファイル整理",
    description="Finderでファイルをフォルダに移動する操作",
    steps=["フォルダを開く", "ファイルをドラッグ"],
    app="Finder",
    triggers=["ファイル移動", "整理"],
    confidence=0.85,
)

# 新規作成
path = writer.write_skill(skill)

# 既存更新（上書き）
path = writer.update_skill(skill)

# 存在確認
exists = writer.skill_exists("ファイル整理")

【処理内容】
1. ExtractedSkill を YAML frontmatter + Markdown body 形式で SKILL.md に書き出す
2. skills_dir / skill.name / SKILL.md のパスに保存
3. _index.md を更新して自動生成スキル一覧を追記

【依存】
Python標準ライブラリ (pathlib, datetime, re), pipeline.models
"""

import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from pipeline.models import ExtractedSkill

logger = logging.getLogger(__name__)


class SkillWriter:
    def __init__(self, skills_dir: Path):
        self._skills_dir = skills_dir

    def write_skill(self, skill: ExtractedSkill) -> Path:
        skill_dir = self._skills_dir / skill.name
        skill_dir.mkdir(parents=True, exist_ok=True)
        path = skill_dir / "SKILL.md"
        path.write_text(self._render(skill), encoding="utf-8")
        logger.info("スキル '%s' を書き出し: %s", skill.name, path)
        self._update_index()
        return path

    def update_skill(self, skill: ExtractedSkill) -> Path:
        return self.write_skill(skill)

    def skill_exists(self, name: str) -> bool:
        return (self._skills_dir / name / "SKILL.md").exists()

    def _render(self, skill: ExtractedSkill) -> str:
        triggers_yaml = "\n".join(f"  - {t}" for t in skill.triggers)
        steps_md = "\n".join(f"{i}. {s}" for i, s in enumerate(skill.steps, 1))
        now = datetime.now(timezone.utc).isoformat()

        return (
            f"---\n"
            f"name: {skill.name}\n"
            f"description: {skill.description}\n"
            f"app: {skill.app}\n"
            f"triggers:\n{triggers_yaml}\n"
            f"confidence: {skill.confidence}\n"
            f"auto_generated: true\n"
            f"generated_at: {now}\n"
            f"---\n"
            f"\n"
            f"# {skill.name}\n"
            f"\n"
            f"{skill.description}\n"
            f"\n"
            f"## 手順\n"
            f"\n"
            f"{steps_md}\n"
        )

    def _update_index(self) -> None:
        index_path = self._skills_dir / "_index.md"
        auto_skills = self._collect_auto_skills()
        if not auto_skills:
            return

        section = _build_auto_section(auto_skills)

        if index_path.exists():
            content = index_path.read_text(encoding="utf-8")
            content = _replace_auto_section(content, section)
        else:
            content = f"# Skills Index\n\n{section}\n"

        index_path.write_text(content, encoding="utf-8")

    def _collect_auto_skills(self) -> List[dict]:
        results = []
        if not self._skills_dir.exists():
            return results
        for skill_md in sorted(self._skills_dir.glob("*/SKILL.md")):
            text = skill_md.read_text(encoding="utf-8")
            if "auto_generated: true" not in text:
                continue
            name = skill_md.parent.name
            desc = ""
            for line in text.splitlines():
                if line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip()
                    break
            results.append({"name": name, "description": desc})
        return results


_AUTO_MARKER_START = "<!-- auto-generated-skills-start -->"
_AUTO_MARKER_END = "<!-- auto-generated-skills-end -->"


def _build_auto_section(skills: List[dict]) -> str:
    lines = [_AUTO_MARKER_START, "## 自動生成スキル", ""]
    for s in skills:
        lines.append(f"- **{s['name']}**: {s['description']}")
    lines.append("")
    lines.append(_AUTO_MARKER_END)
    return "\n".join(lines)


def _replace_auto_section(content: str, section: str) -> str:
    pattern = re.escape(_AUTO_MARKER_START) + r".*?" + re.escape(_AUTO_MARKER_END)
    if re.search(pattern, content, re.DOTALL):
        return re.sub(pattern, section, content, flags=re.DOTALL)
    return content.rstrip() + "\n\n" + section + "\n"
