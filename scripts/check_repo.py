#!/usr/bin/env python3
"""Check repository invariants that must hold before a commit. Pre-commit runs this on the staged tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_platform_files import TARGETS  # noqa: E402


def read(root: Path, path: str) -> str:
    return (root / path).read_text(encoding="utf-8").replace("\r\n", "\n")


def frontmatter(text: str) -> dict[str, str] | None:
    """Return top-level fields of a leading `---` block as raw YAML scalars, or None when the block is missing or unclosed.

    Inline comments are dropped from unquoted values, and a value continued on indented lines (block scalar or plain
    multi-line) is joined, so fields that YAML reads as non-empty are not reported empty."""
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0] != "---":
        return None
    fields: dict[str, str] = {}
    last = None
    for line in lines[1:]:
        if line == "---":
            return fields
        match = re.match(r"^([A-Za-z][\w-]*):(?:\s+(.*))?$", line)
        if match:
            last = match.group(1)
            value = (match.group(2) or "").strip()
            if not value.startswith(("'", '"')):
                value = re.sub(r"(^|\s+)#.*$", "", value)
            fields[last] = "" if value in {">", "|", ">-", "|-", ">+", "|+"} else value
        elif last and line.startswith((" ", "\t")) and line.strip() and not line.strip().startswith("- "):
            fields[last] = (fields[last] + " " + line.strip()).strip()
    return None


def text_value(value: str | None) -> str:
    """A YAML scalar as text: surrounding quotes removed."""
    value = (value or "").strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return value


def true_value(value: str | None) -> bool:
    """A YAML boolean true; a quoted "true" is a string and does not count."""
    return (value or "").strip().lower() == "true"


def check_frontmatter(root: Path) -> list[str]:
    errors: list[str] = []
    for base in ("shared/skills", "claude/skills", "codex/skills"):
        for skill in sorted((root / base).rglob("SKILL.md")):
            fields = frontmatter(skill.read_text(encoding="utf-8"))
            relative = skill.relative_to(root).as_posix()
            if fields is None or not text_value(fields.get("name")) or not text_value(fields.get("description")):
                errors.append(f"SKILL.md frontmatter에 name·description이 필요합니다: {relative}")
            elif text_value(fields["name"]) != skill.parent.name:
                errors.append(f"SKILL.md name이 디렉터리 이름과 다릅니다: {relative} ({text_value(fields['name'])})")
    for agent in sorted((root / "claude/agents").glob("*.md")):
        fields = frontmatter(agent.read_text(encoding="utf-8"))
        relative = agent.relative_to(root).as_posix()
        if fields is None or not text_value(fields.get("name")) or not text_value(fields.get("description")):
            errors.append(f"Claude agent frontmatter에 name·description이 필요합니다: {relative}")
        elif text_value(fields["name"]) != agent.stem:
            errors.append(f"Claude agent name이 파일 이름과 다릅니다: {relative} ({text_value(fields['name'])})")
    for rule in sorted((root / "claude/rules").glob("*.md")):
        text = rule.read_text(encoding="utf-8")
        if text.startswith("---") and frontmatter(text) is None:
            errors.append(f"Claude rule frontmatter가 닫히지 않았습니다: {rule.relative_to(root).as_posix()}")
    for agent in sorted((root / "codex/agents").glob("*.toml")):
        relative = agent.relative_to(root).as_posix()
        try:
            table = tomllib.loads(agent.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            errors.append(f"Codex agent TOML 형식 오류: {relative}: {error}")
            continue
        for key in ("name", "description", "developer_instructions"):
            if not isinstance(table.get(key), str) or not table[key].strip():
                errors.append(f"Codex agent 필드가 필요합니다: {relative} ({key})")
    return errors


def check_references(root: Path) -> list[str]:
    """Reading paths that routing depends on: each consumer must name the documents it hands off to."""
    required = {
        "CLAUDE.md": None,
        "claude/rules/harness-authoring.md": [
            "~/.claude/harness-authoring.md", "~/.claude/harness-components.md",
            "**/AGENTS.override.md", "**/.codex/rules/**/*.rules", "**/.codex/hooks.json", "**/.codex/config.toml",
            "**/.claude/settings.json", "**/.githooks/**/*",
        ],
        "claude/rules/skill-md.md": ["~/.claude/skill-authoring.md"],
        "claude/rules/agents.md": ["~/.claude/agent-authoring.md", "**/agents/**/*.toml"],
        "codex/AGENTS.md": ["~/.codex/harness-authoring.md", "~/.codex/harness-components.md"],
    }
    errors: list[str] = []
    if read(root, "CLAUDE.md").strip() != "@AGENTS.md":
        errors.append("루트 CLAUDE.md는 @AGENTS.md만 담아야 합니다.")
    for path, needles in required.items():
        if needles is None:
            continue
        text = read(root, path)
        errors.extend(f"{path}에 참조가 없습니다: {needle}" for needle in needles if needle not in text)
    return errors


def check_invocation_policies(root: Path) -> list[str]:
    errors: list[str] = []
    explicit_codex = re.compile(r"^\s*allow_implicit_invocation:\s*false\s*$", re.M)

    def claude_explicit(path: str) -> bool:
        fields = frontmatter(read(root, path))
        return fields is not None and true_value(fields.get("disable-model-invocation"))

    if not claude_explicit("claude/skills/refine-harness/SKILL.md") \
            or not explicit_codex.search(read(root, "codex/skills/refine-harness/agents/openai.yaml")):
        errors.append("refine-harness는 양 플랫폼에서 명시 호출 전용이어야 합니다.")
    if not explicit_codex.search(read(root, "codex/skills/frontend-design/agents/openai.yaml")):
        errors.append("외부 frontend-design은 Codex에서 명시 호출 전용이어야 합니다.")
    if not claude_explicit("claude/commands/frontend-design.md"):
        errors.append("Claude용 frontend-design command는 명시 호출 전용이어야 합니다.")
    return errors


def normalized_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def check_vendor(root: Path) -> list[str]:
    source = json.loads(read(root, "shared/third-party-skills.json"))["frontend-design"]
    skill = read(root, "shared/vendor/anthropics/frontend-design/SKILL.md")
    license_text = read(root, "shared/vendor/anthropics/frontend-design/LICENSE.txt")
    claude = read(root, "claude/commands/frontend-design.md")
    claude = claude.replace("disable-model-invocation: true\n", "", 1).replace(
        "license: Complete terms in frontend-design.LICENSE.txt", "license: Complete terms in LICENSE.txt", 1)
    expected_skill = source["upstreamSkillSha256"].upper()
    hashes = {
        "shared/vendor/anthropics/frontend-design/SKILL.md": (normalized_hash(skill), expected_skill),
        "shared/vendor/anthropics/frontend-design/LICENSE.txt": (normalized_hash(license_text), source["licenseSha256"].upper()),
        "codex/skills/frontend-design/SKILL.md": (normalized_hash(read(root, "codex/skills/frontend-design/SKILL.md")), expected_skill),
        "codex/skills/frontend-design/LICENSE.txt": (normalized_hash(read(root, "codex/skills/frontend-design/LICENSE.txt")), source["licenseSha256"].upper()),
        "claude/commands/frontend-design.md": (normalized_hash(claude), expected_skill),
    }
    errors = [f"외부 배포물 해시가 shared/third-party-skills.json 기록과 다릅니다: {path}"
              for path, (actual, expected) in hashes.items() if actual != expected]
    if source.get("implicitInvocation") is not False:
        errors.append("shared/third-party-skills.json의 frontend-design implicitInvocation은 false여야 합니다.")
    return errors


def generated_outputs() -> list[Path]:
    return [output for outputs in TARGETS.values() for output in outputs.values()]


def check_architecture(root: Path) -> list[str]:
    """Every generated output is named in a table row of the structure document, by full path or by its path under the platform directories."""
    text = "\n".join(line for line in read(root, "shared/self-harness-architecture.md").split("\n") if line.startswith("|"))
    errors: list[str] = []
    for output in generated_outputs():
        tail = Path(*output.parts[1:]).as_posix()
        if not re.search(r"`(?:(?:claude|codex)/)?" + re.escape(tail) + "`", text):
            errors.append(f"shared/self-harness-architecture.md 표에 생성물이 없습니다: {output.as_posix()}")
    return errors


GIT_LOCATION = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY", "GIT_PREFIX"}


def clean_env() -> dict[str, str]:
    # git hook이 넘긴 저장소 위치 변수가 남으면 하위 git 호출이 실제 저장소를 대상으로 삼는다.
    env = {key: value for key, value in os.environ.items() if key not in GIT_LOCATION}
    env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return env


def run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=clean_env(), capture_output=True, text=True, encoding="utf-8")


def failure(label: str, result: subprocess.CompletedProcess[str], hint: str = "") -> list[str]:
    if result.returncode == 0:
        return []
    # 오류 출력이 있으면 그것만 보여 준다. 설치기처럼 진행 출력이 많은 명령에서 원인이 묻히지 않게 한다.
    message = f"{label} 실패:\n{(result.stderr or result.stdout).strip()}"
    return [f"{message}\n{hint}" if hint else message]


def check_render(root: Path) -> list[str]:
    result = run([sys.executable, str(root / "scripts/render_platform_files.py"), "--check"], root)
    return failure("생성물 drift 검사", result,
                   "생성물을 직접 고쳤다면 렌더링에서 버려지므로 shared/ 원본이나 claude/·codex/의 platform-text.toml에서 고친다. "
                   "scripts/render_platform_files.py로 갱신하고 생성물도 함께 스테이징한다.")


def check_tests(root: Path) -> list[str]:
    return failure("단위 테스트", run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "*_test.py"], root))


def shell_scripts(root: Path) -> list[Path]:
    scripts = sorted(root.glob("scripts/*.sh")) + sorted(root.glob("claude/hooks/*.sh"))
    scripts += sorted(path for path in (root / ".githooks").iterdir() if path.is_file())
    return scripts


def check_shell(root: Path) -> list[str]:
    bash = shutil.which("bash")
    if not bash:
        return ["bash를 찾지 못해 셸 문법을 검사하지 못했습니다."]
    errors: list[str] = []
    for script in shell_scripts(root):
        errors.extend(failure(f"셸 문법 검사 {script.relative_to(root).as_posix()}", run([bash, "-n", str(script)], root)))
    return errors


def check_install(root: Path) -> list[str]:
    """Install a git-free copy into a scratch home, run the verifier, and require every generated output to be reachable through an installed link."""
    if not sys.platform.startswith("linux"):
        return []
    with tempfile.TemporaryDirectory() as scratch:
        # git 작업 트리에서 설치하면 설치기가 저장소 설정과 hook을 다루므로, git이 아닌 복사본에서 설치한다.
        copy = Path(scratch) / "repo"
        shutil.copytree(root, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"), symlinks=True)
        home = Path(scratch) / "home"
        errors = failure("설치 시뮬레이션(scripts/install.sh, 설치기 끝의 verify.sh 포함)",
                         run(["bash", str(copy / "scripts/install.sh"), "--home", str(home)], copy))
        if errors:
            return errors
        targets = {Path(os.path.realpath(link)) for link in home.rglob("*") if link.is_symlink()}
        for output in generated_outputs():
            real = (copy / output).resolve()
            if not any(real == target or target in real.parents for target in targets):
                errors.append(f"설치기가 생성물을 연결하지 않습니다: {output.as_posix()} (install·verify 스크립트에 링크 추가)")
        return errors


STATIC_CHECKS = (check_render, check_frontmatter, check_references, check_invocation_policies, check_vendor,
                 check_architecture)
CHECKS = STATIC_CHECKS + (check_tests, check_shell, check_install)


def guarded(check, root: Path) -> list[str]:
    # 파일·키 누락으로 한 검사가 중단돼도 나머지 검사와 교정 안내는 계속 낸다.
    try:
        return check(root)
    except (OSError, KeyError, ValueError) as error:
        return [f"{check.__name__} 검사를 끝내지 못했습니다: {type(error).__name__}: {error}"]


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--static", action="store_true", help="파일 내용만 읽는 검사만 실행한다(테스트·셸 문법·설치 시뮬레이션 제외)")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    errors = [error for check in (STATIC_CHECKS if args.static else CHECKS) for error in guarded(check, root)]
    for error in errors:
        print(error, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
