#!/usr/bin/env bash
# 인터프리터 감지 wrapper: python3 우선, 없으면 python 으로 mark-verified.py 실행.
# 수동 호출용이라 python 이 없으면 조용히 넘기지 않고 에러로 알린다.
#   사용: bash ~/.claude/hooks/mark-verified.sh <파일경로> [<파일경로>...]
PY="$(command -v python3 || command -v python)"
[ -n "$PY" ] || { echo "오류: python3/python 둘 다 없음 — 마킹 불가" >&2; exit 1; }
exec "$PY" "$(dirname "$0")/mark-verified.py" "$@"
