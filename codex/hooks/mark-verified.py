#!/usr/bin/env python3
"""Record mtimes after the final independent review of harness metadata."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


def main() -> int:
    state_path = Path(
        os.environ.get(
            "CODEX_META_VERIFIED_STATE",
            str(Path.home() / ".codex" / ".meta-verified.json"),
        )
    )
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        if not isinstance(state, dict):
            state = {}
    except (OSError, ValueError):
        state = {}

    marked = []
    for raw in sys.argv[1:]:
        path = Path(raw).expanduser().resolve()
        paths = [path]
        if path.is_dir():
            paths = [item.resolve() for item in path.rglob("*") if item.is_file()]
        for item in paths:
            try:
                state[str(item)] = item.stat().st_mtime
                marked.append(str(item))
            except OSError:
                print(f"접근 불가: {item}", file=sys.stderr)

    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"마킹됨: {len(marked)}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
