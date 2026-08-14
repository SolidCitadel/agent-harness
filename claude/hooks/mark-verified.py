#!/usr/bin/env python3
# 메타 문서 검증 완료 마킹 로직 (감지 wrapper: mark-verified.sh 가 python3||python 골라 실행).
# 인자로 받은 파일들의 현재 mtime을 상태 파일에 기록한다.
# 지적 반영 뒤 최종 critic 검수까지 끝낸 직후 호출한다. 이후 그 파일을 다시 편집하면
# Stop 게이트가 재발동한다(새 편집은 재검증 요구).
import json, sys, os

state_path = os.environ.get("META_VERIFIED_STATE") or os.path.join(os.path.expanduser("~"), ".claude", ".meta-verified.json")
files = sys.argv[1:]
try:
    with open(state_path, encoding='utf-8') as f:
        state = json.load(f)
except Exception:
    state = {}
marked = []
for fp in files:
    ap = os.path.abspath(fp)
    try:
        state[ap] = os.path.getmtime(ap)
        marked.append(os.path.basename(ap))
    except Exception:
        print("경고: 접근 불가 -", fp, file=sys.stderr)
with open(state_path, 'w', encoding='utf-8') as f:
    json.dump(state, f, ensure_ascii=False, indent=0)
print("마킹됨:", ", ".join(marked) if marked else "(없음)")
