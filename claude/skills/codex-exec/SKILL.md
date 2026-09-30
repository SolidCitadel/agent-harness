---
name: codex-exec
description: 사용자가 조사·검토 같은 하위 작업을 Codex나 codex exec에 맡기라고 했을 때와 하네스 개정안을 독립 검수받을 때, Codex CLI(`codex exec`)를 읽기 전용으로 실행하고 그 결과를 받아 쓰는 방법을 정한다. 사용자가 `/codex:rescue`로 코드 작업을 넘기는 경우, Claude 하위 agent 위임, 다른 skill이 Codex 호출 절차를 따로 정해 둔 작업에는 쓰지 않는다.
---

# Codex exec 위임

위임 지시의 수준과 결과를 신뢰하고 통합하는 기준은 전역 지침을 따르고, Codex CLI 실행과 이어서 질문하는 방법은 이 skill을 따른다. 조사를 맡기면 반환 형식에 사실마다 근거 위치(URL 또는 파일 경로)와, 웹 자료이면 게시일을 붙이라는 요구를 넣는다.

## 실행

`scripts/codex_run.py`가 읽기 전용 실행과 작업 위치, 결과·로그 보존을 고정한다. 지시는 heredoc으로 표준 입력에 넘긴다. 실행은 흔히 Bash 도구의 foreground 제한 시간을 넘기므로 background로 실행해 완료 알림을 기다린다.

```bash
python ~/.claude/skills/codex-exec/scripts/codex_run.py [--search] [--agent <이름>] [--cwd <경로>] [-i <이미지>]... [--model <모델>] [--effort <강도>] <<'EOF'
<지시>
EOF
```

- `--cwd`: Codex가 읽을 파일이 있는 경로. 그 경로가 속한 git 저장소의 루트에서 실행되므로 Codex는 그 저장소의 `AGENTS.md`를 읽는다. 기본값은 현재 디렉터리다.
- `--agent`: `~/.codex/agents/<이름>.toml`의 지시와 모델 설정을 적용한다. 예: `--agent harness-reviewer`.
- `--search`: 웹 검색이 필요할 때 쓴다.
- 모델: 범위가 명확한 조사·탐색·정리는 `--model luna`로, 검수·판단처럼 틀렸을 때 비용이 큰 작업은 `--model` 없이 기본 모델로 실행한다. 사용자가 지정하면 그 모델을 쓴다. 계열 이름은 그 계열의 최신 모델로 바뀐다.
- 추론 강도는 사용자가 지정할 때만 `--effort`로 바꾼다.

지시에는 작업 고유의 입력만 쓴다. `AGENTS.md`와 agent 정의가 이미 주는 지침, 읽기 전용 권한은 다시 쓰지 않는다.

결과는 표준 출력으로 받는다. 끝의 `session:` 줄은 세션 ID, `run:` 줄은 지시·로그·결과를 보존한 실행 폴더다. 산출물에 수행 도구를 기록해야 하면 실행 폴더 `log.txt`의 `model:` 줄을 쓴다. 실행이 실패하면 출력된 로그 끝의 오류(인증, 모델 거부, CLI 버전 등)를 사용자에게 보고하고, Claude가 다른 도구로 대신 수행할지는 사용자 결정을 받는다.

## 이어서 질문

전역 지침에 따라 결과를 추가로 확인해야 하면 Claude 도구로 대신 조사하지 않고 같은 세션에 이어서 질문한다. 작업 위치, agent, 실제 적용된 모델과 추론 강도는 처음 실행에서 이어받고, 이번 질문에 웹 검색이 필요하면 `--search`를 더한다.

```bash
python ~/.claude/skills/codex-exec/scripts/codex_run.py resume [--search] <session id> <<'EOF'
<추가 지시>
EOF
```
