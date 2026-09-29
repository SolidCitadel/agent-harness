# 하네스 구성물

구성물은 문제가 드러난 작업이 아니라 규율이 실제로 필요한 발동 조건과 적용 범위로 고른다. 지침·workflow가 요구하는 것 중 충족 여부를 기계적으로 판별할 수 있는 것은 발생 빈도와 관계없이 필요한 시점에 자동으로 실행되는 hook·검사가 강제하게 하고 지침·workflow에서 뺀다. 지침에는 매번 판단이 필요한 요구만 두고, 기계적으로 판별할 수 있는 예외·edge case는 지침의 조건을 늘리지 않고 검사로 흡수한다. 검사는 오탐 없이 판정하고, 교정 안내는 그 검사의 실패 메시지에 둔다.

- 어디서 무슨 작업을 하든 전제되어야 하는 지식·개인 선호는 전역 `~/.claude/CLAUDE.md`에 둔다.
- 특정 프로젝트 전체에 걸리는 지침은 프로젝트 루트 `CLAUDE.md`에 둔다.
- 특정 경로·파일 유형에만 걸리는 지침은 rule로 프로젝트 `.claude/rules/<주제>.md` 또는 전역 `~/.claude/rules/<주제>.md`에 둔다. rule 파일명은 하나의 주제를 나타낸다. rule은 frontmatter `paths`의 glob에 매칭되는 파일로 작업할 때만 로드되고, `paths`가 없으면 항상 로드된다.
- 특정 작업 시점에만 필요한 전문 지식·절차는 skill로 프로젝트 `.claude/skills/<이름>/SKILL.md` 또는 전역 `~/.claude/skills/<이름>/SKILL.md`에 둔다. skill을 다룰 때 `~/.claude/skill-authoring.md`를 읽는다.
- 맥락·책임·권한을 분리해 맡길 역할은 agent로 프로젝트 `.claude/agents/*.md` 또는 전역 `~/.claude/agents/*.md`에 둘지 판단한다. agent를 다룰 때 `~/.claude/agent-authoring.md`를 읽는다.
- 저장소 상태의 불변 조건 검사는 에이전트와 무관하게 실행되는 git hook에, 도구 사용 전후·세션 시작·응답 종료 같은 에이전트 수명주기 시점의 차단·맥락 주입·자동 갱신은 에이전트 hook에 둔다. 에이전트 hook은 프로젝트 `.claude/settings.json` 또는 전역 `~/.claude/settings.json`의 `hooks`에서 관리한다.

한 프로젝트에만 해당하면 프로젝트 위치, 모든 프로젝트에 걸치면 전역 위치에 둔다.

## 하네스 개정 검수

`~/.claude/harness-review.md`를 읽고 입력을 준비한 뒤, 작성 대화 이력을 상속하지 않는 새 `harness-reviewer`를 호출한다.
