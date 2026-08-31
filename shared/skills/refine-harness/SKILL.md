---
name: refine-harness
description: agent-harness의 기존 동작을 보존하며 중복된 지침, 불필요한 예외·검수·호출·파일을 줄일 때 명시적으로 사용한다.
---

# 하네스 정제

저장소 루트의 `shared/harness-authoring.md`, `shared/self-harness-architecture.md`와 대상 플랫폼의 작성 규율을 읽는다. Codex는 `codex/harness-components.md`, Claude Code는 `claude/rules/harness-authoring.md`를 사용한다.

## 조사와 제안

1. 실제 로딩·호출 경로와 사용자에게 보이는 동작을 확인한다.
2. 각 문장·파일·절차가 보존하는 동작과 발생시키는 비용을 확인한다.
3. 삭제·병합·이동·재작성안을 보존할 동작과 줄어드는 비용에 연결해 제시하고 승인받는다.

비용은 로드되는 분량, 조건과 예외, agent·tool 호출과 검수 회차, 승인·handoff, 정본과 파생물 수로 확인한다.

## 변경과 검증

정본부터 바꾸고 파생물과 호출 경로를 갱신한다. 삭제하거나 병합한 기존 책임마다 새 소유자 또는 폐기 근거를 대응한다.

보존하기로 한 동작과 비용 감소를 직접 확인한다. 링크·생성·형식·고아 참조는 기계적으로 검사한다.
