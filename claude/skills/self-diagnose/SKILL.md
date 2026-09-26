---
name: self-diagnose
description: 사용자가 요청·지침·맥락을 이해하거나 수행한 방식에 불만족을 드러내거나, 에이전트가 그 수행의 어긋남을 발견했을 때 사용한다. 대화 이력을 상속한 fork가 원인과 재발 방지 개정안을 검수까지 마쳐 반환하게 한다.
---

# 수행 진단 위임

주 에이전트가 수행하는 절차다. 이 skill이 생성한 진단 agent는 `~/.claude/self-diagnosis.md`를 따른다.

1. `Agent` 도구를 `subagent_type: fork`로 호출한다. prompt에는 fork가 진단 agent라는 것, `~/.claude/self-diagnosis.md`를 읽고 따르라는 지시, 어긋남이 드러난 사용자 발화·지점을 적는다.
2. fork가 검수자를 호출하지 못해 검수 입력을 반환하면, 작성 대화 이력을 전달하지 않고 새 `harness-reviewer`에 그 입력을 전달한다. 검수 보고는 `SendMessage`로 fork에 돌려준다.
3. 현재 작업의 교정은 주 에이전트가 맡는다. 반환된 보정 제안은 주 에이전트가 판단해 반영하고, 승인된 방향·범위를 바꾸는 보정은 사용자 승인 후 반영한다.
4. 재발 방지 개정안은 사용자 승인 전에는 현재 작업의 기준으로 삼지 않는다. `~/.claude/self-diagnosis.md`의 반환 항목 중 현재 작업 보정 제안을 뺀 나머지를 사용자에게 제시해 승인받는다.
5. 승인되면 승인된 최종안과 승인 과정의 변경을 `SendMessage`로 fork에 전달해 적용을 맡긴다. fork를 재개할 수 없으면 주 에이전트가 `~/.claude/self-diagnosis.md`의 승인 후 적용 절차를 따른다.
