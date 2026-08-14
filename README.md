# agent-harness

Claude와 Codex의 개인 운영 원칙과 재사용 워크플로를 관리한다.

- `shared/`: 플랫폼과 무관한 원칙과 스킬
- `claude/`: Claude의 지침·rule·agent·hook·플랫폼별 skill
- `codex/`: Codex의 지침·critic agent·플랫폼별 skill
- `scripts/`: 제품의 고정 discovery 경로에 선택적 링크를 설치하고 검증하는 스크립트

`~/.claude`와 `~/.codex` 전체를 관리하지 않는다. 인증, 세션, 캐시, 플러그인 및 제품이 쓰는 가변 상태는 각 제품 경로에 남긴다.

## 설치

### Windows

PowerShell에서 실행한다.

```powershell
.\scripts\install.ps1
.\scripts\verify.ps1
```

Windows에서는 디렉터리를 junction으로 연결한다. 파일 symbolic link 권한이 없으면 같은 볼륨의 hard link를 사용하므로, pull이나 checkout 뒤 installer와 verifier를 다시 실행해 연결을 확인한다.

### Linux

Bash에서 실행한다.

```bash
./scripts/install.sh
./scripts/verify.sh
```

Linux에서는 파일과 디렉터리를 symbolic link로 연결한다.

## 변경 흐름

플랫폼에서 발견한 문제는 먼저 해당 플랫폼의 `self-improve`로 고친다. 다른 플랫폼에도 같은 실패 원인이 존재할 때만 `port-harness-change`로 의미를 옮긴다. 양쪽 파일을 기계적으로 같게 만들지 않는다.

변경 소속, 검증, 커밋 규약은 `CONTRIBUTING.md`에서 관리한다.
