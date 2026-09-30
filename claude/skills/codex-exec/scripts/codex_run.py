#!/usr/bin/env python3
"""Run `codex exec` read-only with fixed flags for Claude delegation, and resume a finished run by session id.

The prompt is read from stdin. Each run keeps its prompt, log, last message and metadata in a run directory, and
prints the last message followed by `session:` and `run:` lines."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib

AGENT_KEYS = ("developer_instructions", "model", "model_reasoning_effort")


def runs_dir() -> Path:
    return Path(os.environ.get("CODEX_RUNS_DIR") or Path(tempfile.gettempdir()) / "codex-runs")


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def repo_root(path: Path) -> Path:
    """The git top level containing `path`, so Codex loads that repository's AGENTS.md; `path` itself outside git.
    Other git failures (such as an untrusted owner) stop the run instead of silently moving the working root."""
    result = subprocess.run(["git", "-C", str(path), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        return Path(result.stdout.strip())
    if "not a git repository" in result.stderr:
        return path
    sys.exit(f"git 저장소 루트를 확인하지 못했습니다: {path}\n{result.stderr.strip()}")


def resolve_model(name: str | None, home: Path | None = None) -> str | None:
    """A model id, or a family name such as `luna` resolved to the newest listed `*-luna` model in Codex's model cache.
    Codex rejects bare family names, and the cache follows new releases."""
    if not name:
        return None
    try:
        cache = json.loads(((home or codex_home()) / "models_cache.json").read_text(encoding="utf-8"))
        models = [model for model in cache["models"] if model.get("visibility") == "list"]
    except (OSError, ValueError, KeyError, TypeError):
        models = []
    if any(model.get("slug") == name for model in models) or "-" in name:
        return name
    family = [model for model in models if str(model.get("slug", "")).endswith(f"-{name}")]
    if not family:
        sys.exit(f"모델 별칭을 해석하지 못했습니다: {name} (~/.codex/models_cache.json에서 찾지 못함). 전체 모델 ID를 지정하세요.")
    return min(family, key=lambda model: model.get("priority", sys.maxsize))["slug"]


def codex_command() -> list[str]:
    """Call npm-installed Codex through node, since a Windows .cmd shim lets cmd.exe re-parse quoted arguments."""
    found = shutil.which("codex")
    if not found:
        sys.exit("codex CLI를 찾지 못했습니다.")
    script = Path(found).parent / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
    node = shutil.which("node")
    return [node, str(script)] if os.name == "nt" and script.is_file() and node else [found]


def toml_string(value: str) -> str:
    # JSON 문자열 escape는 TOML basic string과 호환된다.
    return json.dumps(value, ensure_ascii=False)


def agent_overrides(name: str | None, home: Path | None = None) -> list[str]:
    """`-c` overrides that apply an agent definition's instructions and model settings to the exec session."""
    if not name:
        return []
    path = (home or codex_home()) / "agents" / f"{name}.toml"
    if not path.is_file():
        sys.exit(f"Codex agent 정의가 없습니다: {path}")
    definition = tomllib.loads(path.read_text(encoding="utf-8"))
    overrides: list[str] = []
    for key in AGENT_KEYS:
        if isinstance(definition.get(key), str) and definition[key].strip():
            overrides += ["-c", f"{key}={toml_string(definition[key].strip())}"]
    return overrides


def model_arguments(model: str | None, effort: str | None) -> list[str]:
    # agent 정의 뒤에 두어 사용자가 지정한 모델과 추론 강도가 우선한다.
    arguments = ["-m", model] if model else []
    return arguments + (["-c", f"model_reasoning_effort={toml_string(effort)}"] if effort else [])


def exec_arguments(root: Path, result: Path, search: bool = False, images: list[str] | None = None,
                   model: str | None = None, effort: str | None = None, agent: list[str] | None = None) -> list[str]:
    arguments = ["--search"] if search else []
    arguments += ["exec", "--skip-git-repo-check", "-s", "read-only", "-C", str(root)]
    for image in images or []:
        arguments += ["-i", image]
    return arguments + (agent or []) + model_arguments(model, effort) + ["-o", str(result), "-"]


