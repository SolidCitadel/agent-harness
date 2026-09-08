# agent-harness

Claude Code와 Codex의 개인 운영 지침과 재사용 workflow를 관리한다. 자기수정 구성요소의 책임은 `shared/self-harness-architecture.md`에 정리한다.

- `shared/skills/`: 직접 관리하는 플랫폼 공통 workflow
- `shared/vendor/`: 수정하지 않는 외부 원본과 라이선스
- `claude/`: Claude Code의 지침·rule·agent·hook. 수동 도구는 설치 시 `~/.claude/commands/`로 연결한다.
- `codex/`: Codex의 지침·하네스 검수 agent·플랫폼별 skill. 수동 skill은 암시 호출을 끈다.
- `scripts/`: 제품의 고정 discovery 경로에 선택적 링크를 설치하고 검증하는 스크립트

`~/.claude`와 `~/.codex` 전체를 관리하지 않는다. 인증, 세션, 캐시, 플러그인 및 제품이 쓰는 가변 상태는 각 제품 경로에 남긴다.

Anthropic의 `frontend-design` 원본은 `shared/vendor/`에서 관리한다. Claude에서는 `/frontend-design` command로, Codex에서는 `$frontend-design` 수동 skill로만 호출한다.

## 설치

### Windows

PowerShell에서 실행한다.

```powershell
.\scripts\install.ps1
.\scripts\verify.ps1
```

Windows에서는 디렉터리를 junction으로 연결한다. 파일 symbolic link 권한이 없으면 같은 볼륨의 hard link를 사용하므로, pull이나 checkout 뒤 installer와 verifier를 다시 실행해 연결을 확인한다. 파일 링크의 원본·설치 경로와 볼륨·파일 식별자는 `~/.codex/agent-harness-install-state.json`, `~/.claude/agent-harness-install-state.json`에 기록한다. 원본이 교체되어도 설치 파일이 기록된 파일과 같으면 다시 연결한다.

기록이 없는 기존 설치는 현재 원본과의 연결을 확인할 수 있을 때 등록한다. 소유 확인 실패나 상태 파일 손상 시 파일을 보존하고 중단한다. 이미 원본과 분리된 미등록 hard link는 자동 복구하지 않는다. 상태 기록에 실패하면 설치가 완료되지 않은 것으로 보고하며, 원인을 해결한 뒤 installer와 verifier를 다시 실행한다.

### Linux

Bash에서 실행한다.

```bash
./scripts/install.sh
./scripts/verify.sh
```

Linux에서는 파일과 디렉터리를 symbolic link로 연결한다.

설치기는 공통 섹션과 플랫폼 template에서 전역 지침을 생성하고 관리 파일을 제품 discovery 경로에 연결한다. 이미 다른 파일이나 링크가 있는 경로는 변경하지 않고 중단한다.

## 변경 흐름

수행에 대한 불만족이나 어긋남은 `self-diagnose`로 진단해 현재 교정과 재발 방지안을 정한다. 새 프로젝트 정보·결정·제약·선호를 지속적으로 반영할 때는 `integrate-context`로 기록 필요성과 정본을 판단한다. 누적된 하네스의 필요성·효과·비용과 구조는 명시 호출 전용 `refine-harness`로 사용자와 함께 정제한다.

변경 소속, 검증, 커밋 규약은 `CONTRIBUTING.md`에서 관리한다.
