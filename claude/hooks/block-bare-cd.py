#!/usr/bin/env python3
# Block bare `cd` in Bash tool calls — preserves session cwd hygiene.
# (감지 wrapper: block-bare-cd.sh 가 python3||python 골라 실행.)
# Allows: subshells `(cd foo && bar)`, `git -C`, `--directory`, `--prefix`, absolute paths.
import json, sys, re

try:
    data = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)

cmd = (data.get("tool_input") or {}).get("command", "")
if not isinstance(cmd, str):
    sys.exit(0)

# Match: cd at command start, OR after ; && || | (chains that propagate cwd to session).
# Does NOT match: (cd foo && bar) — opening paren makes it a subshell, no session impact.
# re.M 으로 grep 의 줄 단위(^=줄 시작) 동작을 보존: 개행으로 이어진 새 명령의 cd 도 잡는다.
if re.search(r'(^|[;&|]+\s*)cd\s', cmd, re.M):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "bare `cd` 차단 — cwd는 이미 프로젝트 루트이고 세션 간 영속이니 그냥 상대경로로 실행하면 된다. 루트 밖 경로가 불가피할 때만: 절대경로 · `git -C` · `uv --directory` · `npm --prefix` · 서브셸 `(cd ...)`."
    }}))

sys.exit(0)
