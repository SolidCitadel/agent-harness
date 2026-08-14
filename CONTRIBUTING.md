# 기여 규약

## 변경 소속

- 플랫폼과 무관한 원칙과 workflow만 `shared/`에 둔다.
- Claude와 Codex의 discovery 경로, agent 형식, hook, 권한 체계에 묶인 구현은 각 플랫폼 디렉터리에 둔다.
- 한 플랫폼에서 확인한 변경은 반대편에 같은 실패 원인이 존재할 때만 포팅한다.
- installer의 rollback 자료는 `.migration-snapshots/`에 두고 제품 소유 경로에는 저장하지 않는다.

## 검증

- Windows 설치 변경은 `scripts/install.ps1`과 `scripts/verify.ps1`로 확인한다.
- Linux 설치 변경은 `scripts/install.sh`과 `scripts/verify.sh`로 확인한다.
- 공통 링크 명세나 저장소 구조를 바꾸면 두 플랫폼 구현을 함께 검증한다.
- 플랫폼별 동작은 해당 플랫폼의 실제 파일·링크 상태로 판정한다.

## 커밋

Conventional Commits의 변경 유형 대신 영향을 받는 운영 표면을 scope로 쓴다.

```text
<scope>: <imperative summary>
```

예:

```text
codex: replace verification hooks with critic agent
claude: tighten meta-document review workflow
shared: clarify evidence requirements
install: add Linux symlink support
repo: document contribution conventions
```

원 사건, 플랫폼 간 포팅 판단, 호환성 제약이 제목만으로 드러나지 않으면 commit body에 이유를 적는다. 여러 의미를 한 커밋에 묶지 않는다.
