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

발동 조건은 문제가 드러난 작업이 아니라 규율이 실제로 필요한 범위로 정하고, 그 조건에 맞는 유형을 고른다.

- 특정 작업 시점에만 필요한 전문 지식·절차 → 해당 `SKILL.md`
- 특정 경로·파일명·확장자에 한정되는 규칙 → Rule (`.claude/rules`)
- 어디서 무슨 작업을 하든 전제되어야 하는 지식·개인 선호 → `CLAUDE.md`
- 제품 수명주기의 기계적 검사 → hook

컨텍스트 위임이나 격리가 필요하면 유형과 별개로 agent를 둔다.

한 프로젝트에만 해당하면 프로젝트 위치(`<프로젝트>/.claude/…`·`<프로젝트>/CLAUDE.md`), 모든 프로젝트에 걸치면 전역 위치(`~/.claude/…`·`~/.claude/CLAUDE.md`)에 둔다.

`agents.md`, `rules.md`, `skill-md.md`가 매칭되는 유형의 제품 형식을 추가로 규정한다.
