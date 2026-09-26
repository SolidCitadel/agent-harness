#!/usr/bin/env python3
"""Post-edit hook for Claude Code and Codex: render platform files and hand failures back to the agent."""

import json
import os
import subprocess
import sys
from pathlib import Path


# Hook output is read as UTF-8 by both products; Windows pipes otherwise use the ANSI code page.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
renderer = Path(__file__).resolve().parent / "render_platform_files.py"
result = subprocess.run(
    [sys.executable, str(renderer)],
    capture_output=True,
    text=True,
    encoding="utf-8",
    env={**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
)
if result.returncode != 0:
    # Exit code 2 with stderr is fed back to the agent by both Claude Code and Codex.
    print((result.stderr or result.stdout).strip() or "플랫폼 생성물 렌더링 실패", file=sys.stderr)
    sys.exit(2)
if result.stdout.strip():
    # Plain stdout never reaches the model; tell the agent through the context field both products accept.
    notice = (
        "렌더러가 플랫폼 생성물을 갱신했다.\n" + result.stdout.strip()
        + "\n생성물을 직접 고쳤다면 그 수정은 원본 기준으로 되돌려졌으니 shared/ 원본이나 platform-text.toml에서 고친다."
        " 커밋할 때 갱신된 생성물도 함께 스테이징한다."
    )
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": notice}}, ensure_ascii=False))
