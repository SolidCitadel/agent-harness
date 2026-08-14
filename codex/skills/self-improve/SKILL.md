---
name: self-improve
description: 사용자가 Codex의 작업 방식·지침 준수를 지적하거나, 지침 준수가 목적을 해친 상황에서 원인을 진단하고 agent-harness의 Codex 메타 문서를 개선한다.
---

# 자기 개선

## 진단

1. 원 사건과 관련 문서·도구의 실제 상태를 대조한다.
2. 실행 실패나 부주의로 종결하지 말고 실패를 허용한 발동·정보·판정 기준·생산 프레이밍·검증·게이트·도구를 추적한다.
3. 규칙 적용이 목적을 해쳤다면 규칙의 범위·방향·소속을 추적한다.
4. 메타 문서를 바꾸기 전에 [메타 문서 규율](references/meta-doc.md)을 읽는다. 자기수정 workflow를 바꿀 때는 [self-harness 지도](references/harness-engineering.md)도 읽는다.

## 개입

다음 실행에도 남으면서 전체 실패 경로의 원인을 직접 바꾸는 가장 작은 개입을 고른다. 전역 기본값은 `AGENTS.md`, 반복 workflow는 skill, 기계적 수명주기 검증은 Codex hook, 셸 권한 정책은 Codex `.rules`에 둔다.

## 변경과 검증

1. 원인과 최소 수정안을 사용자에게 제안하고 승인받는다.
2. 승인된 Codex 또는 shared 문서를 편집한다.
3. 가능하면 작성 맥락과 결론을 넘기지 않은 독립 agent에 대상 경로·원 사건·직접 연결된 workflow만 전달해 검수한다. 독립 agent를 사용할 수 없으면 새로 원문을 읽는 분리된 검수 패스로 같은 기준을 적용하고 그 한계를 밝힌다.
4. 지적을 반영한 최종 상태를 다시 검수한다.
5. `python ~/.codex/harness-hooks/mark-verified.py <최종 검수한 경로...>`로 현재 파일 상태를 마킹한다.
6. 원인이 Claude에도 존재할 구조적 근거가 있을 때만 `port-harness-change`를 사용한다. 모델 성향이나 Codex 기능에 묶인 문제는 Codex에 남긴다.
