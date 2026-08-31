# Codex 하네스 구성물

무언가를 기록하기 전에 필요한 발동 조건과 적용 범위를 정하고 그 조건을 지원하는 구성물을 고른다.

- 모든 작업에 걸리는 개인 기본값은 전역 `~/.codex/AGENTS.md`에 둔다.
- 특정 프로젝트 전체에 걸리는 지침은 프로젝트 루트 `AGENTS.md`에 둔다.
- 특정 하위 경로에만 걸리는 지침은 해당 경로의 `AGENTS.md`에 둔다. 같은 디렉터리의 `AGENTS.override.md`는 `AGENTS.md`보다 우선하며, 루트에서 현재 작업 디렉터리까지 가까운 지침이 앞선 지침을 덮는다.
- 반복되는 전문 workflow는 skill에 둔다. skill을 다룰 때 `~/.codex/skill-authoring.md`를 읽는다.
- 격리된 판단, 독립 검수, 반복되는 전문 역할은 agent에 둔다. 개인 agent는 `~/.codex/agents/*.toml`, 프로젝트 agent는 `.codex/agents/*.toml`에 두며, agent를 다룰 때 `~/.codex/agent-authoring.md`를 읽는다.
- 제품 수명주기의 기계적 검사는 Codex hook에 둔다. 개인 hook은 `~/.codex/hooks.json` 또는 `~/.codex/config.toml`, 프로젝트 hook은 `.codex/hooks.json` 또는 `.codex/config.toml`에서 관리한다.
- 샌드박스 밖 명령의 허용·질문·차단만 Codex `.rules`에 둔다.
