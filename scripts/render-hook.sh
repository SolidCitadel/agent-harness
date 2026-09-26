#!/usr/bin/env bash
# Claude Code 수정 후 hook 실행기: python3 우선, 없으면 python으로 render_hook.py를 실행한다.
PY="$(command -v python3 || command -v python)"
[ -n "$PY" ] || { echo 'python3 또는 python이 없어 플랫폼 생성물을 렌더링하지 못했습니다.' >&2; exit 2; }
exec "$PY" "$(dirname "$0")/render_hook.py"
