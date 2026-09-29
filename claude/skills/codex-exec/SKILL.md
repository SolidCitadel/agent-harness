---
name: codex-exec
description: 사용자가 조사·검토 같은 하위 작업을 Codex나 codex exec에 맡기라고 했을 때, Codex CLI(`codex exec`)를 읽기 전용으로 실행하고 그 결과를 받아 쓰는 방법을 정한다. 사용자가 `/codex:rescue`로 코드 작업을 넘기는 경우, Claude 하위 agent 위임, 다른 skill이 Codex 호출 절차를 따로 정해 둔 작업에는 쓰지 않는다.
---

# Codex exec 위임

위임 지시의 수준과 결과를 신뢰하고 통합하는 기준은 전역 지침을 따르고, Codex CLI 실행과 이어서 질문하는 방법은 이 skill을 따른다. 조사를 맡기면 반환 형식에 사실마다 근거 위치(URL 또는 파일 경로)와, 웹 자료이면 게시일을 붙이라는 요구를 넣는다.

## 실행

지시문은 scratchpad의 Markdown 파일로 쓰고 stdin으로 넘긴다. Bash 도구로 다음 명령을 background로 실행하고 완료 알림을 기다린다.

```bash
codex [--search] exec --skip-git-repo-check -s read-only -C <작업 디렉터리> [-i <이미지>...] -o <결과.md> - < <지시.md> > <로그.txt> 2>&1
```

- `--search`: 웹 검색이 필요할 때 `exec` 앞에 둔다.
- `-s read-only`: Codex가 작업 중 파일을 바꾸지 않게 한다.
- `-C`: Codex가 읽어야 할 파일이 있는 디렉터리를 준다. 없으면 scratchpad를 준다.
- `-i`: 이미지 입력. 값을 여러 개 받으므로 `-o` 앞에 둔다.
- `-o`: Codex의 마지막 응답만 파일로 받는다. 진행 로그는 `<로그.txt>`로 분리한다.
- 모델과 추론 강도는 `~/.codex/config.toml` 기본값을 쓰고, 사용자가 지정하면 `-m <모델>`, `-c model_reasoning_effort=<값>`으로 바꾼다.

로그 머리의 `model:`과 `session id:` 줄에 실제 모델과 세션 ID가 있다. 산출물에 수행 도구를 기록해야 하면 이 모델명을 쓴다.

실행이 실패하면 로그 끝의 오류(인증, 모델 거부, CLI 버전 등)를 사용자에게 보고하고, Claude가 다른 도구로 대신 수행할지는 사용자 결정을 받는다.

## 이어서 질문

전역 지침에 따라 결과를 추가로 확인해야 하면 Claude 도구로 대신 조사하지 않고 같은 세션에 이어서 질문한다. 처음 실행한 `-C` 디렉터리에서 실행하고, `resume`은 `-s`를 받지 않고 처음 실행의 sandbox도 이어받지 않으므로 `-c sandbox_mode`로 읽기 전용을 다시 지정한다.

```bash
cd <처음 -C 디렉터리> && codex [--search] exec resume --skip-git-repo-check -c sandbox_mode='"read-only"' <session id> -o <결과2.md> - < <추가 지시.md> > <로그2.txt> 2>&1
```
