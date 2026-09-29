#!/usr/bin/env python3
"""Install the harness into the products' discovery paths and verify the installed links.

Links point from the user's home into this repository. Files are symbolic links on every platform; directories are
symbolic links on Linux and junctions on Windows. Windows file links need symbolic link permission (Developer Mode).
Hard links left by the earlier Windows fallback are replaced when they are still the source file or the install state
recorded them. Paths already occupied by something else are left untouched and installation stops.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile

WINDOWS = os.name == "nt"


@dataclass(frozen=True)
class Link:
    source: str  # 저장소 기준 경로
    destination: str  # 홈 기준 경로
    previous: str | None = None  # 같은 설치 경로가 예전에 가리키던 저장소 경로


SHARED_SKILLS = ("brain-storming", "create-pull-request", "grill-me", "improve-code-base-architecture",
                 "interface-design", "review-pull-request", "structure-documentation", "ubiquitous-language")
PLATFORM_SKILLS = ("self-diagnose", "integrate-context", "refine-harness", "modify-harness")

LINKS = (
    Link("claude/CLAUDE.md", ".claude/CLAUDE.md"),
    Link("shared/harness-authoring.md", ".claude/harness-authoring.md"),
    Link("shared/skill-authoring.md", ".claude/skill-authoring.md"),
    Link("shared/agent-authoring.md", ".claude/agent-authoring.md"),
    Link("shared/self-harness-architecture.md", ".claude/self-harness-architecture.md"),
    Link("shared/harness-review.md", ".claude/harness-review.md"),
    Link("claude/harness-components.md", ".claude/harness-components.md"),
    Link("claude/self-diagnosis.md", ".claude/self-diagnosis.md", "shared/self-diagnosis.md"),
    Link("claude/harness-revision.md", ".claude/harness-revision.md"),
    Link("claude/commands/frontend-design.md", ".claude/commands/frontend-design.md"),
    Link("shared/vendor/anthropics/frontend-design/LICENSE.txt", ".claude/commands/frontend-design.LICENSE.txt"),
    Link("claude/rules", ".claude/rules"),
    Link("claude/agents", ".claude/agents"),
    Link("claude/hooks", ".claude/hooks"),
    Link("codex/AGENTS.md", ".codex/AGENTS.md"),
    Link("shared/harness-authoring.md", ".codex/harness-authoring.md"),
    Link("shared/skill-authoring.md", ".codex/skill-authoring.md"),
    Link("shared/agent-authoring.md", ".codex/agent-authoring.md"),
    Link("shared/self-harness-architecture.md", ".codex/self-harness-architecture.md"),
    Link("shared/harness-review.md", ".codex/harness-review.md"),
    Link("codex/self-diagnosis.md", ".codex/self-diagnosis.md", "shared/self-diagnosis.md"),
    Link("codex/harness-revision.md", ".codex/harness-revision.md"),
    Link("codex/harness-components.md", ".codex/harness-components.md"),
    Link("codex/agents/harness-reviewer.toml", ".codex/agents/harness-reviewer.toml"),
    Link("codex/skills/frontend-design", ".agents/skills/frontend-design"),
    *(link for name in PLATFORM_SKILLS for link in (
        Link(f"claude/skills/{name}", f".claude/skills/{name}", f"shared/skills/{name}"),
        Link(f"codex/skills/{name}", f".agents/skills/{name}", f"shared/skills/{name}"))),
    *(link for name in SHARED_SKILLS for link in (
        Link(f"shared/skills/{name}", f".claude/skills/{name}"),
        Link(f"shared/skills/{name}", f".agents/skills/{name}"))),
)

# 이름이 바뀐 구성물의 이전 설치 경로. 새 경로 설치를 확인한 뒤, 이전·새 원본을 가리키는 관리 링크만 제거한다.
RENAMED = (
    (".claude/meta-doc-critic.md", "shared/meta-doc-critic.md", "shared/harness-review.md"),
    (".codex/meta-doc-critic.md", "shared/meta-doc-critic.md", "shared/harness-review.md"),
    (".codex/agents/meta-doc-critic.toml", "codex/agents/meta-doc-critic.toml", "codex/agents/harness-reviewer.toml"),
)
# 더 이상 설치하지 않는 skill의 이전 링크.
REMOVED_SKILLS = tuple(
    (f"{home}/{name}", f"{base}/{name}")
    for name, bases in (("ubuiquitous-language", ("shared/skills", "shared/skills")),
                        ("self-improve", ("claude/skills", "codex/skills")),
                        ("port-harness-change", ("shared/skills", "shared/skills")))
    for home, base in zip((".claude/skills", ".agents/skills"), bases)
)
# 예전 Windows hard link 대체가 설치 파일의 원본과 파일 식별자를 기록하던 상태 파일. 교체를 마치면 지운다.
INSTALL_STATE = (".claude/agent-harness-install-state.json", ".codex/agent-harness-install-state.json")
# 남아 있으면 안 되는 옛 경로.
ABSENT = (".claude/self-harness-engineering.md", ".claude/skills/frontend-design", ".codex/instruction-locations.md",
          ".claude/agents/meta-doc-critic.md",
          *(destination for destination, _, _ in RENAMED), *(destination for destination, _ in REMOVED_SKILLS),
          *INSTALL_STATE)


class InstallError(Exception):
    pass


def say(message: str) -> None:
    print(message, flush=True)


def is_junction(path: Path) -> bool:
    if not WINDOWS:
        return False
    try:
        info = os.lstat(path)
    except OSError:
        return False
    return bool(getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT) \
        and getattr(info, "st_reparse_tag", None) == stat.IO_REPARSE_TAG_MOUNT_POINT


def is_link(path: Path) -> bool:
    return path.is_symlink() or is_junction(path)


def same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(os.path.realpath(left)) == os.path.normcase(os.path.realpath(right))


def link_target(path: Path) -> Path:
    """Where a symbolic link or junction points, one level only. Windows reports targets with the \\\\?\\ or \\??\\
    namespace prefix, which is dropped so the target compares with ordinary paths."""
    target = os.readlink(path)
    for prefix, replacement in (('\\\\?\\UNC\\', '\\\\'), ('\\??\\UNC\\', '\\\\'), ('\\\\?\\', ''), ('\\??\\', '')):
        if target.startswith(prefix):
            target = replacement + target[len(prefix):]
            break
    return Path(os.path.normpath(os.path.join(path.parent, target)))


def links_directly_to(path: Path, source: Path) -> bool:
    """True when the link at `path` names `source` itself. Removal decisions use this so that a user's own link
    reaching a managed file through another link is not mistaken for a managed link."""
    return is_link(path) and os.path.normcase(link_target(path)) == os.path.normcase(source)


def hard_link_of(path: Path, source: Path) -> bool:
    return not is_link(path) and path.is_file() and source.is_file() and os.path.samefile(path, source)


def points_to(path: Path, source: Path) -> bool:
    """True when `path` is a link that reaches `source`; used to keep and verify."""
    return is_link(path) and (links_directly_to(path, source) or same_path(path, source))


def remove_link(path: Path) -> None:
    if is_junction(path):
        os.rmdir(path)  # junction 자체만 지우고 대상은 건드리지 않는다.
    else:
        os.unlink(path)


def create_junction(source: Path, destination: Path) -> None:
    """Junctions need no administrator right. The public standard library cannot create one, so use CPython's
    _winapi.CreateJunction, falling back to cmd's mklink with every argument quoted."""
    try:
        import _winapi
        _winapi.CreateJunction(str(source), str(destination))
        return
    except (ImportError, AttributeError):
        pass
    result = subprocess.run(f'cmd /c mklink /J "{destination}" "{source}"', capture_output=True)
    if result.returncode != 0:
        # cmd 출력은 콘솔 코드 페이지(한국어 Windows는 cp949)이므로 깨진 글자를 허용해 읽는다.
        output = (result.stderr or result.stdout).decode("oem" if WINDOWS else "utf-8", errors="replace").strip()
        raise InstallError(f"junction 생성 실패: {destination}: {output}")


