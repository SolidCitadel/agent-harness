# Self-harness 구조

- 하네스: AI의 작업 수행을 유도·제약·지원하는 지침, 실행 설정·장치와 그 연결 구조.
- 하네스 구성물: 하네스를 이루는 개별 지침·skill·agent 명세·rule·hook 등.
- agent 명세: 역할을 특정 플랫폼에서 실행하도록 이름·설정·지침 연결을 선언한 구성물.

| 구성물 | 책임 |
|---|---|
| `shared/global-instructions.md` | 양 플랫폼 전역 지침의 공통 섹션 |
| `codex/AGENTS.template.md`, `claude/CLAUDE.template.md` | 공통 섹션의 배치와 플랫폼 전용 전역 지침 |
| `codex/AGENTS.md`, `claude/CLAUDE.md` | 플랫폼 템플릿에서 생성해 설치하는 전역 지침 |
| `shared/harness-authoring.md` | 모든 하네스 구성물에 적용하는 플랫폼 중립 작성·개정 규율 |
| `shared/skill-authoring.md`, `shared/agent-authoring.md` | 해당 유형을 다룰 때 읽는 공통 전문 지식 |
| `codex/harness-components.md` | Codex 구성물의 선택·위치와 유형별 작성 규율 라우팅 |
| `claude/rules/harness-authoring.md` | Claude Code의 구성물 유형과 전역·프로젝트 위치 |
| `claude/skills/self-diagnose`, `codex/skills/self-diagnose` | 수행 진단을 대화 이력을 상속한 하위 agent에 위임하고, 반환된 보정 제안과 개정안을 사용자 승인에 연결 |
| `shared/self-diagnosis.md` | 진단 agent의 권한·진단 절차·개정안 검수·반환 계약 |
| `shared/skills/integrate-context` | 새 맥락의 기록 필요성과 정본을 판단하고 지속적으로 반영 |
| `shared/skills/refine-harness` | 누적된 하네스의 개별 판단과 구조를 사용자와 함께 정제 |
| `shared/harness-review.md` | 호출자가 제공할 입력과 하네스 검수자의 범위·권한·출력 |
| `codex/agents/harness-reviewer.toml`, `claude/agents/harness-reviewer.md` | 하네스 검수 역할의 플랫폼별 실행 설정과 공통 계약 연결 |
