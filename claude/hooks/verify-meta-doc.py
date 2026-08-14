#!/usr/bin/env python3
# Stop 게이트 로직 (감지 wrapper: verify-meta-doc.sh 가 python3||python 골라 실행).
# 이번 세션에 편집된 메타 문서(CLAUDE.md·SKILL.md·rules·agents·self-harness-engineering.md)가
# 그 편집 이후 검증·마킹되지 않았으면 완료를 차단한다.
#
# 검증 완료 신호 = ~/.claude/.meta-verified.json 의 파일별 mtime 마커.
# - 검증(critic 실행 + 지적 반영)을 끝낸 뒤 mark-verified.sh로 파일의 현재 mtime을 기록한다.
# - 피드백 반영 편집 뒤 최종 critic 검수를 마치고 마킹한다.
# - 마킹 *이후* 다시 편집되면 파일 mtime > 마커 → 재발동(새 편집은 검증 요구).
#
# 이 방식은 "critic이 실제로 돌았는지"를 트랜스크립트에서 탐지하지 않으므로,
# 에이전트 미등록(부트스트랩)·이름 변경·트랜스크립트 압축에 영향받지 않는다.
import json, sys, os, re

try:
    data = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)

# 무한루프 방지: 직전 차단으로 인한 재진입이면 통과시킨다.
if data.get("stop_hook_active"):
    sys.exit(0)

tp = data.get("transcript_path")
if not tp:
    sys.exit(0)

STATE = os.environ.get("META_VERIFIED_STATE") or os.path.join(os.path.expanduser("~"), ".claude", ".meta-verified.json")
META = re.compile(r'(^|[\\/])(CLAUDE|SKILL|self-harness-engineering)\.md$|[\\/](rules|agents)[\\/].*\.md$', re.IGNORECASE)

# 이번 세션에 편집된(현존하는) 메타 문서 수집
edited = set()
try:
    with open(tp, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            msg = ev.get('message', ev)
            content = msg.get('content') if isinstance(msg, dict) else None
            if not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict) or b.get('type') != 'tool_use':
                    continue
                if b.get('name') in ('Edit', 'Write', 'MultiEdit'):
                    fp = (b.get('input') or {}).get('file_path', '')
                    if isinstance(fp, str) and META.search(fp) and os.path.exists(fp):
                        edited.add(os.path.abspath(fp))
except Exception:
    sys.exit(0)

# 검증 마커 로드
verified = {}
try:
    with open(STATE, encoding='utf-8') as f:
        verified = json.load(f)
except Exception:
    verified = {}

pending = []
for fp in sorted(edited):
    try:
        mt = os.path.getmtime(fp)
    except Exception:
        continue
    vt = verified.get(fp)
    if vt is None or mt > float(vt):
        pending.append(fp)

if pending:
    reason = (
        "이번 세션에서 다음 메타 문서를 편집했으나 검증·마킹되지 않았다(또는 마킹 이후 다시 편집됨):\n"
        + "\n".join("- " + p for p in pending)
        + "\n\nmeta-doc-critic으로 검증하라 — 호출 프롬프트에 대상 경로와 함께, "
          "각 편집이 해결하려는 문제(원 사건과 의도)를 전달한다. "
          "지적을 반영한 최종 상태를 critic으로 다시 검수한 뒤 "
          "`bash ~/.claude/hooks/mark-verified.sh <경로...>`로 마킹하라."
    )
    print(json.dumps({"decision": "block", "reason": reason}))

sys.exit(0)
