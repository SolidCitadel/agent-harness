---
paths:
  - "**/SKILL.md"
globs:
  - "**/SKILL.md"
---

# SKILL.md 작성

- frontmatter의 `name` 필드에 스킬의 고유 이름을 반드시 명시한다(누락 시 파일명인 `SKILL`로 시스템에 덮어써져 뭉뚱그려진다).
- frontmatter의 `description`은 문서 설명이 아니라, Claude가 능동적으로 호출을 결정하기 위한 단서다. 의도한 상황에서 `description`만 보고 호출 여부를 판단할 수 있는 문구를 쓴다.
