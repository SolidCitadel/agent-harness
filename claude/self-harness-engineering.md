# self-harness engineering

에이전트가 자기 운영을 다시 엔지니어링하는 행위와 그 기계의 지도다. self-improve가 개선 대상이 이 기계의 구성물이라 판단하면 이 문서를 읽어 전체 워크플로우를 조망하고 개선점을 짚는다. 이 층위는 "skill을 만드는 skill"처럼 한 단계 위라 변경에 최고 신중도를 요구한다.

관리 정본은 `Documents/Workspace/agent-harness`이고 `~/.claude`의 사용자 작성 항목은 그중 Claude Code 어댑터와 shared skill을 가리킨다. `shared/principles.md`는 플랫폼 중립 의미의 대조 기준이며 Claude Code가 런타임에 직접 읽는 지침은 `CLAUDE.md`다.

## 대상

self-harness engineering의 대상은 에이전트의 자기수정 루프를 이루는 구성물이다 — 확인된 문제를 지속적인 운영 변경으로 바꾸는 절차(self-improve), 메타 문서 변경을 집필하는 규율(meta-doc·type-rule), 변경을 검증하는 도구(critic·게이트).

meta-doc과의 관계는 교차다: meta-doc은 모든 메타 문서(로컬 포함)를 관장하고 이 지도는 그중 자기수정 기계만 관조한다. 어느 쪽도 상대를 포함하지 않는다 — meta-doc은 이 지도의 집필을 서술형 기준으로 규율하고, 이 지도는 meta-doc을 한 구성물로 담는다.

## 표면과 역할

| 구성물 | 역할 | 위치 |
|---|---|---|
| self-improve (skill) | 개선 절차 — 진단·게이트·제안·검증 | `skills/self-improve/SKILL.md` |
| port-harness-change (shared skill) | 확인된 의미를 다른 플랫폼에 선택적으로 포팅 | `shared/skills/port-harness-change/SKILL.md` |
| meta-doc.md (rule) | 메타 문서 집필 규율 — 소속 판단·작성 형식·개정 검증 | `rules/meta-doc.md` |
| type-rule (rule) | 유형별 작성법 | `rules/{rules,agents,skill-md}.md` |
| meta-doc-critic (agent) | 메타 편집 독립 검수 | `agents/meta-doc-critic.md` |
| 검증 게이트 (hook) | critic 검수와 완결 마킹을 잊지 않게 stop 시 상기 | `hooks/verify-meta-doc.py`(로직)·`hooks/mark-verified.sh` |

## 불변 메커니즘과 근거

자기수정은 파급이 커서 반사적 append와 검수 누락이 위험하다. Meta-doc critic은 작성자와 분리된 독립 역할로 기준 결함·중복·불필요한 handoff를 찾는다. 검증 hook은 critic 실행을 증명하지 않으며, 감지된 메타 편집 뒤 검수와 명시적 완결 마킹을 잊지 않도록 stop을 막는 reminder gate다.

승인→편집→critic→지적 반영→최종 critic→완결 마킹의 순서는 사용자 권한을 변경 전에 확인하고, 지적 반영 뒤의 실제 최종 내용을 독립 검수하며, 그 검수가 결합된 파일 상태만 완료로 마킹하기 위해 유지한다.

## 변경 워크플로우

사건 확정 → 확인된 문제의 발동·정보·판정 기준·생산 프레이밍·규칙 범위와 방향·검증·게이트·도구 추적 → 구성요소 삭제·병합 가능성 판정 → 다음 실행에도 남는 최소 개입 제안·승인 → 편집 → 연결된 workflow 전체 critic → 지적 반영 → 최종 critic → 완결 마킹.
