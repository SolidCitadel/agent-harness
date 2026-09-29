#!/usr/bin/env python3
"""Render shared harness sources into platform files by filling {{platform:name}} slots."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
import tomllib


PLATFORM_TEXT = {
    "claude": Path("claude/platform-text.toml"),
    "codex": Path("codex/platform-text.toml"),
}
TARGETS = {
    Path("shared/global-instructions.md"): {
        "claude": Path("claude/CLAUDE.md"),
        "codex": Path("codex/AGENTS.md"),
    },
    Path("shared/self-diagnosis.md"): {
        "claude": Path("claude/self-diagnosis.md"),
        "codex": Path("codex/self-diagnosis.md"),
    },
    Path("shared/harness-revision.md"): {
        "claude": Path("claude/harness-revision.md"),
        "codex": Path("codex/harness-revision.md"),
    },
    Path("shared/harness-components.md"): {
        "claude": Path("claude/harness-components.md"),
        "codex": Path("codex/harness-components.md"),
    },
    Path("shared/skills/integrate-context"): {
        "claude": Path("claude/skills/integrate-context"),
        "codex": Path("codex/skills/integrate-context"),
    },
    Path("shared/skills/refine-harness"): {
        "claude": Path("claude/skills/refine-harness"),
        "codex": Path("codex/skills/refine-harness"),
    },
    Path("shared/skills/modify-harness"): {
        "claude": Path("claude/skills/modify-harness"),
        "codex": Path("codex/skills/modify-harness"),
    },
}
TOKEN = re.compile(r"\{\{platform:([^{}]+)\}\}")
LINE_TOKEN = re.compile(r"^[ \t]*\{\{platform:([^{}]+)\}\}[ \t]*$")
TEXT_SUFFIXES = {".md", ".yaml", ".yml", ".toml", ".txt"}


def parse_values(source: str, path: Path) -> dict[str, str]:
    try:
        table = tomllib.loads(source)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"{path}의 TOML 형식 오류: {error}") from error
    values: dict[str, str] = {}
    for name, value in table.items():
        if not isinstance(value, str):
            raise ValueError(f"{path}의 플랫폼 문구는 문자열이어야 합니다: {name}")
        values[name] = value.replace("\r\n", "\n").strip("\n")
    return values


def rendered(text: str, values: dict[str, str], path: Path, used: set[str]) -> str:
    """Fill slots; a slot alone on its line with an empty value removes the line and one surrounding blank line."""
    lines = text.replace("\r\n", "\n").split("\n")
    output: list[str] = []
    skip_blank = False
    for line in lines:
        if skip_blank:
            skip_blank = False
            if line == "":
                continue
        whole = LINE_TOKEN.match(line)
        if whole and value_of(whole.group(1), values, path, used) == "":
            skip_blank = bool(output) and output[-1] == ""
            continue
        output.append(TOKEN.sub(lambda match: value_of(match.group(1), values, path, used), line))
    result = "\n".join(output).rstrip("\n") + "\n"
    leftover = TOKEN.search(result)
    if leftover:
        raise ValueError(f"{path}의 렌더링 결과에 플랫폼 빈칸이 남았습니다: {leftover.group(0)}")
    return result


def value_of(name: str, values: dict[str, str], path: Path, used: set[str]) -> str:
    if name not in values:
        raise ValueError(f"{path}의 알 수 없는 플랫폼 문구: {name}")
    used.add(name)
    return values[name]


def source_files(root: Path, source: Path) -> list[Path]:
    base = root / source
    if base.is_file():
        return [Path()]
    return sorted(path.relative_to(base) for path in base.rglob("*") if path.is_file())


def expected_outputs(root: Path, values: dict[str, dict[str, str]]) -> tuple[dict[Path, bytes], dict[Path, int], set[str]]:
    outputs: dict[Path, bytes] = {}
    modes: dict[Path, int] = {}
    used: set[str] = set()
    for source, platforms in TARGETS.items():
        for relative in source_files(root, source):
            source_path = root / source / relative
            data = source_path.read_bytes()
            for platform, target in platforms.items():
                if source_path.suffix in TEXT_SUFFIXES:
                    text = rendered(data.decode("utf-8"), values[platform], source / relative, used)
                    outputs[target / relative] = text.encode("utf-8")
                elif b"{{platform:" in data:
                    raise ValueError(f"텍스트로 렌더링하지 않는 파일에 플랫폼 빈칸이 있습니다: {source / relative}")
                else:
                    outputs[target / relative] = data
                # Keep generated files writable so the next in-place render can update them.
                modes[target / relative] = (source_path.stat().st_mode & 0o777) | 0o200
    return outputs, modes, used


def unrendered_slots(root: Path) -> list[str]:
    sources = [root / source for source in TARGETS]
    found = []
    for path in sorted((root / "shared").rglob("*")):
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES or "vendor" in path.relative_to(root).parts:
            continue
        if any(path == source or source in path.parents for source in sources):
            continue
        if TOKEN.search(path.read_text(encoding="utf-8")):
            found.append(str(path.relative_to(root)))
    return found


def current_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    return data.replace(b"\r\n", b"\n") if path.suffix in TEXT_SUFFIXES else data


def mode_differs(path: Path, mode: int) -> bool:
    # Git tracks only the executable bit, and Windows has no POSIX modes to compare.
    return os.name == "posix" and (path.stat().st_mode & 0o111) != (mode & 0o111)


def stale_outputs(root: Path, outputs: dict[Path, bytes], modes: dict[Path, int]) -> list[str]:
    stale = [str(path) for path, data in outputs.items() if not (root / path).is_file()
             or current_bytes(root / path) != data or mode_differs(root / path, modes[path])]
    for source, platforms in TARGETS.items():
        if (root / source).is_dir():
            for target in platforms.values():
                if (root / target).is_dir():
                    stale += [str(path.relative_to(root)) for path in (root / target).rglob("*")
                              if path.is_file() and path.relative_to(root) not in outputs]
    return sorted(stale)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]

    try:
        values = {platform: parse_values((root / path).read_text(encoding="utf-8"), path)
                  for platform, path in PLATFORM_TEXT.items()}
        names = {platform: set(entries) for platform, entries in values.items()}
        if names["claude"] != names["codex"]:
            raise ValueError("플랫폼 문구 이름이 플랫폼마다 다릅니다: " + ", ".join(sorted(names["claude"] ^ names["codex"])))
        outputs, modes, used = expected_outputs(root, values)
        unused = sorted(names["claude"] - used)
        if unused:
            raise ValueError("사용하지 않는 플랫폼 문구: " + ", ".join(unused))
        unrendered = unrendered_slots(root)
        if unrendered:
            raise ValueError("렌더링 대상이 아닌 파일에 플랫폼 빈칸이 있습니다: " + ", ".join(unrendered))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1

    if args.check:
        stale = stale_outputs(root, outputs, modes)
        if stale:
            print("플랫폼 생성물 불일치: " + ", ".join(stale), file=sys.stderr)
            return 1
        return 0

    for path in stale_outputs(root, outputs, modes):
        target = root / path
        if Path(path) not in outputs:
            target.unlink()
            print(f"생성물 제거: {path}")
            for parent in target.parents:
                if parent == root or any(parent.iterdir()):
                    break
                parent.rmdir()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            handle.write(outputs[Path(path)])
        target.chmod(modes[Path(path)])
        print(f"생성물 갱신: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
