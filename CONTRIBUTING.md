# 기여 규약

## 변경 소속

- 플랫폼과 무관한 전역 지침·하네스 작성 규율·구조 의미와 직접 관리하는 workflow는 `shared/`에 둔다.
- 외부 배포물은 `shared/vendor/`에 원본 그대로 두고 출처·버전·해시는 `shared/third-party-skills.json`에서 관리한다.
- Claude Code와 Codex의 discovery 경로, agent 형식, hook, 권한 체계에 묶인 구현은 각 플랫폼 디렉터리에 둔다.
- 플랫폼 전용 변경은 해당 플랫폼에서 완결한다. 반대 플랫폼은 관련 문제나 정제 작업이 생겼을 때 기존 커밋의 원인·변경 이유·검증 범위를 참고해 적용 필요성을 판단한다. 공통 정본은 연결된 플랫폼에 반영하고, 실제 효과를 확인한 범위는 구분해 기록한다.
- 공통 원본에서 플랫폼마다 달라지는 문구는 `{{platform:이름}}` 빈칸으로 두고, 값은 `claude/platform-text.toml`과 `codex/platform-text.toml`에 같은 이름의 키로 둔다. `scripts/render_platform_files.py`의 대상 목록에 있는 생성물과 생성 디렉터리는 렌더러가 소유하므로 직접 고치지 않는다. 렌더러와 설치기는 원본과 다른 생성물을 덮어쓰고 원본에 없는 파일을 지운다. 새 렌더링 대상은 렌더러 대상 목록과 `shared/self-harness-architecture.md` 표에 추가한다. 새 생성물의 설치 경로가 기존 링크로 연결되지 않으면 `install.sh`·`install.ps1`·`verify.sh`·`verify.ps1`에 링크를 추가하고, 기존 링크의 원본이 생성물로 바뀌면 이전 링크 제거도 함께 둔다.

## 검증

- Windows 설치 변경은 `scripts/install.ps1`과 `scripts/verify.ps1`로 확인한다.
- Linux 설치 변경은 `scripts/install.sh`과 `scripts/verify.sh`로 확인한다.
- 공통 링크 명세나 저장소 구조를 바꾸면 두 플랫폼 구현을 함께 검증한다.
- 플랫폼별 동작은 해당 플랫폼의 실제 파일·링크 상태로 판정한다.
- `scripts/render_platform_files.py --check`로 플랫폼 문구와 원본 빈칸의 정합성, 생성물 drift와 잔여 파일을 확인한다.

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
