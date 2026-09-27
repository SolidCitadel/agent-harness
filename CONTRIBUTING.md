# 기여 규약

## 변경 소속

- 플랫폼과 무관한 전역 지침·하네스 작성 규율·구조 의미와 직접 관리하는 workflow는 `shared/`에 둔다.
- 외부 배포물은 `shared/vendor/`에 원본 그대로 두고 출처·버전·해시는 `shared/third-party-skills.json`에서 관리한다.
- Claude Code와 Codex의 discovery 경로, agent 형식, hook, 권한 체계에 묶인 구현은 각 플랫폼 디렉터리에 둔다.
- 플랫폼 전용 변경은 해당 플랫폼에서 완결한다. 반대 플랫폼은 관련 문제나 정제 작업이 생겼을 때 기존 커밋의 원인·변경 이유·검증 범위를 참고해 적용 필요성을 판단한다. 공통 정본은 연결된 플랫폼에 반영하고, 실제 효과를 확인한 범위는 구분해 기록한다.
- 공통 원본에서 플랫폼마다 달라지는 문구는 `{{platform:이름}}` 빈칸으로 두고, 값은 `claude/platform-text.toml`과 `codex/platform-text.toml`에 같은 이름의 키로 둔다. 렌더러와 설치기는 원본과 다른 생성물을 덮어쓰고 원본에 없는 파일을 지운다. 기존 설치 경로의 원본이 바뀌면 `scripts/install.py`의 설치 목록에 이전 원본을 함께 둔다.

## 검증

- `.githooks/pre-commit`과 `.githooks/pre-merge-commit`이 스테이징된 트리에서 `scripts/check_repo.py`로 저장소 불변 조건을 검사해 위반한 커밋을 거부한다. 설치기가 `core.hooksPath`를 설정하기 전(미실행 또는 기존 git hook 보존으로 중단)에는 동작하지 않으므로 먼저 설치한다.
- Linux 커밋 검사는 Windows 분기를 symbolic link로 모의해 실행할 뿐 실제 Windows 파일시스템 동작(junction 판정·생성, Windows 경로 형식, hard link 대체, 볼륨·파일 식별자)은 실행하지 않으므로, 이 동작에 영향을 주는 설치 코드를 Windows가 아닌 곳에서 바꾸면 Windows에서 `python scripts/install.py`를 실행해 확인한다.
- 플랫폼별 동작은 해당 플랫폼의 실제 파일·링크 상태로 판정한다.

## 커밋

Conventional Commits의 변경 유형 대신 영향을 받는 운영 표면을 scope로 쓴다.

```text
<scope>: <imperative summary>
```

예:

```text
codex: clarify critic input contract
claude: align hook paths with installer
shared: refine evidence standard
install: verify supported link targets
repo: clarify contribution scope
```

하네스 개정의 결정 근거는 해당 변경의 커밋 본문에 기록한다. 다음 내용을 검토하고, 변경 내용만으로 복원하기 어려우며 후속 개정 판단에 필요한 근거를 남긴다.

- 목적과 문제: 바꾸려는 행동, 확인된 실패 또는 줄이려는 비용
- 결정과 근거: 선택한 방안, 중요한 대안의 기각 이유와 적용 범위의 근거
- 보존할 요구: 표현·구조가 바뀌어도 유지하려는 사용자 요구와 제약
- 검증과 한계: 실제 확인한 결과, 미확인 동작과 남은 불확실성

본문은 최종 변경에 맞춰 작성한다. 항목별 고정 제목은 요구하지 않는다. 독립적으로 설명하고 되돌릴 수 있는 결정은 커밋을 나눈다. 과거 결정에 의존하거나 이를 변경할 때는 관련 커밋을 식별할 수 있게 참조한다.

기록된 요구를 변경할 때는 필요한 사용자 합의를 다시 확인한다. 과거 기록은 현재 판단의 근거로 재평가한다.
