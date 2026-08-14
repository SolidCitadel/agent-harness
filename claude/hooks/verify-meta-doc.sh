#!/usr/bin/env bash
# 인터프리터 감지 wrapper: python3 우선, 없으면 python 으로 verify-meta-doc.py 실행.
# 둘 다 없으면 조용히 통과(Stop 훅은 fail-open — 잘못 차단하지 않는다).
# stdin(훅 이벤트 JSON)은 exec 로 그대로 .py 에 흘러간다.
PY="$(command -v python3 || command -v python)"
[ -n "$PY" ] || exit 0
exec "$PY" "$(dirname "$0")/verify-meta-doc.py"
