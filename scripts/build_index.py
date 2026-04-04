#!/usr/bin/env python3
"""
Build README dual index and generate docs/features/*.md pages.

Generated artifacts are deterministic (idempotent on unchanged inputs).
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DATE_ONLY_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})$")
DATE_SLUG_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")

MODULE_ORDER = [
    "工具属性",
    "设计与内容属性",
    "监控观测属性",
    "安全与风险属性",
    "流程自动化属性",
]


@dataclass(frozen=True)
class Task:
    task_id: str
    date: str
    title: str
    module: str
    archive_rel: str
    source_kind: str  # nightly-tools | nightly-sidequests
    task_dir: Path
    file_count: int


def parse_args() -> argparse.Namespace:
    script_path = Path(__file__).resolve()
    default_repo_root = script_path.parents[1]

    parser = argparse.ArgumentParser(description="Build README index + feature pages")
    parser.add_argument(
        "--repo-root",
        default=str(default_repo_root),
        help="Repository root (default: script parent repo)",
    )
    return parser.parse_args()


def is_date_only(name: str) -> bool:
    return bool(DATE_ONLY_RE.match(name))


def split_date_slug(name: str) -> tuple[str, str] | None:
    m = DATE_SLUG_RE.match(name)
    if not m:
        return None
    return m.group(1), m.group(2)


def slugify(text: str) -> str:
    s = text.strip().lower()
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "untitled"


def smart_title_from_slug(slug: str) -> str:
    parts = [p for p in slug.replace("_", "-").split("-") if p]
    if not parts:
        return "Untitled"
    return " ".join(p.upper() if len(p) <= 3 else p.capitalize() for p in parts)


def read_first_heading(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None


def read_first_paragraph(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    paragraph: list[str] = []
    started = False
    for line in lines:
        s = line.strip()
        if not started:
            if not s or s.startswith("#"):
                continue
            started = True
        if started:
            if not s:
                break
            if s.startswith("#"):
                break
            paragraph.append(s)

    if paragraph:
        return " ".join(paragraph)
    return None


def is_command_like(line: str) -> bool:
    s = line.strip()
    return bool(
        re.match(
            r"^(python3?|bash|sh|zsh|node|npm|pnpm|yarn|go|cargo|gh|curl|openclaw|\./)\b",
            s,
            flags=re.IGNORECASE,
        )
    )


def extract_usage_commands(readme_path: Path) -> list[str]:
    if not readme_path.exists():
        return []

    text = readme_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    commands: list[str] = []

    in_code = False
    for line in lines:
        stripped = line.rstrip()
        if stripped.startswith("```"):
            if not in_code:
                # opening block
                lang = stripped[3:].strip().lower()
                in_code = lang in {"", "bash", "shell", "sh", "zsh"}
            else:
                in_code = False
            continue

        if in_code:
            candidate = stripped.strip()
            if candidate and not candidate.startswith("#") and is_command_like(candidate):
                commands.append(candidate)

    # fallback: grep command-like lines outside code blocks
    if not commands:
        for line in lines:
            s = line.strip()
            if is_command_like(s):
                commands.append(s)

    # de-duplicate, keep order
    seen = set()
    uniq = []
    for c in commands:
        if c in seen:
            continue
        seen.add(c)
        uniq.append(c)
    return uniq[:8]


def classify_module(task_id: str, title: str, summary: str) -> str:
    text = f"{task_id} {title} {summary}".lower()

    def has_any(words: Iterable[str]) -> bool:
        return any(w in text for w in words)

    if has_any(["vuln", "security", "audit", "assumption", "risk", "killjoy", "scanner"]):
        return "安全与风险属性"
    if has_any(["tone", "voice", "brand", "copy", "design", "vibe"]):
        return "设计与内容属性"
    if has_any(["status", "health", "log", "monitor", "inspector", "lens", "glance", "digest", "pulse"]):
        return "监控观测属性"
    if has_any(["workflow", "cron", "pipeline", "orchestr", "api tester", "tracker", "automation"]):
        return "流程自动化属性"
    return "工具属性"


def list_files_for_page(task_dir: Path) -> list[str]:
    out = []
    for p in sorted(task_dir.rglob("*")):
        if p.is_dir():
            continue
        if "__pycache__" in p.parts:
            continue
        if p.suffix in {".pyc", ".pyo"}:
            continue
        out.append(str(p.relative_to(task_dir)))
    return out


def detect_tasks(repo_root: Path) -> list[Task]:
    tasks: list[Task] = []
    archive_root = repo_root / "archive"

    for source_kind in ["nightly-tools", "nightly-sidequests"]:
        base = archive_root / source_kind
        if not base.exists():
            continue

        # Top-level directories
        for top in sorted([p for p in base.iterdir() if p.is_dir()]):
            top_name = top.name
            date_slug = split_date_slug(top_name)

            # 1) canonical: YYYY-MM-DD-xxx
            if date_slug:
                date, _slug = date_slug
                readme = top / "README.md"
                title = read_first_heading(readme) or smart_title_from_slug(_slug)
                summary = read_first_paragraph(readme) or f"归档任务 {top_name}。"
                module = classify_module(top_name, title, summary)
                file_count = len(list_files_for_page(top))
                tasks.append(
                    Task(
                        task_id=top_name,
                        date=date,
                        title=title,
                        module=module,
                        archive_rel=str(top.relative_to(repo_root)).replace("\\", "/"),
                        source_kind=source_kind,
                        task_dir=top,
                        file_count=file_count,
                    )
                )
                continue

            # 2) special: YYYY-MM-DD (report folder + nested sub tasks)
            if is_date_only(top_name):
                date = top_name

                # 2a) files directly under date folder -> one report task
                top_files = [p for p in top.iterdir() if p.is_file()]
                if top_files:
                    task_id = f"{date}-report"
                    first_md = next((p for p in sorted(top_files) if p.suffix.lower() == ".md"), None)
                    title = read_first_heading(first_md) if first_md else None
                    if not title:
                        title = f"{date} Report"
                    summary = read_first_paragraph(first_md) if first_md else None
                    if not summary:
                        summary = f"日期目录 {date} 的直接产出汇总。"
                    module = classify_module(task_id, title, summary)
                    file_count = len(list_files_for_page(top))
                    tasks.append(
                        Task(
                            task_id=task_id,
                            date=date,
                            title=title,
                            module=module,
                            archive_rel=str(top.relative_to(repo_root)).replace("\\", "/"),
                            source_kind=source_kind,
                            task_dir=top,
                            file_count=file_count,
                        )
                    )

                # 2b) nested directories under date folder
                for sub in sorted([p for p in top.iterdir() if p.is_dir()]):
                    sub_slug = slugify(sub.name)
                    readme = sub / "README.md"
                    readme_title = read_first_heading(readme)
                    title = readme_title or smart_title_from_slug(sub.name)

                    suffix = sub_slug
                    if readme_title:
                        title_slug = slugify(readme_title)
                        if title_slug and title_slug not in sub_slug:
                            suffix = f"{sub_slug}-{title_slug}"

                    task_id = f"{date}-{suffix}"
                    summary = read_first_paragraph(readme) or f"归档任务 {task_id}。"
                    module = classify_module(task_id, title, summary)
                    file_count = len(list_files_for_page(sub))
                    tasks.append(
                        Task(
                            task_id=task_id,
                            date=date,
                            title=title,
                            module=module,
                            archive_rel=str(sub.relative_to(repo_root)).replace("\\", "/"),
                            source_kind=source_kind,
                            task_dir=sub,
                            file_count=file_count,
                        )
                    )

    # de-duplicate by task_id (prefer longer archive path if collision)
    dedup: dict[str, Task] = {}
    for t in tasks:
        prev = dedup.get(t.task_id)
        if not prev:
            dedup[t.task_id] = t
            continue
        if len(t.archive_rel) > len(prev.archive_rel):
            dedup[t.task_id] = t

    return sorted(dedup.values(), key=lambda x: (x.date, x.task_id), reverse=True)


def write_text_if_changed(path: Path, content: str) -> bool:
    old = path.read_text(encoding="utf-8") if path.exists() else None
    if old == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def build_feature_page(repo_root: Path, task: Task) -> str:
    readme = task.task_dir / "README.md"
    summary = read_first_paragraph(readme) or f"自动归档任务 `{task.task_id}`。"
    usage_commands = extract_usage_commands(readme)
    files = list_files_for_page(task.task_dir)

    if task.file_count == 0:
        status = "🟡 占位（目录为空，待补充）"
        output = "当前目录无文件产出。"
    else:
        status = "✅ 已归档（自动生成）"
        output = f"已归档文件数：`{task.file_count}`。"

    suggestions = [
        "补充更清晰的输入/输出示例，降低接手成本。",
        "增加自动化测试或最小 smoke 命令，提升可回归性。",
        "根据实际使用频次，评估是否需要接入 CI 定时巡检。",
    ]

    lines: list[str] = []
    lines.append(f"# {task.title}")
    lines.append("")
    lines.append(f"- 日期：`{task.date}`")
    lines.append(f"- 模块：`{task.module}`")
    lines.append(f"- 来源：`{task.archive_rel}`")
    lines.append("")

    lines.append("## 功能简介")
    lines.append(summary)
    lines.append("")

    lines.append("## 背景/目的")
    lines.append(f"该页面用于沉淀 `{task.task_id}` 的用途、运行方式和交付状态，避免夜间任务信息散落。")
    lines.append("")

    lines.append("## 目录与文件")
    lines.append(f"- 根目录：`{task.archive_rel}`")
    if files:
        lines.append("- 文件列表：")
        for f in files[:200]:
            lines.append(f"  - `{f}`")
    else:
        lines.append("- 当前目录暂无文件。")
    lines.append("")

    lines.append("## 用法/测试方法")
    if usage_commands:
        lines.append("```bash")
        for cmd in usage_commands:
            lines.append(cmd)
        lines.append("```")
    else:
        lines.append("- 暂无 README 命令示例，可按目录内脚本名补充。")
    lines.append("")

    lines.append("## 产出与状态")
    lines.append(f"- 产出：{output}")
    lines.append(f"- 状态：{status}")
    lines.append("")

    lines.append("## 后续迭代建议")
    for s in suggestions:
        lines.append(f"- {s}")
    lines.append("")

    return "\n".join(lines)


def build_readme(repo_root: Path, tasks: list[Task]) -> str:
    by_date: dict[str, list[Task]] = {}
    by_module: dict[str, list[Task]] = {m: [] for m in MODULE_ORDER}

    for t in tasks:
        by_date.setdefault(t.date, []).append(t)
        if t.module not in by_module:
            by_module[t.module] = []
        by_module[t.module].append(t)

    for k in by_date:
        by_date[k] = sorted(by_date[k], key=lambda x: x.task_id)
    for k in by_module:
        by_module[k] = sorted(by_module[k], key=lambda x: (x.date, x.task_id), reverse=True)

    lines: list[str] = []
    lines.append("# Nightly Tasks Collection")
    lines.append("")
    lines.append("自动收录 nightly-tools 与 nightly-sidequests 产物，并维护双索引导航。")
    lines.append("")
    lines.append("## 覆盖范围")
    if tasks:
        dates = sorted({t.date for t in tasks})
        lines.append(f"- 时间：`{dates[0]}` ~ `{dates[-1]}`")
    else:
        lines.append("- 时间：`N/A`")
    lines.append("- 来源：`nightly-tools` + `nightly-sidequests`")
    lines.append(f"- 功能页数量：`{len(tasks)}`")
    lines.append("")

    lines.append("## 导航 A：按日期（新->旧）")
    for date in sorted(by_date.keys(), reverse=True):
        lines.append(f"### {date}")
        for t in by_date[date]:
            lines.append(f"- [{t.title}](docs/features/{t.task_id}.md)  `[{t.module}]`")
        lines.append("")

    lines.append("## 导航 B：按功能模块")
    for module in MODULE_ORDER + [m for m in by_module.keys() if m not in MODULE_ORDER]:
        if module not in by_module or not by_module[module]:
            continue
        lines.append(f"### {module}")
        for t in by_module[module]:
            lines.append(f"- [{t.title}](docs/features/{t.task_id}.md)  `[{t.date}]`")
        lines.append("")

    lines.append("## README 首页导航（目录树 + 链接）")
    lines.append("```text")
    lines.append("nightly-task-collection/")
    lines.append("├── README.md")
    lines.append("├── scripts/")
    lines.append("│   ├── sync_nightly.py")
    lines.append("│   └── build_index.py")
    lines.append("├── docs/")
    lines.append("│   └── features/")
    for t in sorted(tasks, key=lambda x: x.task_id, reverse=True):
        lines.append(f"│       ├── {t.task_id}.md")
    lines.append("├── archive/")
    lines.append("│   ├── nightly-tools/")
    lines.append("│   └── nightly-sidequests/")
    lines.append("└── .github/workflows/nightly-sync-index.yml")
    lines.append("```")
    lines.append("")

    lines.append("## 自动化维护")
    lines.append("- 同步：`python3 scripts/sync_nightly.py --source-root /root/.openclaw/workspace --repo-root .`")
    lines.append("- 重建索引：`python3 scripts/build_index.py --repo-root .`")
    lines.append("- Actions：`.github/workflows/nightly-sync-index.yml`（定时 + 手动）")
    lines.append("")

    lines.append("## 信息架构说明（IA）")
    lines.append("1. 双索引并行：日期索引追踪时间线；模块索引支持能力复用。")
    lines.append("2. 功能页独立：每个任务固定 6 段结构，便于审计与自动更新。")
    lines.append("3. 文档与产物分层：`docs/` 放说明，`archive/` 放原始产物。")
    lines.append("4. 占位显式化：空目录任务也生成页面并标注状态，避免遗漏。")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).expanduser().resolve()

    tasks = detect_tasks(repo_root)
    features_dir = repo_root / "docs" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)

    generated_names: set[str] = set()
    changed_pages = 0

    for task in tasks:
        page_path = features_dir / f"{task.task_id}.md"
        generated_names.add(page_path.name)
        content = build_feature_page(repo_root, task)
        if write_text_if_changed(page_path, content):
            changed_pages += 1

    # Remove stale feature pages
    removed_pages = 0
    for old_page in sorted(features_dir.glob("*.md")):
        if old_page.name in generated_names:
            continue
        old_page.unlink()
        removed_pages += 1

    readme_content = build_readme(repo_root, tasks)
    readme_changed = write_text_if_changed(repo_root / "README.md", readme_content)

    print("== build_index ==")
    print(f"repo_root:       {repo_root}")
    print(f"tasks_detected:  {len(tasks)}")
    print(f"pages_changed:   {changed_pages}")
    print(f"pages_removed:   {removed_pages}")
    print(f"readme_changed:  {readme_changed}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
