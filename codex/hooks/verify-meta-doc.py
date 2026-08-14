#!/usr/bin/env python3
"""Continue a Codex turn when changed harness metadata lacks a verification mark."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def metadata_files(root: Path) -> list[Path]:
    candidates = [root / "shared" / "principles.md", root / "codex" / "AGENTS.md"]
    for pattern in (
        "shared/skills/**/SKILL.md",
        "codex/skills/**/SKILL.md",
        "codex/skills/**/references/*.md",
        "codex/hooks.json",
        "codex/hooks/*.py",
    ):
        candidates.extend(root.glob(pattern))
    return sorted({path.resolve() for path in candidates if path.is_file()})


def load_json(path: Path) -> dict[str, float]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    if event.get("stop_hook_active"):
        return 0

    root = Path(__file__).resolve().parents[2]
    state_path = Path(
        os.environ.get(
            "CODEX_META_VERIFIED_STATE",
            str(Path.home() / ".codex" / ".meta-verified.json"),
        )
    )
    verified = load_json(state_path)
    pending = []
    for path in metadata_files(root):
        marker = verified.get(str(path))
        if marker is None or path.stat().st_mtime > float(marker):
            pending.append(str(path))

    if pending:
        reason = (
            "agent-harness의 다음 메타 문서가 검증 마커보다 새롭다:\n"
            + "\n".join(f"- {path}" for path in pending)
            + "\n\nself-improve 절차에 따라 원 사건과 직접 연결된 workflow를 검수하고, "
            "지적을 반영한 최종 상태를 다시 검수한 뒤 "
            "`python ~/.codex/harness-hooks/mark-verified.py <경로...>`로 마킹하라."
        )
        print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
