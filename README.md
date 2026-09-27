# agent-harness

Claude Code와 Codex의 개인 운영 지침과 재사용 workflow를 관리한다. 자기수정 구성요소의 책임은 `shared/self-harness-architecture.md`에 정리한다.

- `shared/skills/`: 직접 관리하는 플랫폼 공통 workflow
- `shared/vendor/`: 수정하지 않는 외부 원본과 라이선스
- `claude/`: Claude Code의 지침·rule·agent·hook. 수동 도구는 설치 시 `~/.claude/commands/`로 연결한다.
- `codex/`: Codex의 지침·하네스 검수 agent·플랫폼별 skill. 수동 skill은 암시 호출을 끈다.
- `scripts/`: 제품의 고정 discovery 경로에 선택적 링크를 설치하고 검증하는 설치기, 플랫폼 생성물 렌더러, 저장소 검사와 hook 실행기

`~/.claude`와 `~/.codex` 전체를 관리하지 않는다. 인증, 세션, 캐시, 플러그인 및 제품이 쓰는 가변 상태는 각 제품 경로에 남긴다.

Anthropic의 `frontend-design` 원본은 `shared/vendor/`에서 관리한다. Claude에서는 `/frontend-design` command로, Codex에서는 `$frontend-design` 수동 skill로만 호출한다.

## 설치

Python 3.11 이상으로 실행한다.

```bash
python scripts/install.py    # Windows
python3 scripts/install.py   # Linux
```

설치기는 공통 원본의 플랫폼 빈칸을 채워 플랫폼 생성물을 만들고 관리 파일을 제품 discovery 경로에 연결한 뒤 설치 링크를 검증한다. `--verify`는 설치하지 않고 검증만 한다. 이미 다른 파일이나 링크가 있는 경로는 변경하지 않고 중단한다. 생성 디렉터리 안에서 원본에 없는 파일은 제거하고 그 경로를 출력한다.

Linux에서는 파일과 디렉터리를 symbolic link로 연결한다. Windows에서는 디렉터리를 junction으로 연결하고, 파일은 symbolic link 권한이 없으면 같은 볼륨의 hard link를 사용한다. Windows 파일 링크의 원본·설치 경로와 볼륨·파일 식별자는 `~/.codex/agent-harness-install-state.json`, `~/.claude/agent-harness-install-state.json`에 기록한다. 원본이 교체되어도 설치 파일이 기록된 파일과 같으면 다시 연결한다. 기록이 없는 기존 설치는 현재 원본과의 연결을 확인할 수 있을 때 등록한다. 소유 확인 실패나 상태 파일 손상 시 파일을 보존하고 중단한다. 이미 원본과 분리된 미등록 hard link는 자동 복구하지 않는다. 상태 기록에 실패하면 설치가 완료되지 않은 것으로 보고하며, 원인을 해결한 뒤 설치기를 다시 실행한다.

설치기는 이 저장소의 `core.hooksPath`를 `.githooks`로 설정한다. 설치한 clone에서는 pull·checkout·rebase 뒤 git hook이 설치기를 다시 실행하고 HEAD 커밋을 저장소 검사로 확인한다. `git commit`으로 마친 merge(충돌 해결이나 커밋 전 검사 거부 뒤), `reset`, `stash`처럼 git hook이 실행되지 않는 작업 뒤에는 설치기를 다시 실행한다. 파일을 수정하면 Claude Code(`.claude/settings.json`)와 Codex(`.codex/hooks.json`)의 hook이 플랫폼 생성물을 다시 렌더링한다. Codex는 프로젝트 hook을 사용자가 신뢰 승인해야 실행하고, hook 정의(이벤트·matcher·명령)가 바뀌면 다시 승인받는다.

## 변경 흐름

수행에 대한 불만족이나 어긋남이 드러나면 `self-diagnose`가 대화 이력을 상속한 하위 agent에 진단을 맡겨, 검수를 거친 재발 방지안을 사용자 승인에 올린다. 새 프로젝트 정보·결정·제약·선호를 지속적으로 반영할 때는 `integrate-context`로 기록 필요성과 정본을 판단한다. 기존 하네스 구성물의 필요성·효과·비용과 구조는 명시 호출 전용 `refine-harness`로 사용자와 함께 정제한다.

변경 소속, 검증, 커밋 규약은 `CONTRIBUTING.md`에서 관리한다.
