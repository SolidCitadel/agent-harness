#!/usr/bin/env python3
"""Render platform global instructions into platform-owned document structures."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


TARGETS = {
    Path("codex/AGENTS.md"): Path("codex/AGENTS.template.md"),
    Path("claude/CLAUDE.md"): Path("claude/CLAUDE.template.md"),
}
TOKEN = re.compile(r"\{\{shared:([^{}]+)\}\}")


def parse_sections(source: str) -> dict[str, str]:
    normalized = source.replace("\r\n", "\n")
    lines = normalized.splitlines()
    if not lines or lines[0] != "# 공통 전역 지침":
        raise ValueError("shared/global-instructions.md의 제목이 올바르지 않습니다.")

    sections: dict[str, str] = {}
    matches = list(re.finditer(r"(?m)^## ([^\n]+)(?:\n|$)", normalized))
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        if name in sections:
            raise ValueError(f"공통 전역 지침의 섹션이 중복됩니다: {name}")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        body = normalized[match.end():end]
        subsections = list(re.finditer(r"(?m)^### ([^\n]+)(?:\n|$)", body))
        parent_body = body[:subsections[0].start()].strip() if subsections else body.strip()
        sections[name] = f"## {name}\n\n{parent_body}" if parent_body else f"## {name}"
        for child_index, child in enumerate(subsections):
            child_name = child.group(1).strip()
            key = f"{name}/{child_name}"
            if key in sections:
                raise ValueError(f"공통 전역 지침의 하위 섹션이 중복됩니다: {key}")
            child_end = subsections[child_index + 1].start() if child_index + 1 < len(subsections) else len(body)
            child_body = body[child.end():child_end].strip()
            sections[key] = f"### {child_name}\n\n{child_body}" if child_body else f"### {child_name}"

    if not sections:
        raise ValueError("shared/global-instructions.md에 공통 섹션이 없습니다.")
    return sections


def rendered(template: str, sections: dict[str, str], template_path: Path) -> str:
    normalized = template.replace("\r\n", "\n")
    names = TOKEN.findall(normalized)
    unknown = sorted(set(names) - set(sections))
    missing = sorted(set(sections) - set(names))
    repeated = sorted(name for name in set(names) if names.count(name) != 1)
    if unknown:
        raise ValueError(f"{template_path}의 알 수 없는 공통 섹션: {', '.join(unknown)}")
    if missing:
        raise ValueError(f"{template_path}에서 누락된 공통 섹션: {', '.join(missing)}")
    if repeated:
        raise ValueError(f"{template_path}에서 중복된 공통 섹션: {', '.join(repeated)}")

    for name in sections:
        if "/" not in name:
            continue
        parent = name.split("/", 1)[0]
        parent_token = f"{{{{shared:{parent}}}}}"
        child_token = f"{{{{shared:{name}}}}}"
        parent_at = normalized.index(parent_token)
        child_at = normalized.index(child_token)
        between = normalized[parent_at + len(parent_token):child_at]
        if parent_at >= child_at or re.search(r"(?m)^## ", between) or any(
            "/" not in other for other in TOKEN.findall(between)
        ):
            raise ValueError(f"{template_path}의 하위 섹션이 부모 섹션 밖에 있습니다: {name}")

    return TOKEN.sub(lambda match: sections[match.group(1)], normalized).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    source = (root / "shared/global-instructions.md").read_text(encoding="utf-8")
    sections = parse_sections(source)
    stale: list[str] = []
    for relative, template_relative in TARGETS.items():
        path = root / relative
        template = (root / template_relative).read_text(encoding="utf-8")
        expected = rendered(template, sections, template_relative)
        actual = path.read_text(encoding="utf-8").replace("\r\n", "\n") if path.exists() else ""
        if args.check:
            if actual != expected:
                stale.append(str(relative))
            continue
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(expected)

    if stale:
        print("공통 전역 지침과 불일치: " + ", ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
