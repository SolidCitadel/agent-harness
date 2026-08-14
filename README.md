# agent-harness

Claude와 Codex의 개인 운영 원칙과 재사용 워크플로를 관리한다.

- `shared/`: 플랫폼과 무관한 원칙과 스킬
- `claude/`: Claude의 지침·rule·agent·hook·플랫폼별 skill
- `codex/`: Codex의 지침·critic agent·플랫폼별 skill
- `scripts/`: 제품의 고정 discovery 경로에 선택적 링크를 설치하고 검증하는 스크립트

`~/.claude`와 `~/.codex` 전체를 관리하지 않는다. 인증, 세션, 캐시, 플러그인 및 제품이 쓰는 가변 상태는 각 제품 경로에 남긴다.

## 설치

PowerShell에서 다음을 실행한다.

```powershell
.\scripts\install.ps1
.\scripts\verify.ps1
```

설치기는 교체할 기존 대상을 저장소의 Git 제외 경로인 `.migration-snapshots/`로 이동한 뒤 디렉터리는 junction으로 연결한다. 제품 홈의 `backups` 등 제품 소유 경로는 사용하지 않는다. 파일 symbolic link 권한이 없는 Windows에서는 같은 볼륨의 hard link를 사용한다. Git 작업이 정본 파일을 교체하면 hard link가 분리될 수 있으므로 pull이나 checkout 뒤 `install.ps1`과 `verify.ps1`을 다시 실행한다.

## 변경 흐름

플랫폼에서 발견한 문제는 먼저 해당 플랫폼의 `self-improve`로 고친다. 다른 플랫폼에도 같은 실패 원인이 존재할 때만 `port-harness-change`로 의미를 옮긴다. 양쪽 파일을 기계적으로 같게 만들지 않는다.
