#!/usr/bin/env python3
"""Check that a commit changing harness files carries the provenance trailers CONTRIBUTING.md requires.
The commit-msg hook runs this with the message file."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

HARNESS_PREFIXES = ("shared/", "claude/", "codex/")
HARNESS_FILES = ("AGENTS.md", "CLAUDE.md")
TRIGGERS = ("failure", "request", "refine")
AGENT = re.compile(r"^(human|unknown|\S+ \([^()]+\))$")
FORMAT = """하네스 파일을 바꾸는 커밋은 본문 끝에 trailer를 둔다(CONTRIBUTING.md의 커밋 절):
  Trigger: failure | request | refine
  Failure-Model: <모델 ID> (<하네스>) | unknown   # Trigger가 failure일 때만
  Revised-By: <모델 ID> (<하네스>) | human
  Reviewed-By: <모델 ID> (<하네스>) | none
예: Revised-By: claude-opus-5-5 (claude-code)"""


def touches_harness(paths: list[str]) -> bool:
    return any(path.startswith(HARNESS_PREFIXES) or path in HARNESS_FILES for path in paths)


def trailers(message: str) -> dict[str, list[str]]:
    """Read `Key: value` lines of the last paragraph, ignoring comment lines."""
    lines = [line.rstrip() for line in message.replace("\r\n", "\n").split("\n") if not line.startswith("#")]
    while lines and not lines[-1]:
        lines.pop()
    block: list[str] = []
    for line in reversed(lines):
        if not line:
            break
        block.insert(0, line)
    found: dict[str, list[str]] = {}
    for line in block:
        match = re.match(r"^([A-Za-z][\w-]*):\s*(.*)$", line)
        if match:
            found.setdefault(match[1].lower(), []).append(match[2].strip())
    return found


def problems(message: str) -> list[str]:
    found = trailers(message)
    errors: list[str] = []
    trigger = found.get("trigger", [])
    if len(trigger) != 1 or trigger[0] not in TRIGGERS:
        errors.append(f"Trigger는 {', '.join(TRIGGERS)} 중 하나를 한 번 적는다.")
    failure = found.get("failure-model", [])
    if trigger == ["failure"] and not failure:
        errors.append("Trigger가 failure이면 Failure-Model이 필요하다.")
    if failure and trigger != ["failure"]:
        errors.append("Failure-Model은 Trigger가 failure일 때만 적는다.")
    for key, name, allowed in (("failure-model", "Failure-Model", ()), ("revised-by", "Revised-By", ()),
                               ("reviewed-by", "Reviewed-By", ("none",))):
        values = found.get(key, [])
        if key != "failure-model" and not values:
            errors.append(f"{name}가 필요하다.")
        errors += [f"{name} 값 형식이 다르다: {value}" for value in values
                   if value not in allowed and not AGENT.match(value)]
    return errors


def staged_paths(root: Path) -> list[str]:
    result = subprocess.run(["git", "diff", "--cached", "--name-only", "-z"], cwd=root, capture_output=True, check=True)
    return [path for path in result.stdout.decode("utf-8").split("\0") if path]


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parent.parent
    merge_head = subprocess.run(["git", "rev-parse", "--git-path", "MERGE_HEAD"], cwd=root, capture_output=True,
                                text=True, check=True).stdout.strip()
    if (root / merge_head).exists() or not touches_harness(staged_paths(root)):
        return 0
    errors = problems(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if errors:
        print("\n".join(errors) + "\n\n" + FORMAT, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
