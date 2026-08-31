---
paths:
  - "**/AGENTS.md"
  - "**/AGENTS.override.md"
  - "**/CLAUDE.md"
  - "**/SKILL.md"
  - "**/agents/**/*.md"
  - "**/agents/**/*.toml"
  - "**/rules/**/*.md"
  - "**/.codex/rules/**/*.rules"
  - "**/hooks/**/*"
  - "**/.codex/hooks.json"
  - "**/.codex/config.toml"
  - "**/self-harness-architecture.md"
globs:
  - "**/AGENTS.md"
  - "**/AGENTS.override.md"
  - "**/CLAUDE.md"
  - "**/SKILL.md"
  - "**/agents/**/*.md"
  - "**/agents/**/*.toml"
  - "**/rules/**/*.md"
  - "**/.codex/rules/**/*.rules"
  - "**/hooks/**/*"
  - "**/.codex/hooks.json"
  - "**/.codex/config.toml"
  - "**/self-harness-architecture.md"
---

# Claude Code 하네스 작성

대상 하네스 구성물을 바꾸기 전에 `~/.claude/harness-authoring.md`를 읽는다.

무언가를 기록하기 전에 이 규율·지식이 언제·어디서 걸려야 하는지 발동 조건부터 규정한다. 조건은 그것이 불거진 맥락과 독립으로 잡는다. 스킬 실행 중 드러난 필요라도 그 스킬 밖에서도 걸리면 조건은 시점이 아니라 실제 적용 범위다. 유형은 그 발동 조건이 정한다.

- 특정 작업 시점에만 필요한 전문 지식·절차 → 해당 `SKILL.md`
- 특정 경로·파일명·확장자에 한정되는 규칙 → Rule (`.claude/rules`)
- 어디서 무슨 작업을 하든 전제되어야 하는 지식·개인 선호 → `CLAUDE.md`
- 제품 수명주기의 기계적 검사 → hook

유형과 별개로, 실행에 컨텍스트 위임이나 격리가 필요하면 agent로 분리한다.

소속을 정한 뒤 범위로 위치를 정한다. Skill·Rule·agent·hook·`CLAUDE.md`는 저마다 프로젝트 위치(`<프로젝트>/.claude/…`·`<프로젝트>/CLAUDE.md`)와 전역 위치(`~/.claude/…`·`~/.claude/CLAUDE.md`)를 함께 가진다. 한 프로젝트에만 해당하면 프로젝트 위치, 모든 프로젝트에 걸치면 전역 위치에 둔다.

`agents.md`, `rules.md`, `skill-md.md`가 매칭되는 유형의 제품 형식을 추가로 규정한다.
