# Self-harness 구조

| 구성물 | 책임 |
|---|---|
| `shared/global-instructions.md` | 양 플랫폼 전역 지침의 공통 섹션 |
| `codex/AGENTS.template.md`, `claude/CLAUDE.template.md` | 공통 섹션의 배치와 플랫폼 전용 전역 지침 |
| `codex/AGENTS.md`, `claude/CLAUDE.md` | 플랫폼 템플릿에서 생성해 설치하는 전역 지침 |
| `shared/harness-authoring.md` | 모든 하네스 구성물에 적용하는 플랫폼 중립 작성·개정 규율 |
| `shared/skill-authoring.md`, `shared/agent-authoring.md` | 해당 유형을 다룰 때 읽는 공통 전문 지식 |
| `codex/harness-components.md` | Codex 구성물의 선택·위치와 유형별 작성 규율 라우팅 |
| `claude/rules/harness-authoring.md` | Claude Code의 구성물 유형과 전역·프로젝트 위치 |
| 플랫폼별 `self-improve` | 관찰된 실패의 원인 교정 |
| `shared/skills/refine-harness` | 기존 동작을 보존하며 하네스 비용을 줄이는 절차 |
| `shared/meta-doc-critic.md`, 플랫폼별 critic agent | 하네스 변경의 단발 독립 검수 계약과 실행 형식 |
| `shared/skills/port-harness-change` | 확인된 플랫폼 변경의 선택적 포팅 |