def resume_arguments(session: str, result: Path, search: bool = False, model: str | None = None,
                     effort: str | None = None, agent: list[str] | None = None) -> list[str]:
    # resume은 -s를 받지 않고 처음 실행의 sandbox도 이어받지 않으므로 읽기 전용을 설정으로 다시 지정한다.
    arguments = ["--search"] if search else []
    arguments += ["exec", "resume", "--skip-git-repo-check", "-c", 'sandbox_mode="read-only"']
    return arguments + (agent or []) + model_arguments(model, effort) + [session, "-o", str(result), "-"]


def find_run(session: str, base: Path | None = None) -> dict:
    """The metadata of the first run that recorded `session`."""
    for meta in sorted((base or runs_dir()).glob("*/meta.json")):
        data = json.loads(meta.read_text(encoding="utf-8"))
        if data.get("session") == session:
            return data
    sys.exit(f"세션을 기록한 실행 폴더가 없습니다: {session}")


def header(log: str, key: str) -> str | None:
    """A `key: value` line of the Codex log header, such as `session id`, `model` or `reasoning effort`."""
    for line in log.splitlines():
        if line.lower().startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return None


def execute(build: Callable[[Path], list[str]], cwd: Path, prompt: str, meta: dict) -> int:
    run = runs_dir() / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    run.mkdir(parents=True)
    (run / "prompt.md").write_text(prompt, encoding="utf-8")
    result = run / "result.md"
    command = codex_command() + build(result)
    with (run / "log.txt").open("w", encoding="utf-8") as log:
        try:
            code = subprocess.run(command, cwd=cwd, input=prompt, stdout=log, stderr=subprocess.STDOUT, text=True,
                                  encoding="utf-8").returncode
        except OSError as error:
            log.write(f"codex 실행 실패: {error}\n")
            code = 1
    log_text = (run / "log.txt").read_text(encoding="utf-8", errors="replace")
    # resume이 같은 설정으로 이어지도록 요청값이 아니라 실제 적용된 모델·강도를 남긴다.
    meta = {**meta, "session": meta.get("session") or header(log_text, "session id"), "cwd": str(cwd), "exit": code,
            "model": header(log_text, "model") or meta.get("model"),
            "effort": header(log_text, "reasoning effort") or meta.get("effort")}
    (run / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    if code != 0 or not result.is_file():
        print("\n".join(log_text.splitlines()[-40:]), file=sys.stderr)
        print(f"\nexit: {code}\nrun: {run}", file=sys.stderr)
        return code or 1
    print(result.read_text(encoding="utf-8").rstrip())
    print(f"\nsession: {meta['session']}\nrun: {run}")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["resume"]:
        parser = argparse.ArgumentParser(prog="codex_run.py resume")
        parser.add_argument("--search", action="store_true", help="켜면 이번 질문에서 웹 검색을 쓴다")
        parser.add_argument("session")
        args = parser.parse_args(argv[1:])
        previous = find_run(args.session)
        search = args.search or previous.get("search", False)
        agent = previous.get("overrides", [])
        return execute(lambda result: resume_arguments(args.session, result, search, previous.get("model"),
                                                       previous.get("effort"), agent),
                       Path(previous["cwd"]), sys.stdin.read(), {**previous, "search": search})
    parser = argparse.ArgumentParser(prog="codex_run.py")
    parser.add_argument("--search", action="store_true")
    parser.add_argument("--agent")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("-i", "--image", action="append", default=[])
    parser.add_argument("--model", help="모델 ID 또는 계열 이름(sol, luna 등)")
    parser.add_argument("--effort")
    args = parser.parse_args(argv)
    root = repo_root(args.cwd.resolve())
    # 작업 위치를 저장소 루트로 옮기기 전에 상대 경로를 확정한다.
    images = [str(Path(image).resolve()) for image in args.image]
    model = resolve_model(args.model)
    agent = agent_overrides(args.agent)
    return execute(lambda result: exec_arguments(root, result, args.search, images, model, args.effort, agent),
                   root, sys.stdin.read(), {"agent": args.agent, "overrides": agent, "search": args.search,
                                            "model": model, "effort": args.effort})


if __name__ == "__main__":
    sys.exit(main())