def create_directory_link(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if WINDOWS:
        create_junction(source, destination)
    else:
        os.symlink(source, destination, target_is_directory=True)


def create_file_link(source: Path, destination: Path) -> None:
    """Build the symbolic link beside the destination and move it into place, so a hard link being replaced stays
    until its replacement exists."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    # 고유한 빈 이름만 얻고 그 자리에 링크를 만든다.
    fd, temporary = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
    os.close(fd)
    os.unlink(temporary)
    try:
        os.symlink(source, temporary)
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            raise InstallError("Windows에서 symbolic link를 만들 권한이 없습니다. 설정 → 시스템 → 개발자용에서 "
                               "개발자 모드를 켠 뒤 설치기를 다시 실행하세요.") from error
        raise
    try:
        os.replace(temporary, destination)
    finally:
        if os.path.lexists(temporary):
            os.unlink(temporary)


def state_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path))


def load_install_state(home: Path) -> dict:
    """Hard links recorded by the earlier Windows fallback, as destination -> {source, identity}."""
    records = {}
    for name in INSTALL_STATE:
        path = home / name
        if not os.path.lexists(path):
            continue
        try:
            for destination, entry in json.loads(path.read_text(encoding="utf-8"))["files"].items():
                records[destination] = {"source": entry["source"], "identity": dict(entry["identity"])}
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
            raise InstallError(f"이전 설치 상태 파일을 읽지 못했습니다: {path}: {error}\n"
                               "기록된 설치 파일(예전 hard link)을 직접 확인해 지운 뒤 이 상태 파일을 지우고 "
                               "설치기를 다시 실행하세요.") from error
    return records


def replaceable_hard_link(repo: Path, link: Link, destination: Path, records: dict) -> bool:
    """True for a file the earlier Windows fallback installed: still the same file as the source, or recorded for this
    path with its current file identity after the source was replaced. As with the removed fallback, edits made in
    place to such a detached copy are not kept."""
    if is_link(destination) or not destination.is_file():
        return False
    sources = [repo / link.source] + ([repo / link.previous] if link.previous else [])
    if any(source.is_file() and os.path.samefile(destination, source) for source in sources):
        return True
    entry = records.get(state_key(destination))
    info = os.lstat(destination)
    return (entry is not None and entry["source"] in [state_key(source) for source in sources]
            and entry["identity"] == {"volume": str(info.st_dev), "file": str(info.st_ino)})


def retire_previous(repo: Path, home: Path, link: Link) -> None:
    """Remove a managed link that still points at the source this path used before."""
    if not link.previous:
        return
    destination = home / link.destination
    if links_directly_to(destination, repo / link.previous):
        remove_link(destination)
        say(f"이전 관리 링크 제거: {destination}")


def install_link(repo: Path, home: Path, link: Link, records: dict) -> None:
    source, destination = repo / link.source, home / link.destination
    retire_previous(repo, home, link)
    if points_to(destination, source):
        say(f"유지: {destination}")
        return
    if source.is_dir():
        if os.path.lexists(destination):
            raise InstallError(f"기존 경로가 관리 링크와 다릅니다: {destination}")
        create_directory_link(source, destination)
    else:
        if os.path.lexists(destination) and not replaceable_hard_link(repo, link, destination, records):
            raise InstallError(f"기존 경로가 관리 링크와 다릅니다: {destination}\n"
                               "예전 설치본이면 필요한 내용을 옮긴 뒤 지우고 설치기를 다시 실행하세요.")
        create_file_link(source, destination)
    say(f"연결: {destination} -> {source}")


def install_links(repo: Path, home: Path) -> None:
    for link in LINKS:
        if not os.path.lexists(repo / link.source):
            raise InstallError(f"링크 원본이 없습니다: {repo / link.source}")
    records = load_install_state(home)
    for link in LINKS:
        install_link(repo, home, link, records)
    for name in INSTALL_STATE:
        if os.path.lexists(home / name):
            os.unlink(home / name)
            say(f"이전 설치 상태 파일 제거: {home / name}")


def remove_renamed(repo: Path, home: Path) -> None:
    for destination_name, old, new in RENAMED:
        destination = home / destination_name
        if not os.path.lexists(destination):
            continue
        # 이전·새 원본을 직접 가리키는 링크나 새 원본의 hard link만 관리 대상이다.
        if not (links_directly_to(destination, repo / old) or links_directly_to(destination, repo / new)
                or hard_link_of(destination, repo / new)):
            raise InstallError(f"이전 비관리 경로를 보존했습니다: {destination}")
        remove_link(destination)
        say(f"이전 관리 링크 제거: {destination}")


def remove_old_skills(repo: Path, home: Path) -> None:
    for destination_name, old in REMOVED_SKILLS:
        destination = home / destination_name
        if not os.path.lexists(destination):
            continue
        if not links_directly_to(destination, repo / old):
            raise InstallError(f"이전 비관리 skill 경로를 보존했습니다: {destination}")
        remove_link(destination)
        say(f"이전 관리 skill 링크 제거: {destination}")


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, encoding="utf-8")


def is_repository_root(repo: Path) -> bool:
    try:
        top = git(repo, "rev-parse", "--show-toplevel")
    except FileNotFoundError:
        return False
    return top.returncode == 0 and same_path(Path(top.stdout.strip()), repo)


def configure_hooks_path(repo: Path) -> None:
    """Point this repository's git hooks at .githooks, keeping any other hook setup intact."""
    if not is_repository_root(repo):
        say("git을 찾지 못했거나 저장소 루트가 git 작업 트리가 아니어서 core.hooksPath를 설정하지 않았습니다.")
        return
    local = git(repo, "config", "--local", "--get", "core.hooksPath").stdout.strip()
    if local == ".githooks":
        return
    if local:
        raise InstallError(f"기존 core.hooksPath가 관리 값과 다릅니다: {local}")
    # 전역 hook 경로나 .git/hooks의 사용자 hook이 있으면 설정이 그것을 끄게 되므로 보존하고 중단한다.
    inherited = git(repo, "config", "--get", "core.hooksPath").stdout.strip()
    hooks = Path(git(repo, "rev-parse", "--git-path", "hooks").stdout.strip())
    hooks = hooks if hooks.is_absolute() else repo / hooks
    custom = sorted(str(path) for path in (hooks.iterdir() if hooks.is_dir() else [])
                    if not (path.is_dir() and not path.is_symlink()) and not path.name.endswith(".sample"))
    if inherited or custom:
        raise InstallError("기존 git hook이 있어 설치를 중단했습니다: " + ", ".join(filter(None, [inherited, *custom])) +
                           "\n기존 hook을 .githooks로 옮기거나 연결한 뒤 git config --local core.hooksPath .githooks를 설정하고 "
                           "설치기를 다시 실행하세요.")
    if git(repo, "config", "--local", "core.hooksPath", ".githooks").returncode != 0:
        raise InstallError("core.hooksPath 설정 실패")
    say("연결: core.hooksPath -> .githooks")


def verify(repo: Path, home: Path) -> None:
    if is_repository_root(repo) and git(repo, "config", "--local", "--get", "core.hooksPath").stdout.strip() != ".githooks":
        raise InstallError("core.hooksPath가 .githooks가 아닙니다.")
    for link in LINKS:
        destination = home / link.destination
        if not is_link(destination):
            raise InstallError(f"링크가 아닙니다: {destination}")
        if not points_to(destination, repo / link.source):
            raise InstallError(f"링크 대상 불일치: {destination} -> {os.path.realpath(destination)} (예상: {repo / link.source})")
    for name in ABSENT:
        if os.path.lexists(home / name):
            raise InstallError(f"더 이상 사용하지 않는 경로가 남아 있습니다: {home / name}\n"
                               "설치기를 실행하면 관리 경로는 정리됩니다.")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", type=Path, default=Path(os.path.abspath(__file__)).parent.parent)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--verify", action="store_true", help="설치하지 않고 설치 상태만 검증한다")
    args = parser.parse_args(argv)
    # Windows 기존 링크와 이전 설치 상태는 경로를 해석하지 않은 전체 경로로 만들어졌고, Linux 링크는 해석한 경로로 만들어졌다.
    repo = Path(os.path.abspath(args.repo_root) if WINDOWS else os.path.realpath(args.repo_root))
    home = Path(os.path.abspath(args.home))
    try:
        if not args.verify:
            render = subprocess.run([sys.executable, str(repo / "scripts/render_platform_files.py")])
            if render.returncode != 0:
                raise InstallError("플랫폼 생성물 렌더링 실패")
            configure_hooks_path(repo)
            for directory in (".claude", ".codex", ".agents/skills"):
                (home / directory).mkdir(parents=True, exist_ok=True)
            install_links(repo, home)
            remove_renamed(repo, home)
            remove_old_skills(repo, home)
        verify(repo, home)
    except (InstallError, OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    say("검증 완료: 설치 링크가 유효합니다." if args.verify else f"설치 완료: {repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
