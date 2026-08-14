---
paths:
  - "**/agents/**/*.md"
globs:
  - "**/agents/**/*.md"
---

# 서브에이전트 작성

frontmatter에 `name`과 `description`을 둔다. `description`은 설명이 아니라 Claude Code가 언제 이 에이전트를 spawn할지 판단하는 트리거 문구다 — 부차적·장황한 표현을 담지 않는다. 호출 시 전달해야 할 입력이 있으면 그 규약은 description에 담는다 — 호출자가 spawn 전에 보는 유일한 문장이다.
