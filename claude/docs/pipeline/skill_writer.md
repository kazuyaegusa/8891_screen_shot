# skill_writer.py ドキュメント

対応ソース: `claude/src/pipeline/skill_writer.py`

## 概要

抽出されたスキルを YAML frontmatter + Markdown body 形式の SKILL.md ファイルとして書き出すモジュール。
`~/.claude/skills/` 配下にスキルごとのディレクトリを作成し、`_index.md` の自動生成スキルセクションも更新する。

## クラス

### `SkillWriter`

#### コンストラクタ

```python
SkillWriter(skills_dir: Path)
```

| 項目 | 内容 |
|------|------|
| **入力** | `skills_dir`: スキル保存先ディレクトリ（例: `~/.claude/skills`） |

#### `write_skill(skill: ExtractedSkill) -> Path`

スキルを SKILL.md として新規作成する。

| 項目 | 内容 |
|------|------|
| **入力** | `skill`: ExtractedSkill オブジェクト |
| **出力** | 書き出した SKILL.md の Path |

- `skills_dir / skill.name / SKILL.md` に保存
- ディレクトリが存在しない場合は自動作成
- 保存後に `_index.md` を更新

#### `update_skill(skill: ExtractedSkill) -> Path`

既存スキルを上書き更新する。内部的には `write_skill()` と同一動作。

| 項目 | 内容 |
|------|------|
| **入力** | `skill`: ExtractedSkill オブジェクト |
| **出力** | 書き出した SKILL.md の Path |

#### `skill_exists(name: str) -> bool`

指定名のスキルが既に存在するか確認する。

| 項目 | 内容 |
|------|------|
| **入力** | `name`: スキル名 |
| **出力** | `True`（存在する場合）/ `False` |

- `skills_dir / name / SKILL.md` の存在をチェック

## SKILL.md 出力フォーマット

```markdown
---
name: ファイル整理
description: Finderでファイルをフォルダに移動する操作
app: Finder
triggers:
  - ファイル移動
  - 整理
confidence: 0.85
auto_generated: true
generated_at: 2026-02-16T00:00:00+00:00
---

# ファイル整理

Finderでファイルをフォルダに移動する操作

## 手順

1. フォルダを開く
2. ファイルをドラッグ
```

## _index.md 更新

`write_skill()` 実行時に `_index.md` の自動生成セクションを更新する。

- マーカー: `<!-- auto-generated-skills-start -->` 〜 `<!-- auto-generated-skills-end -->`
- マーカーが既存の場合は該当セクションを置換
- マーカーがない場合は末尾に追記
- `_index.md` が存在しない場合は新規作成

### 内部メソッド

- `_render(skill)`: ExtractedSkill を YAML frontmatter + Markdown に変換
- `_update_index()`: 全自動生成スキルを収集して `_index.md` を更新
- `_collect_auto_skills()`: `skills_dir` 配下の `auto_generated: true` なスキルを収集

## 依存ライブラリ

- Python標準ライブラリ (pathlib, datetime, re)
- pipeline.models (ExtractedSkill)
