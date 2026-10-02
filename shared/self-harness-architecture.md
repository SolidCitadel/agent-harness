# Self-harness 구조

- 하네스: AI의 작업 수행을 유도·제약·지원하는 지침, 실행 설정·장치와 그 연결 구조.
- 하네스 구성물: 하네스를 이루는 개별 지침·skill·agent 명세·rule·hook 등과 프로젝트 지침이 하네스 구성물로 선언한 파일.
- agent 명세: 역할을 특정 플랫폼에서 실행하도록 이름·설정·지침 연결을 선언한 구성물.

| 구성물 | 책임 |
|---|---|
| `shared/global-instructions.md` | 양 플랫폼 전역 지침의 원본 |
| `claude/platform-text.toml`, `codex/platform-text.toml` | 공통 원본의 플랫폼 빈칸에 들어갈 문구 |
| `codex/AGENTS.md`, `claude/CLAUDE.md` | 공통 원본에서 생성해 설치하는 전역 지침 |
| `claude/`·`codex/`의 `self-diagnosis.md`, `harness-revision.md`, `harness-components.md`, `skills/integrate-context`, `skills/refine-harness`, `skills/modify-harness` | 공통 원본에서 생성해 설치하는 플랫폼별 파일 |
| `shared/harness-authoring.md` | 모든 하네스 구성물에 적용하는 플랫폼 중립 작성·개정 규율 |
| `shared/skill-authoring.md`, `shared/agent-authoring.md` | 해당 유형을 다룰 때 읽는 공통 전문 지식 |
| `shared/harness-components.md` | 구성물 선택 기준과 플랫폼별 위치, 유형별 작성 규율 라우팅의 원본 |
| `claude/rules/` | Claude Code에서 하네스 파일을 다룰 때 작성 규율을 자동으로 읽게 하는 연결 |
| `claude/skills/self-diagnose`, `codex/skills/self-diagnose` | 수행 진단을 주 에이전트가 직접 수행하고, 보정 제안과 개정안을 사용자 승인에 연결 |
| `shared/self-diagnosis.md` | 수행 진단의 절차와 반환 계약 |
| `shared/harness-revision.md` | 하네스 구성물의 개정안 작성·검수·반환·승인 후 적용과 Codex의 이력 상속 하위 agent 위임 절차 |
| `shared/skills/modify-harness` | 요청받거나 필요를 판단한 하네스 구성물의 추가·변경·삭제를 주 에이전트가 수행하고, Codex에서는 사용자가 지시·승인하면 하위 agent에 위임 |
| `shared/skills/integrate-context` | 새 맥락의 기록 필요성과 정본을 판단하고 지속적으로 반영 |
| `shared/skills/refine-harness` | 기존 하네스 구성물의 규범과 구조를 사용자와 함께 정제 |
| `shared/scripts/worktree.py` | 승인 전 하네스 개정안을 담는 worktree 브랜치의 생성, 기준 브랜치 병합과 정리 |
| `shared/harness-review.md` | 호출자가 제공할 입력과 하네스 검수자의 범위·권한·출력 |
| `codex/agents/harness-reviewer.toml` | 하네스 검수 역할의 실행 설정과 공통 계약 연결. Claude Code는 `codex-exec` wrapper로 이 정의를 적용해 호출 |
